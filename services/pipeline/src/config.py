from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    voyage_api_key: str = ""

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""

    chroma_persist_dir: str = "./data/chroma"

    model_name: str = "claude-sonnet-4-20250514"
    embedding_model: str = "voyage-3"
    temperature: float = 0.2
    max_tokens: int = 2048

    model_config = {"env_file": "../../.env", "extra": "ignore"}


settings = Settings()
