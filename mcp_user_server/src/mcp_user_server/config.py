from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://user:pass@localhost:5432/userdb"
    host: str = "0.0.0.0"
    port: int = 8001
    csv_path: Path = PROJECT_ROOT / "data" / "customer_data.csv"


settings = Settings()
