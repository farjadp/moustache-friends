from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    openai_api_key: str
    telegram_bot_token: str
    telegram_admin_ids: str = ""
    bot_username: str = ""
    chroma_persist_dir: str = "./chroma_db"
    upload_dir: str = "./uploads"
    database_url: str = "sqlite+aiosqlite:///./app.db"
    max_file_size_mb: int = 500
    whisper_model: str = "base"

    @property
    def admin_ids(self) -> List[int]:
        if not self.telegram_admin_ids:
            return []
        return [int(x.strip()) for x in self.telegram_admin_ids.split(",") if x.strip()]

    class Config:
        env_file = ".env"


settings = Settings()
