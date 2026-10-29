import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.config.settings import settings
from app.schemas.validation import (
    DependencyResolutionResult,
    ImportCheckResult,
    ProjectCIStatus,
    PythonVersionInfo,
    ValidationReport,
    ValidationStatus,
)
from app.services.ci.analyzer import ProjectAnalyzer
from app.services.ci.code_checker import CodeChecker
from app.services.ci.python_detector import PythonVersionDetector
from app.services.ci.requirements import RequirementsHandler
from app.services.ci.validator import BaseDependencyValidator, get_validator


class CIPipeline:
    """Orchestrates the complete Phase 1 CI validation pipeline for an extracted project."""

    def __init__(self, validator: Optional[BaseDependencyValidator] = None):
        self.validator = validator or get_validator(
            mode=settings.VALIDATOR_MODE,
            docker_image=settings.DOCKER_VALIDATOR_IMAGE,
        )

    async def run_pipeline(
        self,
        project_id: str,
        extract_dir: Path,
        declared_main_file: Optional[str] = None,
    ) -> ValidationReport:
        """Execute the end-to-end validation pipeline."""
        start_time = time.time()
        report_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)

        errors = []
        warnings = []

        extract_path = extract_dir.resolve()
        if not extract_path.exists() or not extract_path.is_dir():
            completed_at = datetime.now(timezone.utc)
            duration = round(time.time() - start_time, 2)
            return ValidationReport(
                id=report_id,
                project_id=project_id,
                status=ValidationStatus.FAILED,
                project_status=ProjectCIStatus.VALIDATION_FAILED,
                python_version=PythonVersionInfo(
                    version=settings.DEFAULT_PYTHON_VERSION,
                    is_inferred=True,
                    source="default",
                ),
                requirements_existed=False,
                requirements_generated=False,
                errors=[f"Project extraction directory does not exist: {extract_path}"],
                summary="Validation failed: Extracted project directory not found.",
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
            )

        # -------------------------------------------------------------
        # Phase 1: Project Structure Analysis
        # -------------------------------------------------------------
        analyzer = ProjectAnalyzer(extract_path)
        structure_info, python_files = analyzer.scan_structure()

        entry_point_rel, entry_type, entry_details = analyzer.detect_main_entry_point(
            python_files,
            declared_main=declared_main_file,
        )

        # -------------------------------------------------------------
        # Phase 2: Python Version Detection & Inference
        # -------------------------------------------------------------
        detector = PythonVersionDetector(extract_path)
        python_ver_info = detector.detect_version(python_files=python_files)
        if python_ver_info.conflicts:
            for conf in python_ver_info.conflicts:
                warnings.append(conf)

        # -------------------------------------------------------------
        # Phase 3: Dependency Discovery
        # -------------------------------------------------------------
        req_handler = RequirementsHandler(extract_path)
        existing_req_path = req_handler.find_requirements_file()

        requirements_existed = existing_req_path is not None
        requirements_generated = False
        detected_deps = []

        if requirements_existed and existing_req_path:
            req_deps, req_syntax_errors, req_warnings = req_handler.parse_requirements(existing_req_path)
            detected_deps.extend(req_deps)
            errors.extend(req_syntax_errors)
            warnings.extend(req_warnings)
            active_req_path = existing_req_path
        else:
            # Check metadata files first (pyproject.toml, setup.cfg)
            meta_deps, meta_sources = req_handler.extract_from_metadata_files()
            if meta_deps:
                detected_deps.extend(meta_deps)
                warnings.append(
                    f"Dependencies discovered from metadata: {', '.join(meta_sources)}."
                )

            # Infer from AST imports
            inferred_deps = req_handler.infer_dependencies_from_imports(python_files)
            seen_names = {d.name.lower().replace("_", "-") for d in detected_deps}
            for inf in inferred_deps:
                norm = inf.name.lower().replace("_", "-")
                if norm not in seen_names:
                    detected_deps.append(inf)
                    seen_names.add(norm)

            # Create candidate requirements file for isolated resolution with pinned versions
            active_req_path = req_handler.generate_requirements_file(
                dependencies=detected_deps,
                python_version=python_ver_info.version,
            )

        # -------------------------------------------------------------
        # Phase 4: Dependency Resolution & Isolated Validation
        # -------------------------------------------------------------
        dep_validation = await self.validator.validate(
            requirements_path=active_req_path,
            project_dir=extract_path,
            timeout_seconds=settings.VALIDATION_TIMEOUT_SECONDS,
            python_version=python_ver_info.version,
        )

        resolution_conflicts = list(dep_validation.errors)
        resolution_passed = dep_validation.status == "passed" and not resolution_conflicts

        if dep_validation.errors:
            errors.extend([f"Dependency error: {e}" for e in dep_validation.errors])
        if dep_validation.warnings:
            warnings.extend([f"Dependency warning: {w}" for w in dep_validation.warnings])

        # Resolve pinned packages
        resolved_packages = req_handler.build_resolved_dependencies(
            direct_dependencies=detected_deps,
            validator_resolved=dep_validation.resolved_packages,
        )

        lock_file_path = None
        lock_file_generated = False

        # Generate pinned requirements file
        if not requirements_existed:
            # requirements.txt was missing: generate version-pinned requirements.txt
            req_handler.generate_pinned_requirements_file(
                resolved_dependencies=resolved_packages,
                python_version=python_ver_info.version,
                is_inferred=python_ver_info.is_inferred,
                target_path=extract_path / "requirements.txt",
            )
            requirements_generated = True
            lock_file_path = "requirements.txt"
            lock_file_generated = True
            if resolution_passed:
                warnings.append(
                    f"Generated version-pinned requirements.txt with {len(resolved_packages)} "
                    f"compatible packages for Python {python_ver_info.version}."
                )
        else:
            if resolution_passed:
                # Preserve original requirements.txt and create requirements-resolved.txt
                req_handler.generate_resolved_lock_file(
                    resolved_dependencies=resolved_packages,
                    python_version=python_ver_info.version,
                    is_inferred=python_ver_info.is_inferred,
                )
                requirements_generated = False
                lock_file_path = "requirements-resolved.txt"
                lock_file_generated = True

        resolution_result = DependencyResolutionResult(
            status="passed" if resolution_passed else "failed",
            resolved_packages=resolved_packages if resolution_passed else [],
            direct_count=len([r for r in resolved_packages if r.is_direct]) if resolution_passed else 0,
            transitive_count=len([r for r in resolved_packages if not r.is_direct]) if resolution_passed else 0,
            conflicts=resolution_conflicts,
            lock_file_generated=lock_file_generated,
            lock_file_path=lock_file_path,
            duration_seconds=dep_validation.duration_seconds,
        )

        # -------------------------------------------------------------
        # Phase 5: Code & Configuration Validation
        # -------------------------------------------------------------
        code_checker = CodeChecker(extract_path)
        syntax_res = code_checker.check_syntax(python_files)

        if syntax_res.syntax_errors:
            for s_err in syntax_res.syntax_errors:
                loc = f"line {s_err.line}" if s_err.line else "unknown location"
                errors.append(f"Syntax error in '{s_err.file}' at {loc}: {s_err.error_message}")

        # Check for missing imports
        declared_names = [d.name for d in detected_deps]
        local_modules = req_handler._get_local_module_names()
        missing_imports = code_checker.check_missing_imports(
            python_files,
            declared_names,
            local_modules,
        )
        warnings.extend(missing_imports)

        import_res = ImportCheckResult(
            status="passed" if not missing_imports else "warning",
            missing_imports=missing_imports,
            unused_dependencies=[],
            duration_seconds=0.0,
        )

        # Validate entry point
        entry_validation = code_checker.validate_entry_point(
            entry_point_rel,
            entry_type,
            entry_details,
            syntax_res.syntax_errors,
        )
        if entry_validation.warnings:
            warnings.extend(entry_validation.warnings)

        # -------------------------------------------------------------
        # Phase 6: Result Consolidation & Status Determination
        # -------------------------------------------------------------
        has_critical_failure = (
            bool(errors)
            or syntax_res.status == "failed"
            or dep_validation.status == "failed"
            or resolution_result.status == "failed"
        )

        if has_critical_failure:
            overall_status = ValidationStatus.FAILED
            project_status = ProjectCIStatus.VALIDATION_FAILED
        elif warnings:
            overall_status = ValidationStatus.WARNING
            project_status = ProjectCIStatus.VALIDATED
        else:
            overall_status = ValidationStatus.PASSED
            project_status = ProjectCIStatus.VALIDATED

        # Build human-readable summary
        framework_summary = (
            ", ".join(structure_info.detected_frameworks)
            if structure_info.detected_frameworks
            else "Standard Python (no ML framework detected)"
        )
        main_summary = entry_point_rel or "Not identified"

        py_ver_tag = (
            f"Python {python_ver_info.version} (declared in {python_ver_info.source})"
            if not python_ver_info.is_inferred
            else f"Python {python_ver_info.version} ({python_ver_info.source})"
        )

        summary_lines = [
            f"Validation {overall_status.value.upper()}.",
            f"Target: {py_ver_tag}.",
            f"Frameworks: {framework_summary}.",
            f"Main entry point: {main_summary} (type: {entry_type or 'unknown'}).",
            f"Python files: {syntax_res.valid_files}/{syntax_res.total_files} valid.",
            f"Dependencies: {len(detected_deps)} direct package(s) detected.",
            (
                f"Resolved {len(resolved_packages)} package(s) pinned in {lock_file_path}."
                if lock_file_generated
                else "Dependency resolution could not complete."
            ),
        ]
        if errors:
            summary_lines.append(f"Errors encountered ({len(errors)}): {errors[0]}")
        elif warnings:
            summary_lines.append(f"Warnings ({len(warnings)}): {warnings[0]}")

        summary = " ".join(summary_lines)
        completed_at = datetime.now(timezone.utc)
        duration = round(time.time() - start_time, 2)

        report = ValidationReport(
            id=report_id,
            project_id=project_id,
            status=overall_status,
            project_status=project_status,
            python_version=python_ver_info,
            requirements_existed=requirements_existed,
            requirements_generated=requirements_generated,
            structure=structure_info,
            dependencies=detected_deps,
            dependency_resolution=resolution_result,
            dependency_validation=dep_validation,
            syntax_validation=syntax_res,
            import_validation=import_res,
            entry_point_validation=entry_validation,
            errors=errors,
            warnings=warnings,
            summary=summary,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration,
        )

        # Write report to disk in project directory for persistence
        try:
            report_file = extract_path / "validation_report.json"
            report_file.write_text(
                report.model_dump_json(indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

        return report
