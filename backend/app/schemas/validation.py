from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ValidationStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    PENDING = "pending"
    VALIDATING = "validating"


class ProjectCIStatus(str, Enum):
    CREATED = "created"
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    VALIDATED = "validated"
    VALIDATION_FAILED = "validation_failed"


class DetectedDependency(BaseModel):
    name: str = Field(..., description="Canonical PyPI package name")
    version_spec: Optional[str] = Field(None, description="Declared or inferred version constraint")
    source: str = Field("requirements.txt", description="Origin: requirements.txt, inferred, pyproject.toml, etc.")
    inferred: bool = Field(False, description="Whether this dependency was inferred by AST analysis")
    category: Optional[str] = Field(None, description="Category (ml_framework, web_framework, data_processing, utility)")


class ResolvedDependency(BaseModel):
    name: str = Field(..., description="Canonical package name")
    version: str = Field(..., description="Exact pinned resolved version (e.g. '1.5.0')")
    is_direct: bool = Field(True, description="Whether this was a direct dependency or transitive")
    original_spec: Optional[str] = Field(None, description="Original declared version constraint if any")
    category: Optional[str] = Field(None, description="Category (ml_framework, web_framework, data_processing, utility)")


class DependencyValidationResult(BaseModel):
    status: str = Field("passed", description="Validation outcome: passed, failed, warning, skipped")
    validator_type: str = Field("isolated_venv", description="Validator backend used: isolated_venv, docker, dry_run")
    exit_code: Optional[int] = Field(None, description="Process exit code if command was executed")
    packages_checked: List[str] = Field(default_factory=list, description="Packages checked during validation")
    resolved_packages: List[ResolvedDependency] = Field(default_factory=list, description="Resolved packages with versions")
    errors: List[str] = Field(default_factory=list, description="Installation or resolution error messages")
    warnings: List[str] = Field(default_factory=list, description="Installation warnings or non-fatal issues")
    output_snippet: Optional[str] = Field(None, description="Diagnostic stdout/stderr snippet")
    duration_seconds: float = Field(0.0, description="Execution duration in seconds")


class SyntaxErrorDetail(BaseModel):
    file: str = Field(..., description="Relative path of file with syntax error")
    line: Optional[int] = Field(None, description="Line number of syntax error")
    column: Optional[int] = Field(None, description="Column offset of syntax error")
    error_message: str = Field(..., description="Description of the syntax error")
    text: Optional[str] = Field(None, description="Code line text if available")


class SyntaxCheckResult(BaseModel):
    status: str = Field("passed", description="Syntax check outcome: passed, failed")
    total_files: int = Field(0, description="Total Python files checked")
    valid_files: int = Field(0, description="Count of syntactically valid files")
    syntax_errors: List[SyntaxErrorDetail] = Field(default_factory=list, description="Syntax errors detected")
    duration_seconds: float = Field(0.0, description="Execution duration in seconds")


class EntryPointValidationResult(BaseModel):
    status: str = Field("passed", description="Entry point validation outcome: passed, failed, warning")
    detected_entry_point: Optional[str] = Field(None, description="Identified main entry point relative path")
    entry_point_type: Optional[str] = Field(None, description="Type: fastapi, flask, inference_function, cli_script, unknown")
    is_valid: bool = Field(False, description="Whether the main entry point is valid and runnable")
    details: Dict[str, Any] = Field(default_factory=dict, description="Structural details about the entry point")
    warnings: List[str] = Field(default_factory=list, description="Warnings regarding the entry point")


class ProjectStructureInfo(BaseModel):
    total_python_files: int = Field(0, description="Total Python files discovered")
    python_files: List[str] = Field(default_factory=list, description="Relative paths of Python source files")
    config_files: List[str] = Field(default_factory=list, description="Configuration files found")
    detected_frameworks: List[str] = Field(default_factory=list, description="ML/web frameworks detected")
    is_ml_project: bool = Field(False, description="Whether ML libraries or workflows were identified")
    has_requirements: bool = Field(False, description="Whether requirements.txt existed initially")
    has_pyproject: bool = Field(False, description="Whether pyproject.toml was present")
    has_setup: bool = Field(False, description="Whether setup.py/setup.cfg was present")
    has_dockerfile: bool = Field(False, description="Whether Dockerfile was present")
    ignored_paths_count: int = Field(0, description="Number of ignored cache/venv files skipped")


class PythonVersionInfo(BaseModel):
    version: str = Field(..., description="Selected or detected Python version (e.g. '3.11')")
    is_inferred: bool = Field(False, description="Whether the Python version was inferred rather than explicitly declared")
    source: str = Field("default", description="Source: pyproject.toml, Pipfile, .python-version, Dockerfile, inferred, etc.")
    declared_versions: Dict[str, str] = Field(default_factory=dict, description="All declared Python versions mapped by file source")
    conflicts: List[str] = Field(default_factory=list, description="Conflicting version declarations between files")
    supported_candidates: List[str] = Field(default_factory=list, description="Plausible candidate versions evaluated")
    raw_specifier: Optional[str] = Field(None, description="Raw specifier string from configuration")




class DependencyResolutionResult(BaseModel):
    status: str = Field("passed", description="Resolution outcome: passed, failed, warning, skipped")
    resolved_packages: List[ResolvedDependency] = Field(default_factory=list, description="List of resolved pinned packages")
    direct_count: int = Field(0, description="Count of direct dependencies")
    transitive_count: int = Field(0, description="Count of transitive dependencies")
    conflicts: List[str] = Field(default_factory=list, description="Dependency resolution conflicts or incompatible constraints")
    lock_file_generated: bool = Field(False, description="Whether a pinned requirements or lock artifact was generated")
    lock_file_path: Optional[str] = Field(None, description="Relative path of the resolved/pinned requirements file")
    duration_seconds: float = Field(0.0, description="Execution duration in seconds")


class ImportCheckResult(BaseModel):
    status: str = Field("passed", description="Import check outcome: passed, warning, failed")
    missing_imports: List[str] = Field(default_factory=list, description="Imports in code missing from declared/resolved dependencies")
    unused_dependencies: List[str] = Field(default_factory=list, description="Declared packages not directly imported in source code")
    duration_seconds: float = Field(0.0, description="Execution duration in seconds")


class ValidationReport(BaseModel):
    id: str = Field(..., description="Unique report identifier")
    project_id: str = Field(..., description="Associated project ID")
    status: ValidationStatus = Field(ValidationStatus.PASSED, description="Overall validation status: passed, failed, warning")
    project_status: ProjectCIStatus = Field(ProjectCIStatus.VALIDATED, description="Final project status")
    
    # Python Version Stage
    python_version: PythonVersionInfo = Field(
        default_factory=lambda: PythonVersionInfo(version="3.11", is_inferred=True, source="default")
    )
    
    # Requirements existence
    requirements_existed: bool = Field(True, description="Whether requirements.txt existed initially")
    requirements_generated: bool = Field(False, description="Whether requirements.txt was automatically generated")
    
    # Structure & dependencies
    structure: ProjectStructureInfo = Field(default_factory=ProjectStructureInfo, description="Project structural breakdown")
    dependencies: List[DetectedDependency] = Field(default_factory=list, description="Detected dependencies")
    
    # Resolution stage (resolved packages with exact versions)
    dependency_resolution: DependencyResolutionResult = Field(default_factory=DependencyResolutionResult)
    
    # Installation stage (isolated environment verification)
    dependency_validation: DependencyValidationResult = Field(default_factory=DependencyValidationResult)
    
    # Code checks
    syntax_validation: SyntaxCheckResult = Field(default_factory=SyntaxCheckResult)
    import_validation: ImportCheckResult = Field(default_factory=ImportCheckResult)
    entry_point_validation: EntryPointValidationResult = Field(default_factory=EntryPointValidationResult)
    
    # Diagnostic details
    errors: List[str] = Field(default_factory=list, description="Critical errors that caused validation failure")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings and recommendations")
    summary: str = Field("", description="Human-readable summary of validation findings")
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duration_seconds: float = Field(0.0, description="Total pipeline execution duration in seconds")

    class Config:
        from_attributes = True
