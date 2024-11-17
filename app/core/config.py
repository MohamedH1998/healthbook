from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    WHATSAPP_TOKEN: str
    PHONE_NUMBER_ID: str
    GROQ_API_KEY: str
    AWS_ACCESS_KEY: str
    AWS_SECRET_KEY: str
    S3_BUCKET: str
    VERIFY_TOKEN: str
    AWS_REGION: str = "eu-north-1"
    PINECONE_API_KEY: str
    AI_API_KEY: str
    REDIS_URL: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
