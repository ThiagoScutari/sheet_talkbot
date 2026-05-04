from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str = ""
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ORCHESTRATOR_MODEL: str = "claude-haiku-4-5-20251001"
    ANALYST_MODEL: str = "claude-sonnet-4-20250514"
    DATA_DIR: Path = Path("data")

    @property
    def UPLOAD_DIR(self) -> Path:
        return self.DATA_DIR / "uploads"

    @property
    def EDITED_DIR(self) -> Path:
        return self.DATA_DIR / "edited"

    @property
    def DASHBOARD_DIR(self) -> Path:
        return self.DATA_DIR / "dashboards"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()

for _d in [settings.UPLOAD_DIR, settings.EDITED_DIR, settings.DASHBOARD_DIR]:
    _d.mkdir(parents=True, exist_ok=True)
