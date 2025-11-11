from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    # Application
    app_name: str = "RAG Chatbot"
    debug: bool = False
    version: str = "1.0.0"

    # API
    api_v1_prefix: str = "/api/v1"

    # CORS
    cors_origins: List[str] = ["http://localhost:3000"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]

    # Database
    database_url: str = "postgresql://postgres:password@localhost:5432/ragchatbot"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # JWT Authentication
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    # OpenAI
    openai_api_key: str
    embedding_model: str = "text-embedding-3-small"
    llm_model: str = "gpt-4-turbo-preview"

    # Pinecone
    pinecone_api_key: str
    pinecone_environment: str
    pinecone_index_name: str = "rag-chatbot-index"
    pinecone_dimension: int = 1536

    # File Upload
    max_file_size: str = "50MB"
    upload_dir: str = "./uploads"

    # RAG Configuration
    default_chunk_size: int = 1000
    chunk_overlap: int = 200
    default_retrieval_k: int = 8
    rerank_enabled: bool = True
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    top_k_to_rerank: int = 20
    final_k_results: int = 5

    # Security
    rate_limit_per_minute: int = 100
    max_request_size: int = 10 * 1024 * 1024  # 10MB

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()