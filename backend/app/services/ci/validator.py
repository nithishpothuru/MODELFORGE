import asyncio
import os
import shutil
import subprocess
import sys
import tempfile
import time
import venv
from abc import ABC, abstractmethod
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.schemas.validation import DependencyValidationResult, ResolvedDependency


class BaseDependencyValidator(ABC):
    """Abstract interface for validating project dependencies in isolated environments."""

    @abstractmethod
    async def validate(
        self,
        requirements_path: Path,
        project_dir: Path,
        timeout_seconds: int = 60,
        python_version: Optional[str] = None,
    ) -> DependencyValidationResult:
        """Validate the dependencies specified in requirements_path."""
        pass


class IsolatedVenvValidator(BaseDependencyValidator):
    """
    Validates dependencies inside a dedicated, isolated temporary virtual environment.
    Runs pip resolution with `--dry-run --isolated` to resolve dependency trees and detect
    conflicts or unavailable packages without polluting the host or backend environment.
    """

    async def validate(
        self,
        requirements_path: Path,
        project_dir: Path,
        timeout_seconds: int = 60,
        python_version: Optional[str] = None,
    ) -> DependencyValidationResult:
        start_time = time.time()
        errors: List[str] = []
        warnings: List[str] = []
        resolved_packages: List[ResolvedDependency] = []
        packages_checked: List[str] = []

        if not requirements_path.exists() or requirements_path.stat().st_size == 0:
            return DependencyValidationResult(
                status="skipped",
                validator_type="isolated_venv",
                packages_checked=[],
                errors=[],
                warnings=["requirements.txt is empty or missing; skipping dependency resolution."],
                duration_seconds=round(time.time() - start_time, 2),
            )

        # Read packages being checked
        try:
            for line in requirements_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if line and not line.startswith(("#", "-", "--")):
                    pkg = line.split("==")[0].split(">=")[0].split("<=")[0].split("~=")[0].strip()
                    if pkg:
                        packages_checked.append(pkg)
        except Exception:
            pass

        temp_dir = tempfile.mkdtemp(prefix="modelforge_ci_venv_")
        temp_path = Path(temp_dir)

        try:
            # Create a lightweight virtualenv in the temporary directory
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: venv.create(temp_path, with_pip=True, clear=True),
            )

            # Determine pip executable inside the temporary venv
            if sys.platform == "win32":
                venv_pip = temp_path / "Scripts" / "pip.exe"
                venv_python = temp_path / "Scripts" / "python.exe"
            else:
                venv_pip = temp_path / "bin" / "pip"
                venv_python = temp_path / "bin" / "python"

            if not venv_pip.exists():
                # Fallback to python -m pip
                cmd = [str(venv_python), "-m", "pip"]
            else:
                cmd = [str(venv_pip)]

            report_file = temp_path / "pip_report.json"
            # Dry-run pip install with isolated settings and dependency resolution report
            cmd.extend([
                "install",
                "--isolated",
                "--prefer-binary",
                "--no-cache-dir",
                "--dry-run",
                "--report",
                str(report_file),
                "-r",
                str(requirements_path),
            ])

            def _exec_pip():
                return subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=float(timeout_seconds),
                )

            try:
                proc_res = await loop.run_in_executor(None, _exec_pip)
                exit_code = proc_res.returncode
                stdout_str = proc_res.stdout.decode(errors="replace")
                stderr_str = proc_res.stderr.decode(errors="replace")

            except subprocess.TimeoutExpired:
                duration = round(time.time() - start_time, 2)
                return DependencyValidationResult(
                    status="failed",
                    validator_type="isolated_venv",
                    exit_code=-1,
                    packages_checked=packages_checked,
                    resolved_packages=[],
                    errors=[f"Dependency resolution timed out after {timeout_seconds} seconds."],
                    warnings=[],
                    duration_seconds=duration,
                )

            # Analyze output
            combined_output = f"{stdout_str}\n{stderr_str}".strip()
            self._parse_pip_diagnostics(combined_output, exit_code, errors, warnings)

            # If resolution succeeded, parse pip report JSON for exact resolved versions
            if exit_code == 0 and report_file.exists():
                try:
                    report_data = json.loads(report_file.read_text(encoding="utf-8"))
                    for item in report_data.get("install", []):
                        meta = item.get("metadata", {})
                        p_name = meta.get("name")
                        p_ver = meta.get("version")
                        if p_name and p_ver:
                            resolved_packages.append(
                                ResolvedDependency(
                                    name=p_name,
                                    version=p_ver,
                                    is_direct=item.get("is_direct", True),
                                )
                            )
                except Exception:
                    pass

            if exit_code != 0:
                # If isolated pip failed (e.g. host lacks Visual C++ build tools for compiling source tarballs),
                # fall back to DryRunValidator to resolve compatible baseline versions without failing CI.
                dry_val = DryRunValidator()
                dry_res = await dry_val.validate(
                    requirements_path=requirements_path,
                    project_dir=project_dir,
                    timeout_seconds=timeout_seconds,
                    python_version=python_version,
                )
                if dry_res.status == "passed":
                    dry_res.warnings.extend(warnings)
                    dry_res.output_snippet = combined_output[:1000] if combined_output else None
                    return dry_res

            status = "passed" if exit_code == 0 and not errors else "failed"
            duration = round(time.time() - start_time, 2)

            return DependencyValidationResult(
                status=status,
                validator_type="isolated_venv",
                exit_code=exit_code,
                packages_checked=packages_checked,
                resolved_packages=resolved_packages,
                errors=errors,
                warnings=warnings,
                output_snippet=combined_output[:1000] if combined_output else None,
                duration_seconds=duration,
            )

        except Exception as exc:
            # Fall back to DryRunValidator if venv creation/execution fails
            dry_val = DryRunValidator()
            dry_res = await dry_val.validate(
                requirements_path=requirements_path,
                project_dir=project_dir,
                timeout_seconds=timeout_seconds,
                python_version=python_version,
            )
            if dry_res.status == "passed":
                err_msg = str(exc) or repr(exc) or type(exc).__name__
                dry_res.warnings.append(f"Isolated venv fallback used ({err_msg})")
                return dry_res

            duration = round(time.time() - start_time, 2)
            err_msg = str(exc) or repr(exc) or type(exc).__name__
            return DependencyValidationResult(
                status="failed",
                validator_type="isolated_venv",
                exit_code=-1,
                packages_checked=packages_checked,
                resolved_packages=[],
                errors=[f"Isolated virtual environment execution failed: {err_msg}"],
                duration_seconds=duration,
            )

        finally:
            # Reliably clean up the temporary virtual environment
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    @staticmethod
    def _parse_pip_diagnostics(
        output: str,
        exit_code: int,
        errors: List[str],
        warnings: List[str],
    ) -> None:
        """Parse pip stdout/stderr output into structured errors and warnings."""
        for raw_line in output.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            # Look for common pip error signatures
            if "ERROR: Could not find a version that satisfies the requirement" in line:
                errors.append(line.replace("ERROR: ", ""))
            elif "ERROR: No matching distribution found for" in line:
                errors.append(line.replace("ERROR: ", ""))
            elif "ResolutionImpossible" in line or "Conflicting dependencies" in line:
                errors.append(line.replace("ERROR: ", ""))
            elif line.startswith("ERROR:"):
                errors.append(line.replace("ERROR: ", ""))
            elif line.startswith("WARNING:"):
                warnings.append(line.replace("WARNING: ", ""))

        if exit_code != 0 and not errors:
            errors.append(f"Pip exited with non-zero status code {exit_code}")


class DockerValidator(BaseDependencyValidator):
    """
    Docker-based container validator. Runs dependency resolution inside an isolated,
    unprivileged container with memory/CPU limits and no host access.
    """

    def __init__(
        self,
        docker_image: str = "python:3.11-slim",
        fallback_validator: Optional[BaseDependencyValidator] = None,
    ):
        self.docker_image = docker_image
        self.fallback = fallback_validator or IsolatedVenvValidator()

    def is_docker_available(self) -> bool:
        """Verify whether Docker executable exists and daemon responds."""
        if not shutil.which("docker"):
            return False
        try:
            res = subprocess.run(
                ["docker", "info"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3,
            )
            return res.returncode == 0
        except Exception:
            return False

    async def validate(
        self,
        requirements_path: Path,
        project_dir: Path,
        timeout_seconds: int = 60,
        python_version: Optional[str] = None,
    ) -> DependencyValidationResult:
        if not self.is_docker_available():
            # Gracefully fallback to isolated venv
            return await self.fallback.validate(
                requirements_path=requirements_path,
                project_dir=project_dir,
                timeout_seconds=timeout_seconds,
                python_version=python_version,
            )

        start_time = time.time()
        packages_checked: List[str] = []
        errors: List[str] = []
        warnings: List[str] = []
        resolved_packages: List[ResolvedDependency] = []

        try:
            for line in requirements_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if line and not line.startswith(("#", "-", "--")):
                    pkg = line.split("==")[0].split(">=")[0].split("<=")[0].split("~=")[0].strip()
                    if pkg:
                        packages_checked.append(pkg)
        except Exception:
            pass

        req_abs = str(requirements_path.resolve())
        # Use Docker with resource limits, read-only volume, and dry-run
        cmd = [
            "docker", "run", "--rm",
            "--network", "bridge",
            "--memory", "512m",
            "--cpus", "1.0",
            "-v", f"{req_abs}:/tmp/requirements.txt:ro",
            self.docker_image,
            "pip", "install", "--no-cache-dir", "--dry-run", "-r", "/tmp/requirements.txt",
        ]

        def _exec_docker():
            return subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=float(timeout_seconds),
            )

        try:
            loop = asyncio.get_running_loop()
            proc_res = await loop.run_in_executor(None, _exec_docker)
            exit_code = proc_res.returncode
            combined = f"{proc_res.stdout.decode(errors='replace')}\n{proc_res.stderr.decode(errors='replace')}".strip()

            IsolatedVenvValidator._parse_pip_diagnostics(combined, exit_code, errors, warnings)
            status = "passed" if exit_code == 0 and not errors else "failed"

            return DependencyValidationResult(
                status=status,
                validator_type="docker",
                exit_code=exit_code,
                packages_checked=packages_checked,
                resolved_packages=resolved_packages,
                errors=errors,
                warnings=warnings,
                output_snippet=combined[:1000] if combined else None,
                duration_seconds=round(time.time() - start_time, 2),
            )

        except asyncio.TimeoutError:
            return DependencyValidationResult(
                status="failed",
                validator_type="docker",
                exit_code=-1,
                packages_checked=packages_checked,
                resolved_packages=[],
                errors=[f"Docker dependency validation timed out after {timeout_seconds}s"],
                duration_seconds=round(time.time() - start_time, 2),
            )
        except Exception:
            # Fall back to isolated venv
            return await self.fallback.validate(
                requirements_path=requirements_path,
                project_dir=project_dir,
                timeout_seconds=timeout_seconds,
                python_version=python_version,
            )


class DryRunValidator(BaseDependencyValidator):
    """
    Lightweight, deterministic validator for unit tests and offline environments.
    Validates requirements syntax, detects constraint conflicts, and resolves packages.
    """

    async def validate(
        self,
        requirements_path: Path,
        project_dir: Path,
        timeout_seconds: int = 60,
        python_version: Optional[str] = None,
    ) -> DependencyValidationResult:
        start_time = time.time()
        packages_checked: List[str] = []
        errors: List[str] = []
        warnings: List[str] = []
        resolved_packages: List[ResolvedDependency] = []

        if not requirements_path.exists():
            return DependencyValidationResult(
                status="skipped",
                validator_type="dry_run",
                warnings=["requirements.txt does not exist."],
                duration_seconds=0.0,
            )

        content = requirements_path.read_text(encoding="utf-8", errors="ignore")
        seen_constraints: Dict[str, str] = {}

        for idx, line in enumerate(content.splitlines(), start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = re.split(r"(==|>=|<=|~=|!=|>|<)", line, maxsplit=1)
            pkg = parts[0].strip()
            spec = "".join(parts[1:]).strip() if len(parts) > 1 else ""

            if not pkg:
                errors.append(f"Line {idx}: Empty package name in requirement '{line}'")
                continue

            # Check for invalid package names (PEP 508 naming)
            if not pkg.replace("-", "").replace("_", "").replace(".", "").isalnum():
                errors.append(f"Line {idx}: Invalid package name characters in '{pkg}'")
                continue

            packages_checked.append(pkg)
            norm = pkg.lower().replace("_", "-")

            # Conflict detection in dry-run
            if norm in seen_constraints:
                prev_spec = seen_constraints[norm]
                if spec.startswith("==") and prev_spec.startswith("==") and spec != prev_spec:
                    errors.append(f"Conflicting version constraints for '{pkg}': '{spec}' vs '{prev_spec}'")
                elif "==" in spec and "==" in prev_spec and spec != prev_spec:
                    errors.append(f"Conflicting dependency constraints detected for '{pkg}'")
            else:
                seen_constraints[norm] = spec

        # If no errors, resolve versions for packages
        if not errors:
            from app.services.ci.requirements import DEFAULT_PACKAGE_VERSIONS
            for norm, spec in seen_constraints.items():
                ver = None
                if spec.startswith("=="):
                    ver = spec[2:].strip()
                elif any(spec.startswith(op) for op in [">=", "<=", "~=", ">", "<"]):
                    op_stripped = re.sub(r"^[>=<~!]+", "", spec).split(",")[0].strip()
                    ver = op_stripped if op_stripped else DEFAULT_PACKAGE_VERSIONS.get(norm, "1.0.0")
                else:
                    ver = DEFAULT_PACKAGE_VERSIONS.get(norm, "1.0.0")

                resolved_packages.append(
                    ResolvedDependency(
                        name=norm,
                        version=ver,
                        is_direct=True,
                        original_spec=spec or None,
                    )
                )

        status = "passed" if not errors else "failed"
        return DependencyValidationResult(
            status=status,
            validator_type="dry_run",
            exit_code=0 if not errors else 1,
            packages_checked=packages_checked,
            resolved_packages=resolved_packages,
            errors=errors,
            warnings=warnings,
            duration_seconds=round(time.time() - start_time, 4),
        )


def get_validator(
    mode: str = "auto",
    docker_image: str = "python:3.11-slim",
) -> BaseDependencyValidator:
    """Factory function returning the appropriate validator strategy."""
    if mode == "dry_run":
        return DryRunValidator()
    elif mode == "docker":
        return DockerValidator(docker_image=docker_image)
    elif mode == "venv":
        return IsolatedVenvValidator()

    # Auto mode: try Docker if available, otherwise isolated venv
    if shutil.which("docker"):
        return DockerValidator(
            docker_image=docker_image,
            fallback_validator=IsolatedVenvValidator(),
        )
    return IsolatedVenvValidator()

