from fastapi import FastAPI

from app.api.models import router as model_router
from app.database.database import init_db


init_db()

app = FastAPI(
    title="ModelForge API",
    description="ML Model Deployment Platform",
    version="1.0.0"
)


app.include_router(model_router)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "ModelForge Backend"
    }