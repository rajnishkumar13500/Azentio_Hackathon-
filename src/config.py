import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

class Settings:
    PROJECT_NAME: str = "Claims Policy Validation Microservice"
    VERSION: str = "1.0.0"
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Groq & AI Configuration
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "qwen-2.5-32b")
    GROQ_BASE_URL: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    
    # SMTP / Email Configuration (dynamic properties for live updates)
    @property
    def SMTP_HOST(self) -> str:
        load_dotenv(BASE_DIR / ".env", override=True)
        return os.getenv("SMTP_HOST", "").strip()

    @property
    def SMTP_PORT(self) -> int:
        return int(os.getenv("SMTP_PORT", "587"))

    @property
    def SMTP_USER(self) -> str:
        return os.getenv("SMTP_USER", "").strip()

    @property
    def SMTP_PASSWORD(self) -> str:
        return os.getenv("SMTP_PASSWORD", "").strip()

    @property
    def SMTP_FROM(self) -> str:
        return os.getenv("SMTP_FROM", "claims-adjudication@azentio.ai").strip()

    @property
    def SMTP_USE_TLS(self) -> bool:
        return os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")

    # File Paths
    BASE_DIR: Path = BASE_DIR
    STATIC_DIR: Path = BASE_DIR / "static"
    DATA_DIR: Path = BASE_DIR / "data"
    DISPATCHED_EMAILS_DIR: Path = DATA_DIR / "dispatched_emails"
    POLICIES_FILE: Path = DATA_DIR / "sample_policies.json"
    CATALOG_FILE: Path = DATA_DIR / "medical_catalog.json"
    SYNTHETIC_CLAIMS_FILE: Path = DATA_DIR / "synthetic_claims.json"

settings = Settings()
