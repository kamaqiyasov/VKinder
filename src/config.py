from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    DB_HOST: Optional[str] = None
    DB_PORT: Optional[int] = None
    DB_USER: Optional[str] = None
    DB_PASS: Optional[str] = None
    DB_NAME: Optional[str] = None
    VK_GROUP_TOKEN: Optional[str] = None
    VK_GROUP_ID: Optional[int] = None
    VK_APP_ID: Optional[int] = None
    VK_CLIENT_SECRET: Optional[str] = None
    SERVER_URL: Optional[str] = None
    
    @property
    def DATABASE_URL_psycopg(self) -> str:
        return f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @field_validator(
        'DB_HOST', 'DB_PORT', 'DB_USER', 'DB_PASS', 'DB_NAME',
        'VK_GROUP_TOKEN', 'VK_GROUP_ID', 'VK_APP_ID', 'VK_CLIENT_SECRET', 'SERVER_URL'
    )
    @classmethod
    def validate_not_empty(cls, v, info) -> str:
        if v is None:
            field_name = info.field_name
            raise ValueError(f'Поле {field_name} не может быть пустым')
        return v
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()