"""Environment-backed settings; secrets are never committed."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("SOURCEMAP_DATABASE_URL", "sqlite:///./sourcemap.db")
    github_client_id: str = os.getenv("GITHUB_CLIENT_ID", "")
    github_client_secret: str = os.getenv("GITHUB_CLIENT_SECRET", "")
    github_callback_url: str = os.getenv("GITHUB_CALLBACK_URL", "http://localhost:8000/auth/github/callback")
    jwt_secret: str = os.getenv("SOURCEMAP_JWT_SECRET", "")
    jwt_ttl_seconds: int = int(os.getenv("SOURCEMAP_JWT_TTL_SECONDS", "86400"))
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_embedding_model: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    openai_chat_model: str = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    pinecone_api_key: str = os.getenv("PINECONE_API_KEY", "")
    pinecone_index: str = os.getenv("PINECONE_INDEX", "sourcemap")
    redis_url: str = os.getenv("REDIS_URL", "")
    github_token: str = os.getenv("GITHUB_TOKEN", "")
    data_dir: str = os.getenv("SOURCEMAP_DATA_DIR", ".sourcemap")
    free_monthly_tokens: int = int(os.getenv("FREE_MONTHLY_TOKENS", "5000"))


settings = Settings()
