import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """
    Centraliza la configuración leída desde .env / entorno.
    .env SIGUE SIENDO la fuente de valores; este archivo solo los expone tipados
    y en un lugar único para el resto del código.
    """
    MODEL: str = os.getenv("MODEL", "gemini-2.5-flash")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    # DB Tool
    DB_TOOL_URL: str = os.getenv("DB_TOOL_URL")
    DB_TOOL_AUTH: str | None = os.getenv("DB_TOOL_AUTH")
    DB_TOOL_TIMEOUT_SECONDS: int = int(os.getenv("DB_TOOL_TIMEOUT_SECONDS", "25"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Retry / backoff
    RETRY_MAX_ATTEMPTS: int = int(os.getenv("RETRY_MAX_ATTEMPTS", "3"))
    RETRY_BASE_BACKOFF_SECONDS: float = float(os.getenv("RETRY_BASE_BACKOFF_SECONDS", "1.0"))
    RETRY_MAX_BACKOFF_SECONDS: float = float(os.getenv("RETRY_MAX_BACKOFF_SECONDS", "10.0"))
    RETRY_JITTER: float = float(os.getenv("RETRY_JITTER", "0.2"))

settings = Settings()
