from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    # Absolute paths so settings load the same from any working directory. The repo-root
    # .env is shared by all services; a service-level .env overrides it. Missing files are
    # skipped, and inside Docker the values come from compose environment variables.
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT.parent / ".env", PROJECT_ROOT / ".env"), extra="ignore"
    )

    database_url: str = "postgresql+psycopg://kb:kb@localhost:5432/kbdb"

    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"

    host: str = "0.0.0.0"
    port: int = 8002

    chroma_path: Path = PROJECT_ROOT / "chroma_data"
    chroma_collection: str = "tax_knowledge"

    docs_path: Path = PROJECT_ROOT / "data"
    chunk_size: int = 1000
    chunk_overlap: int = 150


settings = Settings()
