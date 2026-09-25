import os

from dotenv import load_dotenv
from supabase import create_client, Client


load_dotenv()


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase credentials are missing")


supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


BUCKET_NAME = "modelforge-models"

def upload_model(file_data: bytes, storage_path: str):
    response = supabase.storage.from_(BUCKET_NAME).upload(
        storage_path,
        file_data,
        {
            "content-type": "application/octet-stream"
        }
    )

    return response