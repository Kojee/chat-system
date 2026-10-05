from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # Absolute paths so settings load the same from any working directory. The repo-root
    # .env is shared by all services; a service-level .env overrides it. Missing files are
    # skipped, and inside Docker the values come from compose environment variables.
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT.parent / ".env", PROJECT_ROOT / ".env"), extra="ignore"
    )

    openai_api_key: SecretStr = Field(min_length=1)  # rejects an empty OPENAI_API_KEY= too
    openai_model: str = "gpt-4o-mini"

    mcp_api_key: str = "dev-key"
    user_mcp_url: str = "http://localhost:8001/mcp"
    kb_mcp_url: str = "http://localhost:8002/mcp"

    summarization_max_tokens: int = 4000
    system_prompt_path: Path = PROJECT_ROOT / "config" / "system_prompt.txt"

    chatdb_dsn: str = "postgresql://chat:chat@localhost:5433/chatdb"

    backend_host: str = "127.0.0.1"
    backend_port: int = 8003


settings = Settings()
