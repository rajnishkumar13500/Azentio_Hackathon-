import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    PROJECT_NAME: str = "Claims Policy Validation Microservice"
    VERSION: str = "1.0.0"
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Groq & AI Configuration
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "qwen-2.5-32b")
    GROQ_BASE_URL: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    
    # File Paths
    BASE_DIR: Path = BASE_DIR
    STATIC_DIR: Path = BASE_DIR / "static"
    DATA_DIR: Path = BASE_DIR / "data"
    POLICIES_FILE: Path = DATA_DIR / "sample_policies.json"
    CATALOG_FILE: Path = DATA_DIR / "medical_catalog.json"
    SYNTHETIC_CLAIMS_FILE: Path = DATA_DIR / "synthetic_claims.json"

settings = Settings()

