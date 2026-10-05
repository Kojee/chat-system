from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str
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
