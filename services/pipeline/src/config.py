from pathlib import Path

from pydantic_settings import BaseSettings

# Resolve project root (.env location) relative to this file
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    # LLM provider: "groq", "google", "openrouter", "anthropic", or "bedrock"
    llm_provider: str = "groq"

    # Groq (recommended — free, fast, reliable)
    groq_api_key: str = ""

    # Google AI Studio (Gemini — free 15 RPM)
    google_api_key: str = ""

    # OpenRouter (multiple models, free tier unreliable)
    openrouter_api_key: str = ""

    # Direct Anthropic API
    anthropic_api_key: str = ""

    # AWS Bedrock
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    # Leave blank to use default AWS credential chain (recommended)

    voyage_api_key: str = ""

    cors_origins: str = "http://localhost:3000"

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""

    data_dir: str = str(_PROJECT_ROOT / "data")
    chroma_persist_dir: str = str(_PROJECT_ROOT / "data" / "chroma")

    # Model name (format depends on provider)
    # Groq: "llama-3.3-70b-versatile"
    # Google: "gemini-2.0-flash"
    # OpenRouter: "google/gemini-2.0-flash-exp:free"
    # Bedrock: "us.anthropic.claude-sonnet-4-20250514-v1:0"
    # Anthropic: "claude-sonnet-4-20250514"
    model_name: str = "llama-3.3-70b-versatile"
    embedding_model: str = "voyage-3"
    temperature: float = 0.2
    max_tokens: int = 2048

    model_config = {"env_file": str(_ENV_FILE), "extra": "ignore"}


settings = Settings()
