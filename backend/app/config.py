import os
import logging


def _asbool(val: str | None, default: bool = False) -> bool:
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")

    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_JSON: bool = _asbool(os.getenv("LOG_JSON"), False)
    SESSION_TTL: int = int(os.getenv("SESSION_TTL", "86400"))
    MAX_CONVERSATION_HISTORY: int = int(os.getenv("MAX_CONVERSATION_HISTORY", "20"))
    RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "3"))
    TRACE_TOOLS: bool = _asbool(os.getenv("TRACE_TOOLS"), False)

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/horticulture"
    )
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    CHROMA_HOST: str = os.getenv("CHROMA_HOST", "chroma")
    CHROMA_PORT: int = int(os.getenv("CHROMA_PORT", "8000"))
    DB_ECHO: bool = _asbool(os.getenv("DB_ECHO"), False)


settings = Settings()


def mask(value: str | None) -> str:
    if not value:
        return "<unset>"
    if len(value) <= 6:
        return "***"
    return value[:3] + "***" + value[-2:]


def validate_settings(fail_on_missing_llm_key: bool = True) -> None:
    """
    Validate critical configuration and log non-sensitive values.

    By default, we fail fast when `GEMINI_API_KEY` is missing, as LLM and
    image services require it for Milestone 3. RAG can degrade gracefully
    but is expected to run with embeddings for best results.
    """
    logging.getLogger(__name__).info(
        "Config: ENV=%s, DB=%s, REDIS=%s, CHROMA=%s:%s, GEMINI_API_KEY=%s",
        settings.ENVIRONMENT,
        settings.DATABASE_URL,
        settings.REDIS_URL,
        settings.CHROMA_HOST,
        settings.CHROMA_PORT,
        mask(settings.GEMINI_API_KEY),
    )

    if fail_on_missing_llm_key and not settings.GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is required for LLM and image services. Set it in the environment/.env."
        )


def setup_logging() -> None:
    """Configure root logging based on LOG_LEVEL and output to stdout.

    Safe to call multiple times; subsequent calls are ignored if handlers exist.
    """
    if logging.getLogger().handlers:
        return
    level = getattr(logging, (settings.LOG_LEVEL or "INFO").upper(), logging.INFO)

    if settings.LOG_JSON:
        class JsonFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
                import json, time
                payload = {
                    "ts": getattr(record, "created", time.time()),
                    "level": record.levelname,
                    "logger": record.name,
                    "msg": record.getMessage(),
                }
                # Common extras if present
                for k in ("session_id", "intent", "tool", "path", "method"):
                    if hasattr(record, k):
                        payload[k] = getattr(record, k)
                return json.dumps(payload, ensure_ascii=False)

        handler = logging.StreamHandler()
        handler.setLevel(level)
        handler.setFormatter(JsonFormatter())
        root = logging.getLogger()
        root.setLevel(level)
        root.addHandler(handler)
    else:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        )
