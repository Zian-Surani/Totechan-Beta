import asyncio
import time
from typing import List, Dict, Any, Optional
import structlog
from openai import AsyncOpenAI
import tiktoken

from app.config.settings import settings
from app.utils.exceptions import EmbeddingError, ExternalServiceError

logger = structlog.get_logger()


class EmbeddingService:
    """Service for generating text embeddings using OpenAI"""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.embedding_model
        self.dimension = settings.pinecone_dimension
        self.batch_size = 100  # Process in batches of 100
        self.max_retries = 3
        self.retry_delay = 1.0

        # Initialize tokenizer for token counting
        try:
            self.tokenizer = tiktoken.encoding_for_model(self.model)
        except KeyError:
            # Fallback to a common tokenizer if model not found
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

    async def generate_embeddings(
        self,
        texts: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        try:
            if not texts:
                return []

            # Log the request
            total_tokens = sum(self._count_tokens(text) for text in texts)
            logger.info(
                "generating_embeddings",
                text_count=len(texts),
                total_tokens=total_tokens,
                model=self.model
            )

            # Process in batches to avoid rate limits
            all_embeddings = []
            for i in range(0, len(texts), self.batch_size):
                batch = texts[i:i + self.batch_size]
                batch_embeddings = await self._generate_batch_embeddings(
                    batch,
                    batch_index=i // self.batch_size,
                    metadata=metadata
                )
                all_embeddings.extend(batch_embeddings)

                # Small delay between batches to avoid rate limits
                if i + self.batch_size < len(texts):
                    await asyncio.sleep(0.1)

            logger.info(
                "embeddings_generated_successfully",
                total_embeddings=len(all_embeddings),
                dimension=len(all_embeddings[0]) if all_embeddings else 0
            )

            return all_embeddings

        except Exception as e:
            logger.error(
                "embedding_generation_failed",
                error=str(e),
                text_count=len(texts)
            )
            raise EmbeddingError(
                f"Failed to generate embeddings: {str(e)}",
                details={"text_count": len(texts), "model": self.model}
            )

    async def generate_single_embedding(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[float]:
        """Generate embedding for a single text"""
        embeddings = await self.generate_embeddings([text], metadata)
        return embeddings[0] if embeddings else []

    async def _generate_batch_embeddings(
        self,
        texts: List[str],
        batch_index: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[List[float]]:
        """Generate embeddings for a batch of texts with retries"""
        last_error = None

        for attempt in range(self.max_retries):
            try:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=texts,
                    encoding_format="float"
                )

                # Extract embeddings
                embeddings = [data.embedding for data in response.data]

                # Validate dimensions
                if embeddings and len(embeddings[0]) != self.dimension:
                    raise EmbeddingError(
                        f"Embedding dimension mismatch: expected {self.dimension}, got {len(embeddings[0])}"
                    )

                logger.debug(
                    "batch_embedding_success",
                    batch_index=batch_index,
                    text_count=len(texts),
                    attempt=attempt + 1
                )

                return embeddings

            except Exception as e:
                last_error = e
                logger.warning(
                    "batch_embedding_attempt_failed",
                    batch_index=batch_index,
                    attempt=attempt + 1,
                    error=str(e)
                )

                # If not the last attempt, wait before retrying
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff

        # All attempts failed
        raise ExternalServiceError(
            f"Failed to generate embeddings after {self.max_retries} attempts: {str(last_error)}",
            service="openai"
        )

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text using the appropriate tokenizer"""
        try:
            return len(self.tokenizer.encode(text))
        except Exception:
            # Fallback: rough estimation (1 token ≈ 4 characters for English)
            return len(text) // 4

    async def estimate_embedding_cost(
        self,
        texts: List[str]
    ) -> Dict[str, Any]:
        """Estimate cost for embedding generation"""
        try:
            # OpenAI pricing (as of 2024)
            # text-embedding-3-small: $0.02 per 1M tokens
            # text-embedding-ada-002: $0.10 per 1M tokens
            pricing = {
                "text-embedding-3-small": 0.02,
                "text-embedding-ada-002": 0.10
            }

            price_per_million_tokens = pricing.get(self.model, pricing["text-embedding-3-small"])

            total_tokens = sum(self._count_tokens(text) for text in texts)
            estimated_cost = (total_tokens / 1_000_000) * price_per_million_tokens

            return {
                "model": self.model,
                "total_tokens": total_tokens,
                "price_per_million_tokens": price_per_million_tokens,
                "estimated_cost_usd": round(estimated_cost, 6),
                "text_count": len(texts)
            }

        except Exception as e:
            logger.error("cost_estimation_error", error=str(e))
            return {
                "model": self.model,
                "total_tokens": 0,
                "price_per_million_tokens": 0,
                "estimated_cost_usd": 0,
                "text_count": len(texts),
                "error": str(e)
            }

    async def validate_model_access(self) -> bool:
        """Validate that we can access the embedding model"""
        try:
            test_text = "This is a test text for embedding validation."
            await self.generate_single_embedding(test_text)
            logger.info("embedding_model_access_validated", model=self.model)
            return True

        except Exception as e:
            logger.error(
                "embedding_model_access_failed",
                model=self.model,
                error=str(e)
            )
            return False

    async def get_embedding_info(self) -> Dict[str, Any]:
        """Get information about the embedding service"""
        return {
            "model": self.model,
            "dimension": self.dimension,
            "batch_size": self.batch_size,
            "max_retries": self.max_retries,
            "tokenizer": str(type(self.tokenizer).__name__),
            "is_accessible": await self.validate_model_access()
        }

    def prepare_texts_for_embedding(
        self,
        chunks: List[Dict[str, Any]]
    ) -> List[str]:
        """Prepare and clean text chunks for embedding"""
        prepared_texts = []

        for chunk in chunks:
            text = chunk.get("text", "").strip()

            # Skip empty or very short texts
            if len(text) < 10:  # Minimum 10 characters
                continue

            # Clean text (basic cleaning)
            # Remove excessive whitespace
            text = ' '.join(text.split())

            # Ensure we don't exceed token limits
            # For text-embedding-3-small, max is 8191 tokens
            max_tokens = 8000  # Leave some buffer
            current_tokens = self._count_tokens(text)

            if current_tokens > max_tokens:
                # Truncate text (this is a simple approach)
                # A more sophisticated approach would preserve sentence boundaries
                words = text.split()
                truncated_text = ""
                token_count = 0

                for word in words:
                    test_text = truncated_text + " " + word if truncated_text else word
                    if self._count_tokens(test_text) <= max_tokens:
                        truncated_text = test_text
                    else:
                        break

                text = truncated_text.strip()

            prepared_texts.append(text)

        return prepared_texts

    async def create_embeddings_with_metadata(
        self,
        chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Create embeddings and attach them to chunk metadata"""
        try:
            # Prepare texts
            texts = self.prepare_texts_for_embedding(chunks)

            if not texts:
                logger.warning("no_valid_texts_for_embedding")
                return []

            # Generate embeddings
            embeddings = await self.generate_embeddings(texts)

            # Attach embeddings to chunks
            chunks_with_embeddings = []
            embedding_index = 0

            for chunk in chunks:
                text = chunk.get("text", "").strip()

                # Skip chunks that were too short or empty
                if len(text) < 10:
                    continue

                if embedding_index < len(embeddings):
                    chunk_with_embedding = chunk.copy()
                    chunk_with_embedding["embedding"] = embeddings[embedding_index]
                    chunk_with_embedding["embedding_model"] = self.model
                    chunk_with_embedding["embedding_dimension"] = self.dimension
                    chunk_with_embedding["token_count"] = self._count_tokens(text)

                    chunks_with_embeddings.append(chunk_with_embedding)
                    embedding_index += 1

            logger.info(
                "embeddings_created_with_metadata",
                total_chunks=len(chunks),
                valid_chunks=len(chunks_with_embeddings),
                model=self.model
            )

            return chunks_with_embeddings

        except Exception as e:
            logger.error("embedding_creation_with_metadata_failed", error=str(e))
            raise