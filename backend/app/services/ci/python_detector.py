import ast
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None

from app.config.settings import settings
from app.schemas.validation import PythonVersionInfo


class PythonVersionDetector:
    """
    Detects declared Python version from project configuration files in priority order,
    identifies conflicting declarations across files, and infers a suitable candidate
    from syntax analysis and dependency requirements when undeclared.
    """

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir.resolve()
        self.supported_versions = getattr(
            settings,
            "SUPPORTED_PYTHON_VERSIONS",
            ["3.9", "3.10", "3.11", "3.12"],
        )
        self.default_version = getattr(
            settings,
            "DEFAULT_PYTHON_VERSION",
            "3.11",
        )

    def detect_version(
        self,
        python_files: Optional[List[Path]] = None,
        detected_packages: Optional[List[str]] = None,
    ) -> PythonVersionInfo:
        """
        Orchestrate detection and inference of Python version for the project.
        """
        declared_versions: Dict[str, str] = {}
        raw_specifiers: Dict[str, str] = {}

        # 1. pyproject.toml
        pyproject_path = self.project_dir / "pyproject.toml"
        if pyproject_path.exists() and tomllib:
            ver, raw = self._parse_pyproject(pyproject_path)
            if ver:
                declared_versions["pyproject.toml"] = ver
                raw_specifiers["pyproject.toml"] = raw

        # 2. Pipfile
        pipfile_path = self.project_dir / "Pipfile"
        if pipfile_path.exists():
            ver = self._parse_pipfile(pipfile_path)
            if ver:
                declared_versions["Pipfile"] = ver
                raw_specifiers["Pipfile"] = ver

        # 3. .python-version
        python_ver_file = self.project_dir / ".python-version"
        if python_ver_file.exists():
            ver = self._parse_python_version_file(python_ver_file)
            if ver:
                declared_versions[".python-version"] = ver
                raw_specifiers[".python-version"] = ver

        # 4. Dockerfiles
        dockerfile_paths = list(self.project_dir.glob("*Dockerfile*")) + list(self.project_dir.glob("docker/*Dockerfile*"))
        for df in dockerfile_paths:
            if df.is_file():
                ver = self._parse_dockerfile(df)
                if ver:
                    rel_name = str(df.relative_to(self.project_dir)).replace("\\", "/")
                    declared_versions[rel_name] = ver
                    raw_specifiers[rel_name] = ver
                    break

        # 5. runtime.txt (Heroku / Streamlit / Cloud)
        runtime_path = self.project_dir / "runtime.txt"
        if runtime_path.exists():
            ver = self._parse_runtime_txt(runtime_path)
            if ver:
                declared_versions["runtime.txt"] = ver
                raw_specifiers["runtime.txt"] = ver

        # 6. setup.cfg / setup.py
        setup_cfg_path = self.project_dir / "setup.cfg"
        if setup_cfg_path.exists():
            ver, raw = self._parse_setup_cfg(setup_cfg_path)
            if ver:
                declared_versions["setup.cfg"] = ver
                raw_specifiers["setup.cfg"] = raw

        # Check for conflicts among declarations
        conflicts = self._find_conflicts(declared_versions)

        # If we have at least one valid declared version
        if declared_versions:
            # Pick by priority order
            priority_order = ["pyproject.toml", "Pipfile", ".python-version", "runtime.txt", "setup.cfg"]
            selected_source = None
            selected_version = None

            for src in priority_order:
                if src in declared_versions:
                    selected_source = src
                    selected_version = declared_versions[src]
                    break

            if not selected_version:
                # Dockerfile or other
                selected_source, selected_version = next(iter(declared_versions.items()))

            return PythonVersionInfo(
                version=selected_version,
                is_inferred=False,
                source=selected_source,
                declared_versions=declared_versions,
                conflicts=conflicts,
                supported_candidates=self.supported_versions,
                raw_specifier=raw_specifiers.get(selected_source),
            )

        # No declared Python version -> Infer from syntax & dependencies
        inferred_ver, reason = self._infer_python_version(
            python_files=python_files,
            detected_packages=detected_packages,
        )

        return PythonVersionInfo(
            version=inferred_ver,
            is_inferred=True,
            source=reason,
            declared_versions={},
            conflicts=[],
            supported_candidates=self.supported_versions,
            raw_specifier=None,
        )

    def _parse_pyproject(self, path: Path) -> Tuple[Optional[str], Optional[str]]:
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8", errors="ignore"))
            # PEP 621 requires-python
            req = data.get("project", {}).get("requires-python")
            if req and isinstance(req, str):
                normalized = self._normalize_version_specifier(req)
                return normalized, req

            # Poetry dependencies python
            poetry_py = data.get("tool", {}).get("poetry", {}).get("dependencies", {}).get("python")
            if poetry_py and isinstance(poetry_py, str):
                normalized = self._normalize_version_specifier(poetry_py)
                return normalized, poetry_py
        except Exception:
            pass
        return None, None

    def _parse_pipfile(self, path: Path) -> Optional[str]:
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            # [requires] python_version = "3.10" or python_full_version = "3.10.8"
            match = re.search(r'python_(?:full_)?version\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                return self._normalize_version_specifier(match.group(1))
        except Exception:
            pass
        return None

    def _parse_python_version_file(self, path: Path) -> Optional[str]:
        try:
            content = path.read_text(encoding="utf-8", errors="ignore").strip()
            first_line = content.splitlines()[0].strip() if content else ""
            if first_line and not first_line.startswith("#"):
                return self._normalize_version_specifier(first_line)
        except Exception:
            pass
        return None

    def _parse_dockerfile(self, path: Path) -> Optional[str]:
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            # FROM python:3.10-slim or FROM python:3.11 or FROM continuumio/miniconda3:latest
            for line in content.splitlines():
                line = line.strip()
                if line.upper().startswith("FROM "):
                    match = re.search(r"python:([0-9]+\.[0-9]+)", line, re.IGNORECASE)
                    if match:
                        return match.group(1)
        except Exception:
            pass
        return None

    def _parse_runtime_txt(self, path: Path) -> Optional[str]:
        try:
            content = path.read_text(encoding="utf-8", errors="ignore").strip()
            # python-3.10.12 or 3.10.12
            match = re.search(r"(?:python-)?([0-9]+\.[0-9]+)", content, re.IGNORECASE)
            if match:
                return match.group(1)
        except Exception:
            pass
        return None

    def _parse_setup_cfg(self, path: Path) -> Tuple[Optional[str], Optional[str]]:
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            match = re.search(r"python_requires\s*=\s*([^\r\n]+)", content)
            if match:
                raw = match.group(1).strip()
                return self._normalize_version_specifier(raw), raw
        except Exception:
            pass
        return None, None

    def _normalize_version_specifier(self, spec: str) -> Optional[str]:
        """Convert specifiers like '>=3.10', '^3.10', '~=3.10.0', '3.10.8' to major.minor e.g. '3.10'."""
        cleaned = spec.strip().replace(" ", "")
        # Match explicit major.minor version number
        match = re.search(r"([0-9]+\.[0-9]+)", cleaned)
        if match:
            major_minor = match.group(1)
            # Verify it maps into supported or sensible Python 3.x
            parts = major_minor.split(".")
            if parts[0] == "3" and len(parts) >= 2:
                return major_minor
        return None

    def _find_conflicts(self, declared_versions: Dict[str, str]) -> List[str]:
        """Identify conflicting major.minor declarations between multiple config files."""
        conflicts: List[str] = []
        if len(declared_versions) <= 1:
            return conflicts

        items = list(declared_versions.items())
        for i in range(len(items)):
            src_a, ver_a = items[i]
            for j in range(i + 1, len(items)):
                src_b, ver_b = items[j]
                if ver_a != ver_b:
                    conflicts.append(
                        f"Conflicting Python version declaration: {src_a} specifies '{ver_a}' "
                        f"while {src_b} specifies '{ver_b}'."
                    )
        return conflicts

    def _infer_python_version(
        self,
        python_files: Optional[List[Path]],
        detected_packages: Optional[List[str]],
    ) -> Tuple[str, str]:
        """
        Infer a supported Python version based on syntax features and dependency constraints.
        """
        min_required_minor = 9  # default baseline 3.9

        # Analyze syntax features
        if python_files:
            for py_file in python_files:
                try:
                    content = py_file.read_text(encoding="utf-8", errors="ignore")
                    tree = ast.parse(content, filename=str(py_file))
                    for node in ast.walk(tree):
                        # Match/case statements introduced in Python 3.10
                        if hasattr(ast, "Match") and isinstance(node, ast.Match):
                            min_required_minor = max(min_required_minor, 10)

                        # Union type syntax in annotations: int | str (ast.BinOp with ast.BitOr)
                        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
                            min_required_minor = max(min_required_minor, 10)

                        # Exception groups (except*) in Python 3.11
                        if hasattr(ast, "TryStar") and isinstance(node, ast.TryStar):
                            min_required_minor = max(min_required_minor, 11)

                except Exception:
                    continue

        # Check detected package baselines
        if detected_packages:
            for pkg in detected_packages:
                norm = pkg.lower().replace("_", "-")
                # Packages requiring Python 3.10+
                if norm in {"torch", "torchvision", "torchaudio", "transformers", "accelerate"}:
                    min_required_minor = max(min_required_minor, 10)
                # Modern versions of polars, gradio, etc. often prefer 3.10+
                if norm in {"polars", "gradio", "diffusers"}:
                    min_required_minor = max(min_required_minor, 10)

        # If no specific constraint forced a higher version, use default configured candidate
        if min_required_minor <= 9:
            candidate = self.default_version
        else:
            # Select supported version matching requirement
            candidate = None
            for sup in self.supported_versions:
                try:
                    sup_minor = int(sup.split(".")[1])
                    if sup_minor >= min_required_minor:
                        candidate = sup
                        break
                except (IndexError, ValueError):
                    continue

            if not candidate:
                candidate = self.default_version

        reason = (
            f"inferred (requires Python >= 3.{min_required_minor} based on syntax and dependencies)"
            if min_required_minor > 9
            else "inferred (default supported candidate)"
        )

        return candidate, reason
