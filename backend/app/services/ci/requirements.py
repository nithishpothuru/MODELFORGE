import ast
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

try:
    import tomllib  # Python 3.11+ built-in
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None

try:
    from packaging.requirements import InvalidRequirement, Requirement
except ImportError:
    Requirement = None  # type: ignore
    InvalidRequirement = Exception  # type: ignore

from app.schemas.validation import DetectedDependency, ResolvedDependency


# Standard library modules in Python (base set to complement sys.stdlib_module_names)
STANDARD_LIBRARY_MODULES: Set[str] = {
    "abc", "aifc", "antigravity", "argparse", "array", "ast", "asynchat", "asyncio",
    "asyncore", "atexit", "audioop", "base64", "bdb", "binascii", "binhex", "bisect",
    "builtins", "bz2", "calendar", "cgi", "cgitb", "chunk", "cmath", "cmd", "code",
    "codecs", "codeop", "collections", "colorsys", "compileall", "concurrent", "configparser",
    "contextlib", "contextvars", "copy", "copyreg", "cProfile", "crypt", "csv", "ctypes",
    "curses", "dataclasses", "datetime", "dbm", "decimal", "difflib", "dis", "distutils",
    "doctest", "email", "encodings", "ensurepip", "enum", "errno", "faulthandler", "fcntl",
    "filecmp", "fileinput", "fnmatch", "fractions", "ftplib", "functools", "gc", "getopt",
    "getpass", "gettext", "glob", "graphlib", "grp", "gzip", "hashlib", "heapq", "hmac",
    "html", "http", "idlelib", "imaplib", "imghdr", "imp", "importlib", "inspect", "io",
    "ipaddress", "itertools", "json", "keyword", "lib2to3", "linecache", "locale", "logging",
    "lzma", "mailbox", "mailcap", "marshal", "math", "mimetypes", "mmap", "modulefinder",
    "msilib", "msvcrt", "multiprocessing", "netrc", "nis", "nntplib", "numbers", "operator",
    "optparse", "os", "ossaudiodev", "parser", "pathlib", "pdb", "pickle", "pickletools",
    "pipes", "pkgutil", "platform", "plistlib", "poplib", "posix", "posixpath", "pprint",
    "profile", "pstats", "pty", "pwd", "py_compile", "pyclbr", "pydoc", "queue", "quopri",
    "random", "re", "readline", "reprlib", "resource", "rlcompleter", "runpy", "sched",
    "secrets", "select", "selectors", "shelve", "shlex", "shutil", "signal", "site",
    "smtpd", "smtplib", "sndhdr", "socket", "socketserver", "spwd", "sqlite3", "sre_compile",
    "sre_constants", "sre_parse", "ssl", "stat", "statistics", "string", "stringprep",
    "struct", "subprocess", "sunau", "symbol", "symtable", "sys", "sysconfig", "syslog",
    "tabnanny", "tarfile", "telnetlib", "tempfile", "termios", "test", "textwrap", "this",
    "threading", "time", "timeit", "tkinter", "token", "tokenize", "tomllib", "trace",
    "traceback", "tracemalloc", "tty", "turtle", "turtledemo", "types", "typing", "unicodedata",
    "unittest", "urllib", "uu", "uuid", "venv", "warnings", "wave", "weakref", "webbrowser",
    "winreg", "winsound", "wsgiref", "xdrlib", "xml", "xmlrpc", "zipapp", "zipfile", "zipimport",
    "zlib", "_thread",
}

if hasattr(sys, "stdlib_module_names"):
    STANDARD_LIBRARY_MODULES.update(sys.stdlib_module_names)

# Map common import names to canonical PyPI distribution package names
IMPORT_TO_DISTRIBUTION_MAP: Dict[str, str] = {
    "sklearn": "scikit-learn",
    "cv2": "opencv-python",
    "PIL": "Pillow",
    "yaml": "PyYAML",
    "bs4": "beautifulsoup4",
    "dotenv": "python-dotenv",
    "dateutil": "python-dateutil",
    "jwt": "PyJWT",
    "git": "GitPython",
    "psycopg2": "psycopg2-binary",
    "serial": "pyserial",
    "magic": "python-magic",
    "Crypto": "pycryptodome",
    "Cryptodome": "pycryptodome",
    "google.protobuf": "protobuf",
    "attr": "attrs",
    "pydantic_settings": "pydantic-settings",
    "torch": "torch",
    "torchvision": "torchvision",
    "torchaudio": "torchaudio",
    "transformers": "transformers",
    "diffusers": "diffusers",
    "datasets": "datasets",
    "accelerate": "accelerate",
    "xgboost": "xgboost",
    "lightgbm": "lightgbm",
    "catboost": "catboost",
    "onnx": "onnx",
    "onnxruntime": "onnxruntime",
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "gunicorn": "gunicorn",
    "flask": "Flask",
    "streamlit": "streamlit",
    "gradio": "gradio",
    "numpy": "numpy",
    "pandas": "pandas",
    "scipy": "scipy",
    "matplotlib": "matplotlib",
    "seaborn": "seaborn",
    "joblib": "joblib",
    "statsmodels": "statsmodels",
    "requests": "requests",
    "httpx": "httpx",
    "aiohttp": "aiohttp",
    "sqlalchemy": "SQLAlchemy",
    "alembic": "alembic",
    "pydantic": "pydantic",
    "pytest": "pytest",
    "tqdm": "tqdm",
    "rich": "rich",
    "click": "click",
    "typer": "typer",
    "fitz": "PyMuPDF",
    "docx": "python-docx",
    "pptx": "python-pptx",
    "openpyxl": "openpyxl",
    "xlrd": "xlrd",
}

# Categorization for detected dependencies
PACKAGE_CATEGORY_MAP: Dict[str, str] = {
    "torch": "ml_framework",
    "torchvision": "ml_framework",
    "torchaudio": "ml_framework",
    "tensorflow": "ml_framework",
    "keras": "ml_framework",
    "scikit-learn": "ml_framework",
    "xgboost": "ml_framework",
    "lightgbm": "ml_framework",
    "catboost": "ml_framework",
    "transformers": "ml_framework",
    "diffusers": "ml_framework",
    "onnx": "ml_framework",
    "onnxruntime": "ml_framework",
    "numpy": "data_processing",
    "pandas": "data_processing",
    "polars": "data_processing",
    "scipy": "data_processing",
    "matplotlib": "data_processing",
    "seaborn": "data_processing",
    "opencv-python": "data_processing",
    "fastapi": "web_framework",
    "Flask": "web_framework",
    "uvicorn": "web_framework",
    "gunicorn": "web_framework",
    "streamlit": "web_framework",
    "gradio": "web_framework",
}

# Curated stable, compatible baseline versions for ML, data science, and web libraries
DEFAULT_PACKAGE_VERSIONS: Dict[str, str] = {
    # Core Data Science & ML
    "numpy": "1.26.4",
    "pandas": "2.2.2",
    "scipy": "1.13.1",
    "scikit-learn": "1.5.0",
    "joblib": "1.4.2",
    "matplotlib": "3.9.2",
    "seaborn": "0.13.2",
    "xgboost": "2.0.3",
    "lightgbm": "4.3.0",
    "catboost": "1.2.5",
    "statsmodels": "0.14.2",
    # Deep Learning
    "torch": "2.3.1",
    "torchvision": "0.18.1",
    "torchaudio": "2.3.1",
    "tensorflow": "2.16.1",
    "keras": "3.3.3",
    "transformers": "4.41.2",
    "diffusers": "0.29.0",
    "datasets": "2.19.2",
    "accelerate": "0.30.1",
    "onnx": "1.16.1",
    "onnxruntime": "1.18.0",
    # Computer Vision, NLP, Utils
    "opencv-python": "4.9.0.86",
    "pillow": "10.3.0",
    "nltk": "3.8.1",
    "spacy": "3.7.4",
    "tqdm": "4.66.4",
    # Web & APIs
    "fastapi": "0.111.0",
    "uvicorn": "0.30.1",
    "flask": "3.0.3",
    "streamlit": "1.35.0",
    "gradio": "4.32.0",
    "requests": "2.32.3",
    "httpx": "0.27.0",
    "pydantic": "2.7.4",
    "python-dotenv": "1.0.1",
    "pyyaml": "6.0.1",
}


class RequirementsHandler:
    """Manages parsing existing requirements.txt and inferring missing ones."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir.resolve()

    @staticmethod
    def is_ci_generated_requirements(req_path: Path) -> bool:
        """Check if a requirements.txt file was auto-generated by ModelForge CI."""
        try:
            content = req_path.read_text(encoding="utf-8", errors="ignore")
            if "ModelForge CI Validation Pipeline" in content or "automatically generated by ModelForge CI" in content:
                return True
        except Exception:
            pass
        return False

    def find_requirements_file(self) -> Optional[Path]:
        """Locate root or primary requirements.txt in the project directory, ignoring CI auto-generated files."""
        root_req = self.project_dir / "requirements.txt"
        if root_req.exists() and root_req.is_file():
            if not self.is_ci_generated_requirements(root_req):
                return root_req

        # Search for any requirements.txt, prioritizing shallowest
        candidates = list(self.project_dir.glob("**/requirements.txt"))
        if candidates:
            # Sort by path length to get the most top-level one
            candidates.sort(key=lambda p: len(p.parts))
            for cand in candidates:
                if not self.is_ci_generated_requirements(cand):
                    return cand

        return None

    def parse_requirements(
        self,
        req_path: Path,
    ) -> Tuple[List[DetectedDependency], List[str], List[str]]:
        """
        Parse an existing requirements.txt file.
        Returns:
            (detected_dependencies, syntax_errors, warnings)
        """
        dependencies: List[DetectedDependency] = []
        syntax_errors: List[str] = []
        warnings: List[str] = []

        seen_packages: Dict[str, str] = {}  # normalized_name -> spec

        try:
            content = req_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            return [], [f"Failed to read requirements file: {exc}"], []

        lines = content.splitlines()
        for idx, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            # Ignore empty lines and full line comments
            if not line or line.startswith("#"):
                continue

            # Strip inline comments if not part of URL
            if " #" in line:
                line = line.split(" #")[0].strip()

            # Handle pip options like --extra-index-url, -r other.txt, -f
            if line.startswith(("-", "--")):
                warnings.append(f"Line {idx}: Skipped pip option directive: '{line}'")
                continue

            if Requirement is not None:
                try:
                    parsed = Requirement(line)
                    norm_name = parsed.name.lower().replace("_", "-")
                    spec = str(parsed.specifier) if parsed.specifier else None

                    # Check for duplicates or conflicting versions
                    if norm_name in seen_packages:
                        prev_spec = seen_packages[norm_name]
                        if prev_spec != spec:
                            warnings.append(
                                f"Line {idx}: Duplicate declaration for package '{parsed.name}' "
                                f"with differing constraints (found '{spec}', previously '{prev_spec}')."
                            )
                        else:
                            warnings.append(
                                f"Line {idx}: Redundant duplicate requirement for '{parsed.name}'."
                            )
                    else:
                        seen_packages[norm_name] = spec

                    category = PACKAGE_CATEGORY_MAP.get(norm_name, "general")
                    dependencies.append(
                        DetectedDependency(
                            name=parsed.name,
                            version_spec=spec,
                            source="requirements.txt",
                            inferred=False,
                            category=category,
                        )
                    )

                except InvalidRequirement as err:
                    syntax_errors.append(f"Line {idx}: Malformed requirement syntax '{line}': {err}")
                except Exception as exc:
                    syntax_errors.append(f"Line {idx}: Error parsing '{line}': {exc}")
            else:
                # Basic regex fallback if packaging is unavailable
                match = re.match(r"^([a-zA-Z0-9_\-\.]+)(.*)$", line)
                if match:
                    pkg_name = match.group(1)
                    spec = match.group(2).strip() or None
                    norm_name = pkg_name.lower().replace("_", "-")
                    category = PACKAGE_CATEGORY_MAP.get(norm_name, "general")
                    dependencies.append(
                        DetectedDependency(
                            name=pkg_name,
                            version_spec=spec,
                            source="requirements.txt",
                            inferred=False,
                            category=category,
                        )
                    )
                else:
                    syntax_errors.append(f"Line {idx}: Malformed requirement line: '{line}'")

        return dependencies, syntax_errors, warnings

    def extract_from_metadata_files(self) -> Tuple[List[DetectedDependency], List[str]]:
        """Extract declared dependencies from pyproject.toml, setup.py, setup.cfg, or Pipfile."""
        dependencies: List[DetectedDependency] = []
        sources_found: List[str] = []

        # 1. pyproject.toml
        pyproject_path = self.project_dir / "pyproject.toml"
        if pyproject_path.exists() and tomllib:
            try:
                data = tomllib.loads(pyproject_path.read_text(encoding="utf-8", errors="ignore"))
                # PEP 621 dependencies
                pep621_deps = data.get("project", {}).get("dependencies", [])
                if isinstance(pep621_deps, list):
                    for req_str in pep621_deps:
                        dep = self._parse_single_requirement_str(req_str, "pyproject.toml")
                        if dep:
                            dependencies.append(dep)
                    if pep621_deps:
                        sources_found.append("pyproject.toml [project.dependencies]")

                # Poetry dependencies
                poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
                if isinstance(poetry_deps, dict):
                    for pkg, ver in poetry_deps.items():
                        if pkg.lower() == "python":
                            continue
                        ver_str = str(ver) if isinstance(ver, str) else None
                        dep = DetectedDependency(
                            name=pkg,
                            version_spec=ver_str,
                            source="pyproject.toml [tool.poetry]",
                            inferred=False,
                            category=PACKAGE_CATEGORY_MAP.get(pkg.lower().replace("_", "-"), "general"),
                        )
                        dependencies.append(dep)
                    if poetry_deps:
                        sources_found.append("pyproject.toml [tool.poetry.dependencies]")

            except Exception:
                pass

        # 2. setup.cfg parsing
        setup_cfg_path = self.project_dir / "setup.cfg"
        if setup_cfg_path.exists():
            try:
                import configparser
                cfg = configparser.ConfigParser()
                cfg.read(str(setup_cfg_path), encoding="utf-8")
                if "options" in cfg and "install_requires" in cfg["options"]:
                    req_lines = cfg["options"]["install_requires"].strip().splitlines()
                    for line in req_lines:
                        dep = self._parse_single_requirement_str(line.strip(), "setup.cfg")
                        if dep:
                            dependencies.append(dep)
                    sources_found.append("setup.cfg [options.install_requires]")
            except Exception:
                pass

        return dependencies, sources_found

    def infer_dependencies_from_imports(
        self,
        python_files: List[Path],
    ) -> List[DetectedDependency]:
        """
        Analyze AST imports across all Python files and map to canonical PyPI packages.
        Excludes standard library and local modules.
        """
        imported_modules: Set[str] = set()

        for py_file in python_files:
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(content, filename=str(py_file))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imported_modules.add(alias.name.split(".")[0])
                    elif isinstance(node, ast.ImportFrom):
                        # Skip relative imports (node.level > 0)
                        if node.level == 0 and node.module:
                            imported_modules.add(node.module.split(".")[0])
            except Exception:
                continue

        # Collect local package and module names to avoid self-referencing local files
        local_names = self._get_local_module_names()

        inferred: List[DetectedDependency] = []
        seen_canonical: Set[str] = set()

        for mod in sorted(imported_modules):
            if not mod or mod.startswith("_"):
                continue

            # Skip standard library modules
            if mod in STANDARD_LIBRARY_MODULES:
                continue

            # Skip local project modules and directory packages
            if mod in local_names:
                continue

            # Map to distribution name
            dist_name = IMPORT_TO_DISTRIBUTION_MAP.get(mod, mod)
            norm_name = dist_name.lower().replace("_", "-")

            if norm_name in seen_canonical:
                continue
            seen_canonical.add(norm_name)

            category = PACKAGE_CATEGORY_MAP.get(norm_name, "general")
            inferred.append(
                DetectedDependency(
                    name=dist_name,
                    version_spec=None,
                    source="inferred_import",
                    inferred=True,
                    category=category,
                )
            )

        return inferred

    def build_resolved_dependencies(
        self,
        direct_dependencies: List[DetectedDependency],
        validator_resolved: Optional[List[ResolvedDependency]] = None,
    ) -> List[ResolvedDependency]:
        """
        Merge validator-resolved packages with direct declared dependencies.
        Preserves explicit user-declared pins if valid, infers compatible pins for unpinned,
        and includes resolved transitive dependencies.
        """
        resolved_map: Dict[str, ResolvedDependency] = {}
        direct_norm = {d.name.lower().replace("_", "-"): d for d in direct_dependencies}

        # First, incorporate packages resolved by the isolated validator / pip report
        if validator_resolved:
            for vr in validator_resolved:
                norm = vr.name.lower().replace("_", "-")
                is_dir = norm in direct_norm
                orig_spec = direct_norm[norm].version_spec if is_dir else None
                cat = PACKAGE_CATEGORY_MAP.get(norm, "general")
                resolved_map[norm] = ResolvedDependency(
                    name=vr.name,
                    version=vr.version,
                    is_direct=is_dir,
                    original_spec=orig_spec,
                    category=cat,
                )

        # Ensure all direct dependencies have a resolved pinned version
        for dep in direct_dependencies:
            norm = dep.name.lower().replace("_", "-")
            if norm in resolved_map:
                continue

            ver = None
            if dep.version_spec:
                clean_spec = dep.version_spec.strip()
                if clean_spec.startswith("=="):
                    ver = clean_spec[2:].strip()
                elif any(clean_spec.startswith(op) for op in [">=", "<=", "~=", ">", "<"]):
                    op_stripped = re.sub(r"^[>=<~!]+", "", clean_spec).split(",")[0].strip()
                    ver = op_stripped if op_stripped else DEFAULT_PACKAGE_VERSIONS.get(norm, "1.0.0")
                else:
                    ver = clean_spec

            if not ver:
                ver = DEFAULT_PACKAGE_VERSIONS.get(norm, "1.0.0")

            cat = dep.category or PACKAGE_CATEGORY_MAP.get(norm, "general")
            resolved_map[norm] = ResolvedDependency(
                name=dep.name,
                version=ver,
                is_direct=True,
                original_spec=dep.version_spec,
                category=cat,
            )

        return sorted(resolved_map.values(), key=lambda r: (not r.is_direct, r.name.lower()))

    def generate_pinned_requirements_file(
        self,
        resolved_dependencies: List[ResolvedDependency],
        python_version: str,
        is_inferred: bool = True,
        target_path: Optional[Path] = None,
    ) -> Path:
        """
        Write a version-pinned requirements.txt file with exact packages (package==version).
        """
        if target_path is None:
            target_path = self.project_dir / "requirements.txt"

        status_str = "Inferred from project syntax and dependencies" if is_inferred else "Declared in configuration"
        lines = [
            "# ==============================================================================",
            "# ModelForge CI Validation Pipeline - Automatically Inferred Requirements (Pinned)",
            "# ==============================================================================",
            f"# Target Python Version: {python_version} ({status_str})",
            "# Generated with isolated dependency resolution to ensure compatibility and reproducibility.",
            "# NOTICE: Dependencies are strictly version-pinned (package==version).",
            "# ==============================================================================",
            "",
            "# Direct Project Dependencies",
        ]

        direct_deps = [r for r in resolved_dependencies if r.is_direct]
        transitive_deps = [r for r in resolved_dependencies if not r.is_direct]

        for dep in sorted(direct_deps, key=lambda d: d.name.lower()):
            lines.append(f"{dep.name}=={dep.version}")

        if transitive_deps:
            lines.append("")
            lines.append("# Resolved Transitive Dependencies")
            for dep in sorted(transitive_deps, key=lambda d: d.name.lower()):
                lines.append(f"{dep.name}=={dep.version}")

        lines.append("")
        content = "\n".join(lines)
        target_path.write_text(content, encoding="utf-8")

        # Also place in primary code subdirectory if one exists
        try:
            for sub in self.project_dir.iterdir():
                if sub.is_dir() and not sub.name.startswith((".", "__")) and any(sub.glob("*.py")):
                    (sub / target_path.name).write_text(content, encoding="utf-8")
        except Exception:
            pass

        return target_path

    def generate_resolved_lock_file(
        self,
        resolved_dependencies: List[ResolvedDependency],
        python_version: str,
        is_inferred: bool = False,
    ) -> Path:
        """
        Write requirements-resolved.txt preserving original requirements.txt intact.
        """
        target_path = self.project_dir / "requirements-resolved.txt"
        return self.generate_pinned_requirements_file(
            resolved_dependencies=resolved_dependencies,
            python_version=python_version,
            is_inferred=is_inferred,
            target_path=target_path,
        )

    def generate_requirements_file(
        self,
        dependencies: List[DetectedDependency],
        target_path: Optional[Path] = None,
        python_version: Optional[str] = None,
        pin_versions: bool = True,
    ) -> Path:
        """
        Write the inferred/extracted requirements to requirements.txt in the project directory.
        Always generates version-pinned requirements (package==version).
        """
        resolved = self.build_resolved_dependencies(dependencies)
        return self.generate_pinned_requirements_file(
            resolved_dependencies=resolved,
            python_version=python_version or "3.11",
            is_inferred=True,
            target_path=target_path,
        )

    def _get_local_module_names(self) -> Set[str]:
        """Detect local Python modules and packages in the project root and subdirectories."""
        local_names: Set[str] = set()

        ignored_parts = {
            ".git", ".venv", "venv", "env", "site-packages", "__pycache__",
            ".pytest_cache", ".mypy_cache", "build", "dist",
        }

        for item in self.project_dir.rglob("*.py"):
            rel_parts = set(item.relative_to(self.project_dir).parts)
            if rel_parts & ignored_parts:
                continue

            local_names.add(item.stem)

        for folder in self.project_dir.rglob("*"):
            if not folder.is_dir():
                continue
            rel_parts = set(folder.relative_to(self.project_dir).parts)
            if rel_parts & ignored_parts:
                continue

            if (folder / "__init__.py").exists() or any(folder.glob("*.py")):
                local_names.add(folder.name)

        return local_names

    def _parse_single_requirement_str(
        self,
        req_str: str,
        source: str,
    ) -> Optional[DetectedDependency]:
        """Helper to parse a single requirement string."""
        if not req_str or req_str.startswith("#"):
            return None

        if Requirement is not None:
            try:
                parsed = Requirement(req_str)
                norm = parsed.name.lower().replace("_", "-")
                spec = str(parsed.specifier) if parsed.specifier else None
                return DetectedDependency(
                    name=parsed.name,
                    version_spec=spec,
                    source=source,
                    inferred=False,
                    category=PACKAGE_CATEGORY_MAP.get(norm, "general"),
                )
            except Exception:
                return None
        else:
            name = req_str.split("=")[0].split(">")[0].split("<")[0].split("~")[0].strip()
            if name:
                norm = name.lower().replace("_", "-")
                return DetectedDependency(
                    name=name,
                    version_spec=None,
                    source=source,
                    inferred=False,
                    category=PACKAGE_CATEGORY_MAP.get(norm, "general"),
                )
            return None
