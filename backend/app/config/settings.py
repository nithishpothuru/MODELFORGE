import json
from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "ModelForge API"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Supabase Configuration
    SUPABASE_URL: str = ""
    SUPABASE_PUBLISHABLE_KEY: str = ""
    SUPABASE_SECRET_KEY: str = ""
    SUPABASE_BUCKET: str = "ml-forge-data"

    # Local fallback storage / working directory
    UPLOAD_DIR: str = "./uploads"

    # CI Validation Pipeline Configuration
    VALIDATOR_MODE: str = "auto"  # auto, venv, docker, dry_run
    VALIDATION_TIMEOUT_SECONDS: int = 180
    DOCKER_VALIDATOR_IMAGE: str = "python:3.11-slim"
    DEFAULT_PYTHON_VERSION: str = "3.11"
    SUPPORTED_PYTHON_VERSIONS: List[str] = ["3.9", "3.10", "3.11", "3.12"]
    PIN_RESOLVED_REQUIREMENTS: bool = True

    # CORS origins
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env", str(Path(__file__).resolve().parent.parent.parent / ".env")),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
