import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "Claims Data Ingestion Pipeline"
    API_V1_PREFIX: str = "/api/v1"
    
    # Database
    # Defaults to SQLite for immediate zero-config execution; seamlessly accepts PostgreSQL connection string
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/data/claims_ingestion.db")
    
    # Storage
    STORAGE_DIR: str = os.getenv("STORAGE_DIR", str(BASE_DIR / "storage"))
    SAMPLE_DATA_DIR: str = os.getenv("SAMPLE_DATA_DIR", str(BASE_DIR / "sample_data"))
    
    # Validation settings
    AMOUNT_TOLERANCE: float = 0.05  # rounding tolerance for line items vs total
    MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024  # 50MB
    
    ALLOWED_EXTENSIONS: set = {".csv", ".xlsx", ".json", ".pdf", ".png", ".jpg", ".jpeg"}
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

# Ensure required directories exist
os.makedirs(settings.STORAGE_DIR, exist_ok=True)
os.makedirs(os.path.join(settings.STORAGE_DIR, "uploads"), exist_ok=True)
os.makedirs(os.path.join(settings.STORAGE_DIR, "documents"), exist_ok=True)
os.makedirs(settings.SAMPLE_DATA_DIR, exist_ok=True)
os.makedirs(os.path.dirname(settings.DATABASE_URL.replace("sqlite:///", "")), exist_ok=True)
