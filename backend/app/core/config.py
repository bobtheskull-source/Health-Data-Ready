from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Health Data Ready"
    VERSION: str = "0.1.0"
    
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost/healthdataready"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Password hashing
    BCRYPT_ROUNDS: int = 12
    
    # MFA (placeholder for future)
    MFA_ENABLED: bool = False
    
    # File storage
    STORAGE_BUCKET: str = "health-data-ready"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_UPLOAD_TYPES: list = ["application/pdf", "text/csv", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    
    # Audit
    AUDIT_LOG_RETENTION_DAYS: int = 2555  # 7 years
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
