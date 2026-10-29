import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import HTTPException, UploadFile, status

from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    ProjectUploadResponse,
)
from app.schemas.validation import ValidationReport
from app.services.ci.pipeline import CIPipeline
from app.services.storage_service import storage_service
from app.services.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class ProjectService:
    def __init__(self):
        # In-memory storage for projects; can be backed by Supabase DB
        self._projects: Dict[str, dict] = {}
        self.ci_pipeline = CIPipeline()

    def list_projects(self) -> List[ProjectResponse]:
        """Return all projects."""
        return [ProjectResponse(**p) for p in self._projects.values()]

    def _resolve_project(self, project_id: str) -> Optional[dict]:
        """Fetch project from memory, or restore it from local uploads and Supabase."""
        project = self._projects.get(project_id)
        if project:
            return project

        # Check local uploads directory
        local_project_dir = Path(storage_service.upload_dir) / project_id
        extract_dir = local_project_dir / "extracted"

        if local_project_dir.exists() and extract_dir.exists():
            now = datetime.now(timezone.utc)
            zips = list(local_project_dir.glob("*.zip"))
            zip_name = zips[0].name if zips else None
            storage_path = f"{project_id}/{zip_name}" if zip_name else None

            project_name = "ModelForge Project"
            status_val = "uploaded"
            main_file = None
            req_file = None

            try:
                client = get_supabase_client()
                db_res = client.table("projects").select("*").eq("id", project_id).execute()
                if db_res.data:
                    row = db_res.data[0]
                    project_name = row.get("project_name", project_name)
                    status_val = row.get("status", status_val)
                    main_file = row.get("main_file")
                    req_file = row.get("requirements_file")
            except Exception:
                pass

            reconstructed = {
                "id": project_id,
                "title": project_name,
                "description": None,
                "framework": None,
                "version": "1.0.0",
                "status": status_val,
                "file_path": storage_path,
                "extracted_path": str(extract_dir.resolve()),
                "main_file": main_file,
                "requirements_file": req_file,
                "python_version": None,
                "python_version_inferred": None,
                "validation_status": None,
                "validation_report": None,
                "metadata": {},
                "created_at": now,
                "updated_at": now,
            }
            self._projects[project_id] = reconstructed
            return reconstructed

        return None

    def get_project(self, project_id: str) -> ProjectResponse:
        """Fetch a project by ID or raise 404."""
        project = self._resolve_project(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID '{project_id}' not found",
            )
        return ProjectResponse(**project)

    def create_project(self, project_in: ProjectCreate) -> ProjectResponse:
        """Create a new project record."""
        project_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        project_dict = {
            "id": project_id,
            "title": project_in.title,
            "description": project_in.description,
            "framework": project_in.framework,
            "version": project_in.version or "1.0.0",
            "status": "created",
            "file_path": None,
            "extracted_path": None,
            "main_file": None,
            "requirements_file": None,
            "python_version": None,
            "python_version_inferred": None,
            "validation_status": None,
            "validation_report": None,
            "metadata": {},
            "created_at": now,
            "updated_at": now,
        }
        self._projects[project_id] = project_dict

        # Attempt to record creation in Supabase DB if configured
        try:
            client = get_supabase_client()
            client.table("projects").insert({
                "id": project_id,
                "project_name": project_in.title,
                "main_file": "main.py",
                "status": "created",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }).execute()
        except Exception as exc:
            logger.debug("Non-fatal Supabase sync warning during create: %s", exc)

        return ProjectResponse(**project_dict)

    def update_project(self, project_id: str, project_in: ProjectUpdate) -> ProjectResponse:
        """Update an existing project."""
        project = self._projects.get(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID '{project_id}' not found",
            )

        update_data = project_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                project[key] = value

        project["updated_at"] = datetime.now(timezone.utc)

        try:
            client = get_supabase_client()
            db_update = {"updated_at": project["updated_at"].isoformat()}
            if "title" in update_data and update_data["title"]:
                db_update["project_name"] = update_data["title"]
            if "status" in update_data and update_data["status"]:
                db_update["status"] = update_data["status"]
            if "main_file" in update_data and update_data["main_file"]:
                db_update["main_file"] = update_data["main_file"]
            if "requirements_file" in update_data and update_data["requirements_file"]:
                db_update["requirements_file"] = update_data["requirements_file"]
            client.table("projects").update(db_update).eq("id", project_id).execute()
        except Exception as exc:
            logger.debug("Non-fatal Supabase sync warning during update: %s", exc)

        return ProjectResponse(**project)

    def delete_project(self, project_id: str) -> bool:
        """Delete a project by ID."""
        if project_id not in self._projects:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID '{project_id}' not found",
            )
        del self._projects[project_id]

        try:
            client = get_supabase_client()
            client.table("projects").delete().eq("id", project_id).execute()
        except Exception as exc:
            logger.debug("Non-fatal Supabase delete warning: %s", exc)

        return True

    async def handle_project_upload(
        self,
        project_id: str,
        file: UploadFile,
    ) -> ProjectUploadResponse:
        """Upload a file to Supabase and extract ZIPs for CI processing."""
        project = self._projects.get(project_id)

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID '{project_id}' not found",
            )

        saved_path = None
        storage_path = None

        try:
            saved_path, storage_path = (
                await storage_service.save_upload_file(
                    file,
                    subfolder=project_id,
                )
            )

            extracted_files: List[str] = []
            is_zip = saved_path.suffix.lower() == ".zip"

            if is_zip:
                extract_dir = saved_path.parent / "extracted"
                extracted_files = storage_service.extract_zip(
                    saved_path,
                    extract_to=extract_dir,
                )

                project["extracted_path"] = str(extract_dir)
                project["metadata"]["extracted_files"] = extracted_files
                project["status"] = "uploaded"

                # Upload all unzipped files directly into the project folder in Supabase Storage
                try:
                    uploaded_supabase_files = storage_service.upload_directory_to_supabase(
                        local_dir=extract_dir,
                        storage_prefix=project_id,
                    )
                    project["metadata"]["supabase_extracted_files"] = uploaded_supabase_files

                    # Remove any raw zip archives and clean up any legacy extracted/ folder from Supabase Storage
                    client = get_supabase_client()
                    client.storage.from_(settings.SUPABASE_BUCKET).remove([
                        f"{project_id}/{saved_path.name}",
                        f"{project_id}/Sample ML MODEL.zip",
                        f"{project_id}/model.zip",
                    ])
                    try:
                        legacy_items = client.storage.from_(settings.SUPABASE_BUCKET).list(f"{project_id}/extracted")
                        if legacy_items:
                            client.storage.from_(settings.SUPABASE_BUCKET).remove([
                                f"{project_id}/extracted/{item['name']}" for item in legacy_items if item.get('name')
                            ])
                    except Exception:
                        pass
                except Exception as exc:
                    logger.debug("Non-fatal Supabase sync of extracted files warning: %s", exc)
            else:
                project["status"] = "uploaded"

            # Keep the Supabase path in the API metadata,
            # not the machine-specific local path.
            project["file_path"] = storage_path
            now = datetime.now(timezone.utc)
            project["updated_at"] = now

            # Sync upload metadata to Supabase DB if possible
            try:
                client = get_supabase_client()
                client.table("projects").upsert({
                    "id": project_id,
                    "project_name": project.get("title") or "ModelForge Project",
                    "main_file": project.get("main_file") or "main.py",
                    "zip_path": storage_path,
                    "status": "uploaded",
                    "updated_at": now.isoformat(),
                }).execute()
            except Exception as exc:
                logger.debug("Non-fatal Supabase DB upload update error: %s", exc)

            return ProjectUploadResponse(
                project_id=project_id,
                filename=file.filename or saved_path.name,
                status=project["status"],
                file_path=storage_path,
                extracted_files=extracted_files,
                message=(
                    "File uploaded to Supabase and ZIP extracted successfully"
                    if is_zip
                    else "File uploaded to Supabase successfully"
                ),
            )

        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    "Upload or extraction failed. Check the Supabase "
                    "bucket, credentials, and backend logs."
                ),
            ) from exc

    async def validate_project(
        self,
        project_id: str,
        declared_main_file: Optional[str] = None,
    ) -> ValidationReport:
        """Run the CI validation pipeline on an uploaded and extracted project."""
        project = self._resolve_project(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID '{project_id}' not found",
            )

        extracted_path_str = project.get("extracted_path")
        if not extracted_path_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project has no extracted files to validate. Please upload a project archive first.",
            )

        extract_dir = Path(extracted_path_str)
        if not extract_dir.exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Extracted directory '{extracted_path_str}' no longer exists on disk.",
            )

        # Transition status to validating
        project["status"] = "validating"
        project["updated_at"] = datetime.now(timezone.utc)

        try:
            client = get_supabase_client()
            client.table("projects").update({
                "status": "validating",
                "updated_at": project["updated_at"].isoformat(),
            }).eq("id", project_id).execute()
        except Exception:
            pass

        # Execute full automated pipeline
        main_candidate = declared_main_file or project.get("main_file")
        report = await self.ci_pipeline.run_pipeline(
            project_id=project_id,
            extract_dir=extract_dir,
            declared_main_file=main_candidate,
        )

        # Update project state based on pipeline results
        project["status"] = report.project_status.value
        project["validation_status"] = report.status.value
        project["validation_report"] = report.model_dump()
        project["metadata"]["validation_report"] = report.model_dump()
        project["python_version"] = report.python_version.version
        project["python_version_inferred"] = report.python_version.is_inferred

        if report.entry_point_validation.detected_entry_point:
            project["main_file"] = report.entry_point_validation.detected_entry_point

        # If a resolved lock file (requirements-resolved.txt) was produced, upload it to Supabase Storage
        resolved_req_file = extract_dir / "requirements-resolved.txt"
        if resolved_req_file.exists():
            try:
                storage_service.upload_file_to_supabase(
                    local_path=resolved_req_file,
                    storage_path=f"{project_id}/requirements-resolved.txt",
                    content_type="text/plain",
                )
            except Exception as exc:
                logger.debug("Non-fatal Supabase requirements-resolved.txt upload warning: %s", exc)

        # Upload created/existing requirements.txt to Supabase Storage
        req_candidates = list(extract_dir.rglob("requirements.txt"))
        if req_candidates:
            req_file = req_candidates[0]
            try:
                storage_req_path = f"{project_id}/requirements.txt"
                storage_service.upload_file_to_supabase(
                    local_path=req_file,
                    storage_path=storage_req_path,
                    content_type="text/plain",
                )
                project["requirements_file"] = storage_req_path

                # If requirements.txt was generated in a nested folder, sync there too
                rel_nested = str(req_file.relative_to(extract_dir)).replace("\\", "/")
                if rel_nested != "requirements.txt":
                    storage_service.upload_file_to_supabase(
                        local_path=req_file,
                        storage_path=f"{project_id}/{rel_nested}",
                        content_type="text/plain",
                    )
            except Exception as exc:
                logger.debug("Non-fatal Supabase requirements.txt upload warning: %s", exc)
                project["requirements_file"] = "requirements.txt"
        elif report.requirements_existed or report.requirements_generated:
            project["requirements_file"] = "requirements.txt"

        # Also upload the validation report to Supabase Storage
        report_file = extract_dir / "validation_report.json"
        if report_file.exists():
            try:
                storage_service.upload_file_to_supabase(
                    local_path=report_file,
                    storage_path=f"{project_id}/validation_report.json",
                    content_type="application/json",
                )
            except Exception as exc:
                logger.debug("Non-fatal Supabase validation_report.json upload warning: %s", exc)

        # Remove any lingering zip files or extracted/ leftovers from Supabase Storage for this project
        try:
            client = get_supabase_client()
            client.storage.from_(settings.SUPABASE_BUCKET).remove([
                f"{project_id}/Sample ML MODEL.zip",
                f"{project_id}/model.zip",
            ])
            legacy_items = client.storage.from_(settings.SUPABASE_BUCKET).list(f"{project_id}/extracted")
            if legacy_items:
                client.storage.from_(settings.SUPABASE_BUCKET).remove([
                    f"{project_id}/extracted/{item['name']}" for item in legacy_items if item.get('name')
                ])
        except Exception:
            pass

        if report.structure.detected_frameworks and not project.get("framework"):
            project["framework"] = report.structure.detected_frameworks[0]

        now = datetime.now(timezone.utc)
        project["updated_at"] = now

        # Sync final validation results with Supabase DB
        try:
            client = get_supabase_client()
            db_update = {
                "status": project["status"],
                "updated_at": now.isoformat(),
            }
            if project.get("main_file"):
                db_update["main_file"] = project["main_file"]
            if project.get("requirements_file"):
                db_update["requirements_file"] = project["requirements_file"]

            client.table("projects").update(db_update).eq("id", project_id).execute()
        except Exception as exc:
            logger.debug("Non-fatal Supabase update warning: %s", exc)

        return report

    def get_project_validation(self, project_id: str) -> ValidationReport:
        """Retrieve the latest validation report for a project."""
        project = self._resolve_project(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID '{project_id}' not found",
            )

        report_data = project.get("validation_report")
        if not report_data:
            # Fallback: check if validation_report.json exists on disk
            extracted_path = project.get("extracted_path")
            if extracted_path:
                disk_report = Path(extracted_path) / "validation_report.json"
                if disk_report.exists():
                    try:
                        report_data = json.loads(disk_report.read_text(encoding="utf-8"))
                        project["validation_report"] = report_data
                    except Exception:
                        pass

        if not report_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No validation report found for project '{project_id}'. Initiate validation first.",
            )

        return ValidationReport(**report_data)


project_service = ProjectService()
