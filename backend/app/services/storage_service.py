
import io
import mimetypes
import shutil
import stat
import zipfile
from pathlib import Path, PurePosixPath
from typing import List, Optional, Tuple

from fastapi import UploadFile

from app.config.settings import settings
from app.services.supabase_client import get_supabase_client


MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # 100 MB
MAX_EXTRACTED_BYTES = 500 * 1024 * 1024  # 500 MB
MAX_ARCHIVE_FILES = 5000


class StorageService:
    def __init__(self):
        backend_uploads = Path(__file__).resolve().parent.parent.parent / "uploads"
        self.upload_dir = backend_uploads.resolve() if backend_uploads.exists() else Path(settings.UPLOAD_DIR).resolve()
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _safe_filename(filename: str) -> str:
        # Handle both Windows and Unix-style paths.
        name = filename.replace("\\", "/").split("/")[-1]

        if not name or name in {".", ".."}:
            raise ValueError("Invalid uploaded filename")

        return name

    @staticmethod
    def _validate_zip(content: bytes) -> None:
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                members = archive.infolist()

                if len(members) > MAX_ARCHIVE_FILES:
                    raise ValueError("ZIP contains too many files")

                total_size = 0

                for member in members:
                    if "\x00" in member.filename:
                        raise ValueError("ZIP contains an unsafe file path")

                    normalized = member.filename.replace("\\", "/")
                    path = PurePosixPath(normalized)

                    if (
                        path.is_absolute()
                        or ".." in path.parts
                        or ":" in path.parts[0]
                    ):
                        raise ValueError(
                            "ZIP contains an unsafe file path"
                        )

                    unix_mode = member.external_attr >> 16
                    if stat.S_ISLNK(unix_mode):
                        raise ValueError(
                            "ZIP contains a symbolic link"
                        )

                    # Guard against zip-bomb compression ratios on large payloads
                    if member.compress_size > 0 and member.file_size > 10 * 1024 * 1024:
                        ratio = member.file_size / member.compress_size
                        if ratio > 100:
                            raise ValueError("ZIP appears to be an archive bomb (excessive compression ratio)")

                    total_size += member.file_size

                    if total_size > MAX_EXTRACTED_BYTES:
                        raise ValueError(
                            "Extracted ZIP would exceed 500 MB"
                        )

                if not members:
                    raise ValueError("ZIP archive is empty")

        except zipfile.BadZipFile as exc:
            raise ValueError("Uploaded file is not a valid ZIP archive") from exc

    def extract_zip(
        self,
        zip_path: Path,
        extract_to: Path | None = None,
    ) -> List[str]:
        if extract_to is None:
            extract_to = zip_path.parent / "extracted"

        extract_to = extract_to.resolve()

        # Start from a clean directory to avoid mixing old files
        # with files from the current archive.
        if extract_to.exists():
            shutil.rmtree(extract_to)

        extract_to.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, "r") as archive:
                # Validate every member before extracting any member.
                for member in archive.infolist():
                    normalized = member.filename.replace("\\", "/")
                    relative = PurePosixPath(normalized)

                    if (
                        relative.is_absolute()
                        or ".." in relative.parts
                        or ":" in relative.parts[0]
                    ):
                        raise ValueError(
                            "ZIP contains an unsafe file path"
                        )

                    destination = (
                        extract_to.joinpath(*relative.parts)
                    ).resolve()

                    if not destination.is_relative_to(extract_to):
                        raise ValueError(
                            "ZIP contains a path outside the extraction directory"
                        )

                    unix_mode = member.external_attr >> 16
                    if stat.S_ISLNK(unix_mode):
                        raise ValueError(
                            "ZIP contains a symbolic link"
                        )

                archive.extractall(extract_to)

        except Exception:
            shutil.rmtree(extract_to, ignore_errors=True)
            raise

        return [
            str(file.relative_to(extract_to))
            for file in extract_to.rglob("*")
            if file.is_file()
        ]

    async def save_upload_file(
        self,
        upload_file: UploadFile,
        subfolder: str,
    ) -> Tuple[Path, str]:
        filename = self._safe_filename(upload_file.filename or "")

        content = await upload_file.read(MAX_UPLOAD_BYTES + 1)

        if not content:
            raise ValueError("Uploaded file is empty")

        if len(content) > MAX_UPLOAD_BYTES:
            raise ValueError("Upload exceeds the 100 MB limit")

        is_zip = filename.lower().endswith(".zip")

        if is_zip:
            self._validate_zip(content)

        project_dir = self.upload_dir / subfolder
        project_dir.mkdir(parents=True, exist_ok=True)

        local_path = project_dir / filename

        # Keep a local copy for extraction and CI
        local_path.write_bytes(content)

        # Do NOT upload raw zip to Supabase Storage; unzipped files will be uploaded instead
        if is_zip:
            return local_path, f"{subfolder}/"

        # For non-archive files, upload to Supabase Storage directly
        storage_path = f"{subfolder}/{filename}"
        try:
            client = get_supabase_client()
            client.storage.from_(settings.SUPABASE_BUCKET).upload(
                path=storage_path,
                file=content,
                file_options={
                    "content-type": (
                        upload_file.content_type
                        or "application/octet-stream"
                    ),
                    "upsert": "true",
                },
            )
            return local_path, storage_path
        except Exception:
            local_path.unlink(missing_ok=True)
            raise

    def list_files(self, subfolder: str = "") -> List[str]:
        target = (self.upload_dir / subfolder).resolve()

        if not target.is_relative_to(self.upload_dir):
            raise ValueError("Invalid directory")

        if not target.exists():
            return []

        return [
            file.name
            for file in target.iterdir()
            if file.is_file()
        ]

    def upload_file_to_supabase(
        self,
        local_path: Path,
        storage_path: str,
        content_type: Optional[str] = None,
    ) -> str:
        """Upload an individual file to Supabase Storage."""
        if not local_path.exists() or not local_path.is_file():
            raise ValueError(f"File not found: {local_path}")

        if not content_type:
            content_type, _ = mimetypes.guess_type(str(local_path))
            if not content_type:
                content_type = (
                    "text/plain"
                    if local_path.suffix in [".txt", ".py", ".md", ".json", ".yaml", ".yml"]
                    else "application/octet-stream"
                )

        client = get_supabase_client()
        client.storage.from_(settings.SUPABASE_BUCKET).upload(
            path=storage_path,
            file=local_path.read_bytes(),
            file_options={
                "content-type": content_type,
                "upsert": "true",
            },
        )
        return storage_path

    def upload_directory_to_supabase(
        self,
        local_dir: Path,
        storage_prefix: str,
    ) -> List[str]:
        """Upload all files from a directory to Supabase Storage under storage_prefix."""
        uploaded_paths: List[str] = []
        if not local_dir.exists() or not local_dir.is_dir():
            return uploaded_paths

        client = get_supabase_client()
        for item in local_dir.rglob("*"):
            if not item.is_file():
                continue

            rel_str = str(item.relative_to(local_dir)).replace("\\", "/")
            storage_path = f"{storage_prefix}/{rel_str}".replace("//", "/")

            content_type, _ = mimetypes.guess_type(str(item))
            if not content_type:
                if item.suffix in [".txt", ".py", ".md", ".json", ".yaml", ".yml"]:
                    content_type = "text/plain"
                else:
                    content_type = "application/octet-stream"

            try:
                client.storage.from_(settings.SUPABASE_BUCKET).upload(
                    path=storage_path,
                    file=item.read_bytes(),
                    file_options={
                        "content-type": content_type,
                        "upsert": "true",
                    },
                )
                uploaded_paths.append(storage_path)
            except Exception:
                pass

        return uploaded_paths

    def download_directory_from_supabase(
        self,
        storage_prefix: str,
        local_dir: Path,
    ) -> List[Path]:
        """Download all files from Supabase Storage under storage_prefix to local_dir."""
        downloaded: List[Path] = []
        client = get_supabase_client()
        local_dir.mkdir(parents=True, exist_ok=True)

        def _download_prefix(curr_prefix: str, curr_target: Path):
            try:
                items = client.storage.from_(settings.SUPABASE_BUCKET).list(curr_prefix)
            except Exception:
                return

            for item in items:
                name = item.get("name")
                if not name or name.startswith("."):
                    continue

                is_file = bool(item.get("id") or item.get("metadata"))
                remote_item_path = f"{curr_prefix}/{name}".replace("//", "/")
                local_item_path = curr_target / name

                if is_file:
                    try:
                        content = client.storage.from_(settings.SUPABASE_BUCKET).download(remote_item_path)
                        local_item_path.parent.mkdir(parents=True, exist_ok=True)
                        local_item_path.write_bytes(content)
                        downloaded.append(local_item_path)
                    except Exception:
                        pass
                else:
                    local_item_path.mkdir(parents=True, exist_ok=True)
                    _download_prefix(remote_item_path, local_item_path)

        _download_prefix(storage_prefix, local_dir)
        return downloaded

    def delete_local_project_dir(self, project_id: str) -> None:
        """Remove the local uploads directory for a project."""
        target = self.upload_dir / project_id
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)


storage_service = StorageService()

