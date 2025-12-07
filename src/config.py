from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASS: str = "password"
    DB_NAME: str = "myapp"
    VK_GROUP_TOKEN: str = "your_vk_token_here"
    VK_USER_TOKEN: str = "your_vk_token_here"
    VK_GROUP_ID: int = 111111
    VK_APP_ID: int = 1111
    VK_CLIENT_SECRET: str = 'client_secret'
    VK_REDIRECT_URI: str = 'redirect_uri'
    
    @property
    def DATABASE_URL_psycopg(self) -> str:
        return f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()