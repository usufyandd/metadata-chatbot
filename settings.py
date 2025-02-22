from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    server_host: str
    server_port: int

    db_driver: str
    db_user: str
    db_password: str
    db_instance: str
    db_port: int
    db_database: str    

    secret_key: str
    access_token_expire_minutes: int

    elasticsearch_host: str
    elasticsearch_port: int
    elasticsearch_index: str

    openai_api_key: str
    openai_model: str
    GEMINI_API_KEY: str

    environment: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()