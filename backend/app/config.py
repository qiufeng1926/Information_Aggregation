from pathlib import Path
from urllib.parse import quote_plus

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "达人信息聚合系统"
    DEBUG: bool = True

    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "app_user"
    DB_PASSWORD: str = "app123"
    DB_NAME: str = "influencer_db"
    DATABASE_URL: str = ""

    MYSQL_ROOT_PASSWORD: str = ""

    REDIS_URL: str = "redis://localhost:6379/0"

    SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # 采集模式: mock(模拟) / api(星图API) / browser(Playwright星图自动化，推荐)
    COLLECTOR_MODE: str = "browser"
    DOUYIN_API_TOKEN: str = ""
    DOUYIN_API_BASE: str = "https://open.douyin.com"
    DOUYIN_COOKIE: str = ""
    XINGTU_COOKIE: str = ""
    XINGTU_COOKIE_FILE: str = ""
    XINGTU_STORAGE_STATE: str = "cookies/xingtu_state.json"

    # Playwright 配置
    PLAYWRIGHT_HEADLESS: bool = False
    PLAYWRIGHT_SLOW_MO: int = 80
    PLAYWRIGHT_TIMEOUT: int = 60000
    PLAYWRIGHT_WAIT_AFTER_SEARCH: int = 5000
    PLAYWRIGHT_FALLBACK_MOCK: bool = False
    PLAYWRIGHT_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )

    @model_validator(mode="after")
    def build_database_url(self) -> "Settings":
        if not self.DATABASE_URL:
            password = quote_plus(self.DB_PASSWORD)
            self.DATABASE_URL = (
                f"mysql+pymysql://{self.DB_USER}:{password}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
            )

        if self.XINGTU_STORAGE_STATE and not Path(self.XINGTU_STORAGE_STATE).is_absolute():
            self.XINGTU_STORAGE_STATE = str(BACKEND_DIR / self.XINGTU_STORAGE_STATE)

        if self.XINGTU_COOKIE_FILE and not Path(self.XINGTU_COOKIE_FILE).is_absolute():
            self.XINGTU_COOKIE_FILE = str(BACKEND_DIR / self.XINGTU_COOKIE_FILE)

        return self


settings = Settings()
