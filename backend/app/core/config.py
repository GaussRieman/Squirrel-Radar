from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./macro_cycle_radar.db"
    cors_origins: str = "http://127.0.0.1:3000"
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    agent_model: str = "openai:gpt-5.4"
    enable_model_calls: bool = True


settings = Settings()
