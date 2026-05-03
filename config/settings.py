from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="WORLDAI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Infrastructure ──────────────────────────────────────────────
    domain: str = "localhost"
    acme_email: str = ""
    env: str = "development"

    # ── API Keys ────────────────────────────────────────────────────
    openrouter_api_key: str = ""
    anthropic_api_key: str = ""
    telegram_bot_token: str = ""

    # ── PostgreSQL ──────────────────────────────────────────────────
    postgres_user: str = "worldai"
    postgres_password: str = ""
    postgres_db: str = "worldai"

    # ── Redis ───────────────────────────────────────────────────────
    redis_password: str = ""
    redis_url: str = "redis://redis:6379"

    # ── Memgraph ────────────────────────────────────────────────────
    memgraph_user: str = "memgraph"
    memgraph_password: str = ""
    memgraph_uri: str = "bolt://memgraph:7687"

    # ── Qdrant ──────────────────────────────────────────────────────
    qdrant_api_key: str = ""
    qdrant_url: str = "http://qdrant:6333"

    # ── LLM Routing ─────────────────────────────────────────────────
    llm_budget_model: str = "deepseek/deepseek-chat"
    llm_mid_model: str = "meta-llama/llama-4-scout"
    llm_frontier_model: str = "anthropic/claude-opus-4-6"
    confidence_threshold: float = 0.75
    simulation_threshold: float = 0.40

    # ── Local inference (xLAM-2 via llama.cpp) ─────────────────────
    xlam_local_url: str = ""   # e.g. http://localhost:8080/v1 — empty = disabled

    # ── n8n ─────────────────────────────────────────────────────────
    n8n_encryption_key: str = ""

    # ── Langfuse ────────────────────────────────────────────────────
    langfuse_secret_key: str = ""
    langfuse_public_key: str = ""
    langfuse_nextauth_secret: str = ""
    langfuse_salt: str = ""

    # ── Dify ────────────────────────────────────────────────────────
    dify_secret_key: str = ""
    dify_version: str = "0.6.14"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
