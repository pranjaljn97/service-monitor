from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "SM_", "env_file": ".env"}

    openai_status_url: str = "https://status.openai.com/api/v2"
    openai_poll_interval: int = 60

    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
