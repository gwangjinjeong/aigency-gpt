# backend/app/core/config.py
import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    # API 설정
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "PDF Vectorization API"
    VERSION: str = "1.0.0"

    # Supabase 설정
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_BUCKET_NAME: str = "pdf-documents"

    # OpenAI 설정
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # ChromaDB 설정
    CHROMA_DB_PATH: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "pdf_document_embeddings"

    # 파일 업로드 설정
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_FILE_TYPES: list = [".pdf"]

    # 처리 설정
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # CORS 설정
    BACKEND_CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]

    class Config:
        case_sensitive = True


settings = Settings()


# 환경 변수 검증
def validate_environment():
    """필수 환경 변수가 설정되어 있는지 확인"""
    required_vars = {
        "SUPABASE_URL": settings.SUPABASE_URL,
        "SUPABASE_KEY": settings.SUPABASE_KEY,
        "OPENAI_API_KEY": settings.OPENAI_API_KEY
    }

    missing_vars = [var for var, value in required_vars.items() if not value]

    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    return True


if __name__ == "__main__":
    try:
        validate_environment()
        print("✅ All environment variables are set correctly")
        print(f"Supabase URL: {settings.SUPABASE_URL}")
        print(f"Bucket Name: {settings.SUPABASE_BUCKET_NAME}")
    except ValueError as e:
        print(f"❌ {e}")