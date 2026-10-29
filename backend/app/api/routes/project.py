from typing import List, Optional
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status

from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    ProjectUploadResponse,
)
from app.schemas.validation import ValidationReport
from app.services.project_service import project_service

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", response_model=List[ProjectResponse])
def get_projects():
    """Retrieve all projects."""
    return project_service.list_projects()


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(project: ProjectCreate):
    """Create a new model project."""
    return project_service.create_project(project)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str):
    """Retrieve a project by its unique ID."""
    return project_service.get_project(project_id)


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: str, project_update: ProjectUpdate):
    """Update project metadata or configuration."""
    return project_service.update_project(project_id, project_update)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str):
    """Delete a project."""
    project_service.delete_project(project_id)
    return None


@router.post("/{project_id}/upload", response_model=ProjectUploadResponse)
async def upload_project_file(
    project_id: str,
    file: UploadFile = File(..., description="Model file (.pkl, .onnx, .pt, .bin) or zip archive"),
):
    """Upload model weight or zip archive to project, automatically unpacking if zip."""
    return await project_service.handle_project_upload(project_id, file)


@router.post("/quick-unpack", response_model=ProjectUploadResponse)
async def quick_unpack(
    file: UploadFile = File(..., description="Zip archive containing model files"),
    title: str = Form(default="Quick Model Import"),
):
    """Convenience endpoint: create project and unpack archive in a single call."""
    new_project = project_service.create_project(ProjectCreate(title=title))
    return await project_service.handle_project_upload(new_project.id, file)


@router.post("/{project_id}/validate", response_model=ValidationReport)
@router.get("/{project_id}/validate", response_model=ValidationReport)
async def validate_project(
    project_id: str,
    main_file: Optional[str] = Query(None, description="Optional override path to main entry point file"),
):
    """
    Run automated CI validation pipeline on the extracted project.
    Analyzes project structure, requirements, dependencies, and code syntax.
    Accepts both POST and GET (enabling direct browser address bar execution).
    """
    return await project_service.validate_project(project_id, declared_main_file=main_file)


@router.get("/{project_id}/validation", response_model=ValidationReport)
def get_project_validation(project_id: str):
    """Retrieve the latest CI validation report for the specified project."""
    return project_service.get_project_validation(project_id)
