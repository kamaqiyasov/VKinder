
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASS: str = "password"
    DB_NAME: str = "vkinder"
    VK_GROUP_TOKEN: str = "your_group_token_here"  # Для работы бота
    VK_USER_TOKEN: str = "your_user_token_here"    # Для поиска пользователей

    @property
    def VK_TOKEN(self) -> str:
        return self.VK_GROUP_TOKEN if self.VK_GROUP_TOKEN else self.VK_USER_TOKEN

    @property
    def DATABASE_URL_psycopg(self) -> str:
        return f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()