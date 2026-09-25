from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pathlib import Path
import uuid

from sqlalchemy.orm import Session

from app.services.storage_service import upload_model
from app.database.database import get_db
from app.database.model import Model


router = APIRouter(
    prefix="/models",
    tags=["Models"]
)


async def upload_model_api(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    # 1. Check file extension
    allowed_extensions = [".pkl", ".joblib"]

    extension = Path(file.filename).suffix.lower()

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Only .pkl and .joblib files are supported"
        )

    # 2. Generate unique model ID
    model_id = str(uuid.uuid4())

    # 3. Define cloud storage path
    storage_path = f"models/{model_id}/model{extension}"

    # 4. Read uploaded file
    file_data = await file.read()

    # 5. Upload model to Supabase Storage
    try:
        upload_model(file_data, storage_path)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Model upload failed: {str(e)}"
        )

        model_record = Model(
        model_id=model_id,
        filename=file.filename,
        storage_path=storage_path,
        status="uploaded"
    )

    db.add(model_record)
    db.commit()

    # 6. Return model information
    return {
        "model_id": model_id,
        "filename": file.filename,
        "storage_path": storage_path,
        "status": "uploaded"
    }

