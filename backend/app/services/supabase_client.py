
from functools import lru_cache

from supabase import Client, create_client

from app.config.settings import settings


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    if not settings.SUPABASE_URL or not settings.SUPABASE_SECRET_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SECRET_KEY must be configured in .env"
        )

    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SECRET_KEY,
    )
