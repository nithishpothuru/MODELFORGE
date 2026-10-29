import ast
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from app.schemas.validation import (
    EntryPointValidationResult,
    SyntaxCheckResult,
    SyntaxErrorDetail,
)
from app.services.ci.requirements import (
    IMPORT_TO_DISTRIBUTION_MAP,
    STANDARD_LIBRARY_MODULES,
)


class CodeChecker:
    """Validates Python syntax, detects undeclared imports, and validates entry points."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir.resolve()

    def check_syntax(self, python_files: List[Path]) -> SyntaxCheckResult:
        """
        Compile all Python source files to check for syntax errors without executing them.
        """
        start_time = time.time()
        syntax_errors: List[SyntaxErrorDetail] = []
        valid_count = 0

        for py_file in python_files:
            rel_str = str(py_file.relative_to(self.project_dir)).replace("\\", "/")
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                # compile with 'exec' strictly parses and compiles without running
                compile(content, rel_str, "exec", dont_inherit=True)
                valid_count += 1
            except SyntaxError as err:
                detail = SyntaxErrorDetail(
                    file=rel_str,
                    line=err.lineno,
                    column=err.offset,
                    error_message=err.msg or "Syntax error",
                    text=err.text.strip() if err.text else None,
                )
                syntax_errors.append(detail)
            except Exception as exc:
                detail = SyntaxErrorDetail(
                    file=rel_str,
                    line=None,
                    column=None,
                    error_message=f"Failed to read or compile file: {exc}",
                    text=None,
                )
                syntax_errors.append(detail)

        status = "passed" if not syntax_errors else "failed"
        duration = round(time.time() - start_time, 4)

        return SyntaxCheckResult(
            status=status,
            total_files=len(python_files),
            valid_files=valid_count,
            syntax_errors=syntax_errors,
            duration_seconds=duration,
        )

    def check_missing_imports(
        self,
        python_files: List[Path],
        declared_package_names: List[str],
        local_modules: Set[str],
    ) -> List[str]:
        """
        Identify top-level imports that are not in the standard library,
        not in local project packages, and not present in declared requirements.
        """
        missing_warnings: List[str] = []

        # Normalize declared package names
        norm_declared = {
            pkg.lower().replace("_", "-")
            for pkg in declared_package_names
        }

        # Track usage of imports per file
        module_usage: Dict[str, Set[str]] = {}

        for py_file in python_files:
            rel_str = str(py_file.relative_to(self.project_dir)).replace("\\", "/")
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(content, filename=str(py_file))
                for node in ast.walk(tree):
                    mod_name = None
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            mod_name = alias.name.split(".")[0]
                    elif isinstance(node, ast.ImportFrom):
                        if node.level == 0 and node.module:
                            mod_name = node.module.split(".")[0]

                    if mod_name and not mod_name.startswith("_"):
                        module_usage.setdefault(mod_name, set()).add(rel_str)
            except Exception:
                continue

        for mod, files in module_usage.items():
            if mod in STANDARD_LIBRARY_MODULES:
                continue
            if mod in local_modules:
                continue

            # Map import name to PyPI package name
            dist_name = IMPORT_TO_DISTRIBUTION_MAP.get(mod, mod)
            norm_dist = dist_name.lower().replace("_", "-")

            if norm_dist not in norm_declared:
                files_preview = ", ".join(sorted(list(files))[:2])
                if len(files) > 2:
                    files_preview += f" and {len(files) - 2} other(s)"
                missing_warnings.append(
                    f"Module '{mod}' (PyPI package '{dist_name}') is imported in {files_preview} "
                    f"but is not declared in requirements.txt."
                )

        return missing_warnings

    def validate_entry_point(
        self,
        entry_point_rel: Optional[str],
        entry_type: Optional[str],
        details: Dict[str, Any],
        syntax_errors: List[SyntaxErrorDetail],
    ) -> EntryPointValidationResult:
        """
        Validate the discovered or declared main application file.
        """
        warnings: List[str] = []

        if not entry_point_rel:
            return EntryPointValidationResult(
                status="warning",
                detected_entry_point=None,
                entry_point_type="unknown",
                is_valid=False,
                details={},
                warnings=["No primary application entry point (e.g. main.py, app.py) could be identified."],
            )

        # Check if the entry point had syntax errors
        has_syntax_error = any(e.file == entry_point_rel for e in syntax_errors)
        if has_syntax_error:
            return EntryPointValidationResult(
                status="failed",
                detected_entry_point=entry_point_rel,
                entry_point_type=entry_type or "unknown",
                is_valid=False,
                details=details,
                warnings=[f"Entry point file '{entry_point_rel}' contains syntax errors."],
            )

        # Evaluate suitability of the entry point
        is_valid = True
        status = "passed"

        if entry_type == "fastapi":
            instances = details.get("fastapi_app_instances", [])
            if not instances:
                warnings.append(f"FastAPI imported in '{entry_point_rel}', but no app instance assigned.")
        elif entry_type == "flask":
            instances = details.get("flask_app_instances", [])
            if not instances:
                warnings.append(f"Flask imported in '{entry_point_rel}', but no app instance assigned.")
        elif entry_type == "inference_function":
            funcs = details.get("inference_functions", [])
            if not funcs:
                warnings.append(f"Inference functions expected in '{entry_point_rel}' but none found.")
        elif entry_type == "cli_script":
            if not details.get("has_main_guard"):
                warnings.append(f"Script '{entry_point_rel}' lacks '__main__' guard block.")
        elif entry_type == "unknown":
            is_valid = False
            status = "warning"
            warnings.append(f"Entry point '{entry_point_rel}' structure could not be classified.")

        return EntryPointValidationResult(
            status=status,
            detected_entry_point=entry_point_rel,
            entry_point_type=entry_type,
            is_valid=is_valid,
            details=details,
            warnings=warnings,
        )
