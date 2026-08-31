from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT / ".env"), extra="ignore")

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str | None = None

    data_dir: Path = ROOT / "data"
    knowledge_dir: Path = ROOT / "knowledge"
    chroma_dir: Path = ROOT / "data" / "chroma"
    sqlite_path: Path = ROOT / "data" / "aftermath.db"
    checkpoints_path: Path = ROOT / "data" / "checkpoints.db"

    chunk_size: int = 800
    chunk_overlap: int = 120
    retrieve_k: int = 4
    similarity_threshold: float = 0.35


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.chroma_dir.mkdir(parents=True, exist_ok=True)
