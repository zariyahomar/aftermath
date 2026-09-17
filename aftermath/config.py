from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        extra="ignore",
    )

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"

    # App storage
    data_dir: Path = ROOT / "data"
    knowledge_dir: Path = ROOT / "knowledge"
    chroma_dir: Path = ROOT / "data" / "chroma"
    sqlite_path: Path = ROOT / "data" / "aftermath.db"
    checkpoints_path: Path = ROOT / "data" / "checkpoints.db"

    # RAG
    chunk_size: int = 800
    chunk_overlap: int = 120
    retrieve_k: int = 4
    similarity_threshold: float = 0.35


settings = Settings()

settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.chroma_dir.mkdir(parents=True, exist_ok=True)