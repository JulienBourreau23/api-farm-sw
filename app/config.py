from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://sw_app:password@localhost:5432/farming-sw"
    API_SECRET: str = "change_me"  # Clé partagée avec Symfony pour sécuriser les appels inter-services

    class Config:
        env_file = ".env"

settings = Settings()
