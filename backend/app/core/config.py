from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=('.env', 'backend/.env'),
        env_file_encoding='utf-8',
        extra='ignore'
    )

    app_name: str = 'Transfreezer Insight Suite'
    cors_origins: list[str] = ['http://localhost:3000']
    model_file: str = 'app/modules/forecast_operativo/artifacts/models/transfreezer_modelo_ts.pkl'
    model_dir: str = 'app/modules/forecast_operativo/artifacts/models'
    econometria_model_file: str = 'app/modules/econometria/artifacts/models/transfreezer_modelo_econometrico_v1.pkl'
    econometria_model_dir: str = 'app/modules/econometria/artifacts/models'
    mineria_model_file: str = 'app/modules/mineria/artifacts/models/best_model.pkl'
    mineria_model_dir: str = 'app/modules/mineria/artifacts/models'
    asistente_db_file: str = 'app/modules/asistente_inteligente/artifacts/alertas_viales.db'
    asistente_zero_shot_model: str = 'joeddav/xlm-roberta-large-xnli'
    asistente_gemini_models: list[str] = [
        'models/gemini-2.5-flash',
        'gemini-2.0-flash',
    ]
    asistente_gemini_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices('ASISTENTE_GEMINI_API_KEY', 'GEMINI_API_KEY', 'GOOGLE_API_KEY'),
    )
    openrouter_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices('OPENROUTER_API_KEY'),
    )
    openrouter_model: str = 'google/gemma-4-31b-it:free'
    openrouter_model_fallbacks: list[str] = [
        'google/gemma-4-31b-it:free',
        'meta-llama/llama-3.3-70b-instruct:free',
        'openai/gpt-oss-20b:free',
        'nvidia/nemotron-nano-9b-v2:free',
    ]
    asistente_scrape_timeout_seconds: int = 12
    default_forecast_horizon: int = 6
    snowflake_account: str | None = None
    snowflake_user: str | None = None
    snowflake_password: str | None = None
    snowflake_warehouse: str | None = None
    snowflake_database: str | None = None
    snowflake_schema: str | None = None
    snowflake_role: str | None = None
    snowflake_query_timeout_seconds: int = 60

    @property
    def resolved_model_path(self) -> Path:
        return Path(self.model_file)

    def has_snowflake_credentials(self) -> bool:
        required_values = [
            self.snowflake_account,
            self.snowflake_user,
            self.snowflake_password,
            self.snowflake_warehouse,
            self.snowflake_database,
            self.snowflake_schema,
            self.snowflake_role
        ]
        return all(required_values)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
