from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProjectBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=120, description="Project or model name")
    description: Optional[str] = Field(None, max_length=500, description="Brief description of the model")
    framework: Optional[str] = Field(None, description="Framework used (e.g., PyTorch, Scikit-learn, ONNX, TensorFlow)")
    version: Optional[str] = Field("1.0.0", description="Model version tag")


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=120)
    description: Optional[str] = Field(None, max_length=500)
    framework: Optional[str] = None
    version: Optional[str] = None
    status: Optional[str] = None
    main_file: Optional[str] = None
    requirements_file: Optional[str] = None
    python_version: Optional[str] = None
    python_version_inferred: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class ProjectResponse(ProjectBase):
    id: str
    status: str = "created"
    file_path: Optional[str] = None
    extracted_path: Optional[str] = None
    main_file: Optional[str] = None
    requirements_file: Optional[str] = None
    python_version: Optional[str] = None
    python_version_inferred: Optional[bool] = None
    validation_status: Optional[str] = None
    validation_report: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        from_attributes = True


class ProjectUploadResponse(BaseModel):
    project_id: str
    filename: str
    status: str
    file_path: str
    extracted_files: List[str] = Field(default_factory=list)
    message: str
