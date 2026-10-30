from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.config.settings import settings
from app.api.routes.project import router as project_router
from app.api.routes.deployment import router as deployment_router
from app.services.supabase_client import get_supabase_client


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="High-performance backend API for ModelForge ML model packaging and deployment.",
    version="0.1.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# Enable CORS for frontend clients
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Register API routers
app.include_router(project_router, prefix=settings.API_V1_STR)
app.include_router(deployment_router, prefix=settings.API_V1_STR)

@app.get("/", tags=["Health"])
def root():
    """Root endpoint verifying API liveness and providing documentation paths."""
    return {
        "service": settings.PROJECT_NAME,
        "status": "online",
        "docs_url": f"{settings.API_V1_STR}/docs",
        "version": "0.1.0",
    }


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint for orchestration and uptime monitoring."""
    return {"status": "ok"}


@app.get("/health/supabase", tags=["Health"])
def supabase_health_check():
    """Verify that the backend can query the Supabase projects table."""
    try:
        client = get_supabase_client()
        client.table("projects").select("id").limit(1).execute()

        return {
            "status": "ok",
            "message": "Supabase database connection successful",
        }
    except Exception:
        raise HTTPException(
            status_code=503,
            detail=(
                "Supabase check failed. Verify environment variables, "
                "projects table, and database permissions."
            ),
        )


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
