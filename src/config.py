
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASS: str = "password"
    DB_NAME: str = "vkinder"
    VK_GROUP_TOKEN: str = "your_group_token_here"  # Для работы бота
    VK_USER_TOKEN: str = "your_user_token_here"  # Для поиска пользователей
    DEBUG: bool = False

    @property
    def DATABASE_URL_psycopg(self) -> str:
        return f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "vkinder.log"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
