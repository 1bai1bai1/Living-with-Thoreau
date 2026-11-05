from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # The .env can live at the project root or in backend/.
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    # Gemini on Vertex AI, signed in with `gcloud auth application-default login`
    # (no API key). Same setup as the CS639 reference project.
    GOOGLE_CLOUD_PROJECT: str = ""
    GOOGLE_CLOUD_LOCATION: str = "global"
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    # If set, all Gemini traffic goes here instead (a local stand-in).
    LLM_BASE_URL: str = ""

    # "auto": Gemini when a project is configured, otherwise the offline mock.
    # "mock": always the mock (authored fallback text, no network).
    # "gemini": always Gemini.
    LLM_MODE: str = "auto"
    # Seconds between words when the mock "streams", so the UI feels alive.
    MOCK_STREAM_DELAY: float = 0.02

    CORS_ORIGINS: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def use_gemini(self) -> bool:
        if self.LLM_MODE == "mock":
            return False
        if self.LLM_MODE == "gemini":
            return True
        return bool(self.GOOGLE_CLOUD_PROJECT or self.LLM_BASE_URL)


def get_settings() -> Settings:
    return Settings()
