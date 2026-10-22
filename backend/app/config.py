from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"
    db_path: str = "data/memory.db"
    learn_threshold: int = 3
    # Optional: your tunnel address (e.g. https://abc.trycloudflare.com) so the
    # AI apps page can show ready-made ChatGPT / claude.ai links.
    public_mcp_url: str = ""
    # Password for people opening the app through a public link (make share).
    # You on localhost never need it.
    app_password: str = ""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_path(self) -> Path:
        path = Path(self.db_path)
        return path if path.is_absolute() else Path(__file__).resolve().parents[1] / path


settings = Settings()
