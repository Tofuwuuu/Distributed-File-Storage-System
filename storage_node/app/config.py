from pathlib import Path
from pydantic import BaseSettings


class Settings(BaseSettings):
    node_id: str = "storage-node"
    data_dir: Path = Path("/data")
    coordinator_url: str | None = None

    class Config:
        env_prefix = ""
        env_file = None


settings = Settings()

# Ensure data directory exists early
settings.data_dir.mkdir(parents=True, exist_ok=True)

