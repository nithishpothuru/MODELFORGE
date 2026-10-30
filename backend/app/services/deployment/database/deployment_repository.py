"""
Deployment Repository
Persistent storage layer for deployment records using SQLite and integration with existing backend persistence (Supabase).
Stores deployment_id, project_id, container_id, image_id, allocated_port,
deployment_status (status), health_status (health), public_url, created_at (created_time), and updated_at (updated_time).
Supports full CRUD operations, status updates, and backend sync.
"""

import json
import sqlite3
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, Generator
from datetime import datetime, timezone

from ..config import settings
from ..models.deployment_status import DeploymentStatus
from ..models.deployment_result import DeploymentResult

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = settings.db_path


class DeploymentRepository:
    """Repository layer for persisting, querying, and updating ModelForge deployment records."""

    def __init__(self, db_path: Optional[Union[str, Path]] = None, sync_supabase: bool = True):
        """
        Initialize the SQLite repository.

        Parameters
        ----------
        db_path : Optional[Union[str, Path]]
            Path to SQLite database file.
        sync_supabase : bool
            Whether to attempt syncing deployment updates to Supabase backend.
        """
        self.db_path = str(db_path) if db_path else str(DEFAULT_DB_PATH)
        self.sync_supabase = sync_supabase
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager creating a connection and guaranteeing it closes."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Create tables and indexes if they do not exist."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS deployments (
                    deployment_id TEXT PRIMARY KEY,
                    project_id TEXT,
                    container_id TEXT,
                    image_id TEXT,
                    image_name TEXT,
                    allocated_port INTEGER,
                    deployment_status TEXT NOT NULL,
                    health_status TEXT,
                    public_url TEXT,
                    project_name TEXT,
                    framework TEXT,
                    message TEXT,
                    details TEXT,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_deployments_status 
                ON deployments(deployment_status)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_deployments_project_id 
                ON deployments(project_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_deployments_created_at 
                ON deployments(created_at)
            """)
            conn.commit()

    def create(self, record: Union[DeploymentResult, Dict[str, Any]]) -> str:
        """Alias for save(). Insert or update a deployment record."""
        return self.save(record)

    def save(self, record: Union[DeploymentResult, Dict[str, Any]]) -> str:
        """
        Insert or update a deployment record.

        Parameters
        ----------
        record : Union[DeploymentResult, Dict[str, Any]]

        Returns
        -------
        str
            The deployment ID.
        """
        if isinstance(record, DeploymentResult):
            data = record.model_dump()
        else:
            data = dict(record)

        deployment_id = data.get("deployment_id")
        if not deployment_id:
            raise ValueError("Record must have 'deployment_id'.")

        now = datetime.now(timezone.utc).isoformat()
        created_at = data.get("created_at") or data.get("created_time") or now
        updated_at = data.get("updated_at") or data.get("updated_time") or now

        # Standardize field names
        project_id = data.get("project_id")
        container_id = data.get("container_id")
        image_name = data.get("image_name")
        image_id = data.get("image_id") or image_name
        allocated_port = data.get("allocated_port") if "allocated_port" in data else data.get("host_port")

        dep_status = data.get("deployment_status") or data.get("status") or DeploymentStatus.PENDING.value
        if isinstance(dep_status, DeploymentStatus):
            dep_status = dep_status.value

        health_status = data.get("health_status") or data.get("health") or ("Healthy" if data.get("healthy") else "pending")
        public_url = data.get("public_url") or data.get("proxy_url") or data.get("url")

        project_name = data.get("project_name")
        framework = data.get("framework")
        message = data.get("message")
        details = data.get("details")

        metadata = data.get("metadata") or {}
        if isinstance(metadata, dict):
            metadata = dict(metadata)
            if data.get("startup_command"):
                metadata["startup_command"] = data["startup_command"]
            if data.get("entry_point_type"):
                metadata["entry_point_type"] = data["entry_point_type"]
        metadata_json = json.dumps(metadata) if isinstance(metadata, (dict, list)) else str(metadata)

        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO deployments (
                    deployment_id, project_id, container_id, image_id, image_name,
                    allocated_port, deployment_status, health_status, public_url,
                    project_name, framework, message, details, metadata_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(deployment_id) DO UPDATE SET
                    project_id = coalesce(excluded.project_id, deployments.project_id),
                    container_id = coalesce(excluded.container_id, deployments.container_id),
                    image_id = coalesce(excluded.image_id, deployments.image_id),
                    image_name = coalesce(excluded.image_name, deployments.image_name),
                    allocated_port = coalesce(excluded.allocated_port, deployments.allocated_port),
                    deployment_status = excluded.deployment_status,
                    health_status = coalesce(excluded.health_status, deployments.health_status),
                    public_url = coalesce(excluded.public_url, deployments.public_url),
                    project_name = coalesce(excluded.project_name, deployments.project_name),
                    framework = coalesce(excluded.framework, deployments.framework),
                    message = coalesce(excluded.message, deployments.message),
                    details = coalesce(excluded.details, deployments.details),
                    metadata_json = coalesce(excluded.metadata_json, deployments.metadata_json),
                    updated_at = excluded.updated_at
            """, (
                deployment_id, project_id, container_id, image_id, image_name,
                allocated_port, str(dep_status), health_status, public_url,
                project_name, framework, message, details, metadata_json,
                created_at, updated_at
            ))
            conn.commit()

        logger.info("Saved deployment %s with status %s", deployment_id, dep_status)

        # Sync to backend persistence
        if self.sync_supabase:
            self._sync_backend("save", deployment_id, {
                "project_id": project_id,
                "container_id": container_id,
                "image_id": image_id,
                "allocated_port": allocated_port,
                "status": str(dep_status),
                "health": health_status,
                "public_url": public_url,
                "created_at": created_at,
                "updated_at": updated_at
            })

        return deployment_id

    def get(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a deployment record by ID."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM deployments WHERE deployment_id = ?", (deployment_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_dict(row)

    def get_by_project(self, project_id: str) -> List[Dict[str, Any]]:
        """Retrieve all deployments for a project ID."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM deployments WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,)
            )
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def list_all(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List deployments, optionally filtered by status."""
        with self._connection() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute(
                    "SELECT * FROM deployments WHERE deployment_status = ? ORDER BY created_at DESC",
                    (status,)
                )
            else:
                cursor.execute("SELECT * FROM deployments ORDER BY created_at DESC")
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def update(self, deployment_id: str, fields: Dict[str, Any]) -> bool:
        """
        Update arbitrary fields for a deployment.

        Parameters
        ----------
        deployment_id : str
            The deployment ID.
        fields : Dict[str, Any]
            Dictionary of fields to update.

        Returns
        -------
        bool
            True if row was updated.
        """
        if not fields:
            return False

        allowed_keys = {
            "project_id", "container_id", "image_id", "image_name",
            "allocated_port", "deployment_status", "health_status",
            "public_url", "project_name", "framework", "message",
            "details", "status", "health"
        }

        updates = []
        params = []
        now = datetime.now(timezone.utc).isoformat()

        for k, v in fields.items():
            if k == "status":
                k = "deployment_status"
                if isinstance(v, DeploymentStatus):
                    v = v.value
            elif k == "health":
                k = "health_status"

            if k in allowed_keys:
                updates.append(f"{k} = ?")
                params.append(v)

        if not updates:
            return False

        updates.append("updated_at = ?")
        params.append(now)
        params.append(deployment_id)

        query = f"UPDATE deployments SET {', '.join(updates)} WHERE deployment_id = ?"

        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            conn.commit()
            success = cursor.rowcount > 0

        if success and self.sync_supabase:
            self._sync_backend("update", deployment_id, {**fields, "updated_at": now})

        return success

    def update_status(self,
                      deployment_id: str,
                      status: Union[DeploymentStatus, str],
                      message: Optional[str] = None,
                      details: Optional[str] = None) -> bool:
        """Update deployment status and timestamp."""
        status_str = status.value if isinstance(status, DeploymentStatus) else str(status)
        fields = {"deployment_status": status_str}
        if message is not None:
            fields["message"] = message
        if details is not None:
            fields["details"] = details
        return self.update(deployment_id, fields)

    def update_health(self, deployment_id: str, health_status: str) -> bool:
        """Update health check status."""
        return self.update(deployment_id, {"health_status": health_status})

    def delete(self, deployment_id: str) -> bool:
        """Delete a deployment record."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM deployments WHERE deployment_id = ?", (deployment_id,))
            conn.commit()
            deleted = cursor.rowcount > 0

        if deleted and self.sync_supabase:
            self._sync_backend("delete", deployment_id, {})

        return deleted

    def _sync_backend(self, action: str, deployment_id: str, data: Dict[str, Any]) -> None:
        """
        Synchronize deployment record with existing backend persistence (Supabase).
        Performs non-fatal, safe synchronization.
        """
        try:
            from app.services.supabase_client import get_supabase_client
            client = get_supabase_client()
            if not client:
                return

            payload = {
                "id": deployment_id,
                "project_id": data.get("project_id"),
                "container_id": data.get("container_id"),
                "image_id": data.get("image_id"),
                "allocated_port": data.get("allocated_port"),
                "status": data.get("deployment_status") or data.get("status"),
                "health": data.get("health_status") or data.get("health"),
                "public_url": data.get("public_url"),
                "updated_at": data.get("updated_at")
            }
            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}

            if action == "save":
                payload["created_at"] = data.get("created_at")
                client.table("deployments").upsert(payload).execute()
            elif action == "update":
                client.table("deployments").update(payload).eq("id", deployment_id).execute()
            elif action == "delete":
                client.table("deployments").delete().eq("id", deployment_id).execute()

            # Also update project table deployment status if project_id is known
            proj_id = data.get("project_id")
            status_val = data.get("deployment_status") or data.get("status")
            pub_url = data.get("public_url")
            if proj_id and (status_val or pub_url):
                proj_update = {}
                if status_val:
                    proj_update["deployment_status"] = status_val
                if pub_url:
                    proj_update["deployment_url"] = pub_url
                if proj_update:
                    client.table("projects").update(proj_update).eq("id", proj_id).execute()

        except Exception as exc:
            logger.debug("Non-fatal backend persistence sync notice for deployment %s: %s", deployment_id, exc)

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert SQLite Row to dictionary with parsed metadata and convenient aliases."""
        d = dict(row)
        meta_raw = d.get("metadata_json")
        if meta_raw:
            try:
                d["metadata"] = json.loads(meta_raw)
            except Exception:
                d["metadata"] = meta_raw
        else:
            d["metadata"] = {}

        # Provide aliases requested by specification
        d["status"] = d.get("deployment_status")
        d["health"] = d.get("health_status")
        d["created_time"] = d.get("created_at")
        d["updated_time"] = d.get("updated_at")
        if not d.get("image_id") and d.get("image_name"):
            d["image_id"] = d.get("image_name")

        if isinstance(d.get("metadata"), dict):
            if "startup_command" in d["metadata"] and not d.get("startup_command"):
                d["startup_command"] = d["metadata"]["startup_command"]
            if "entry_point_type" in d["metadata"] and not d.get("entry_point_type"):
                d["entry_point_type"] = d["metadata"]["entry_point_type"]

        return d
