import asyncio
from typing import List, Dict, Any, Optional, Tuple
import structlog
import numpy as np

from app.config.settings import settings
from app.services.embeddings import EmbeddingService
from app.services.vectordb import VectorDBService
from app.services.reranker import RerankerService
from app.models.chat_schemas import RetrievalConfig, SourceCitation
from app.utils.exceptions import RetrievalError

logger = structlog.get_logger()


class RetrievalService:
    """Service for intelligent document retrieval with reranking"""

    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_db_service = VectorDBService()
        self.reranker_service = RerankerService()
        self.default_k = settings.default_retrieval_k
        self.min_relevance_threshold = 0.5

    async def retrieve_relevant_chunks(
        self,
        query: str,
        user_id: str,
        config: Optional[RetrievalConfig] = None
    ) -> List[SourceCitation]:
        """Retrieve relevant document chunks for a query"""
        try:
            # Use default config if none provided
            retrieval_config = config or RetrievalConfig()

            logger.info(
                "retrieval_started",
                query=query[:100] + "..." if len(query) > 100 else query,
                user_id=user_id,
                config=retrieval_config.dict()
            )

            # Step 1: Generate query embedding
            query_embedding = await self.embedding_service.generate_single_embedding(query)

            # Step 2: Initial vector search with more results than needed
            initial_k = max(retrieval_config.k, settings.top_k_to_rerank) if retrieval_config.rerank else retrieval_config.k
            search_results = await self._perform_vector_search(
                query_embedding,
                user_id,
                initial_k,
                retrieval_config.filters
            )

            if not search_results:
                logger.info("no_search_results_found", user_id=user_id, query=query[:50])
                return []

            # Step 3: Rerank results if enabled
            if retrieval_config.rerank and len(search_results) > retrieval_config.k:
                reranked_results = await self._rerank_results(
                    query,
                    search_results,
                    retrieval_config.k
                )
            else:
                # Use top-k results without reranking
                reranked_results = search_results[:retrieval_config.k]

            # Step 4: Filter by relevance threshold if provided
            if retrieval_config.threshold:
                filtered_results = [
                    result for result in reranked_results
                    if result.get("score", 0) >= retrieval_config.threshold
                ]
            else:
                filtered_results = reranked_results

            # Step 5: Convert to SourceCitation format
            source_citations = await self._convert_to_source_citations(
                filtered_results,
                query_embedding
            )

            logger.info(
                "retrieval_completed",
                user_id=user_id,
                initial_results=len(search_results),
                reranked_results=len(reranked_results),
                final_results=len(source_citations),
                reranking_enabled=retrieval_config.rerank
            )

            return source_citations

        except Exception as e:
            logger.error(
                "retrieval_failed",
                query=query[:100] if query else "",
                user_id=user_id,
                error=str(e)
            )
            raise RetrievalError(
                f"Failed to retrieve relevant chunks: {str(e)}",
                details={"query": query, "user_id": user_id}
            )

    async def _perform_vector_search(
        self,
        query_embedding: List[float],
        user_id: str,
        top_k: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Perform vector search in Pinecone"""
        try:
            # Create user-specific filter
            user_filter = {"user_id": user_id}

            # Combine with additional filters if provided
            if filters:
                user_filter.update(filters)

            # Search vectors
            search_results = await self.vector_db_service.search_vectors(
                query_vector=query_embedding,
                top_k=top_k,
                filter_dict=user_filter,
                include_metadata=True
            )

            return search_results

        except Exception as e:
            logger.error("vector_search_failed", user_id=user_id, error=str(e))
            raise RetrievalError(
                f"Vector search failed: {str(e)}",
                details={"user_id": user_id, "top_k": top_k}
            )

    async def _rerank_results(
        self,
        query: str,
        search_results: List[Dict[str, Any]],
        final_k: int
    ) -> List[Dict[str, Any]]:
        """Rerank search results using cross-encoder"""
        try:
            # Extract texts for reranking
            texts_to_rerank = []
            result_metadata = []

            for result in search_results:
                metadata = result.get("metadata", {})
                text = metadata.get("text", "")

                if text.strip():
                    texts_to_rererank.append(text.strip())
                    result_metadata.append({
                        "id": result.get("id"),
                        "original_score": result.get("score", 0),
                        "metadata": metadata
                    })

            if not texts_to_rerank:
                return []

            # Perform reranking
            reranked_scores = await self.reranker_service.rerank(
                query,
                texts_to_rerank
            )

            # Combine original results with reranked scores
            reranked_results = []
            for i, metadata in enumerate(result_metadata):
                if i < len(reranked_scores):
                    reranked_result = {
                        "id": metadata["id"],
                        "score": reranked_scores[i],
                        "original_score": metadata["original_score"],
                        "metadata": metadata["metadata"],
                        "rerank_improvement": reranked_scores[i] - metadata["original_score"]
                    }
                    reranked_results.append(reranked_result)

            # Sort by reranked score and take top_k
            reranked_results.sort(key=lambda x: x["score"], reverse=True)
            return reranked_results[:final_k]

        except Exception as e:
            logger.error("reranking_failed", error=str(e))
            # Fallback to original search results
            return search_results[:final_k]

    async def _convert_to_source_citations(
        self,
        results: List[Dict[str, Any]],
        query_embedding: List[float]
    ) -> List[SourceCitation]:
        """Convert search results to SourceCitation format"""
        source_citations = []

        for result in results:
            try:
                metadata = result.get("metadata", {})
                text = metadata.get("text", "")

                # Create citation
                citation = SourceCitation(
                    document_id=metadata.get("doc_id", ""),
                    filename=metadata.get("source_filename", ""),
                    page_number=metadata.get("page_number"),
                    chunk_index=metadata.get("chunk_index", 0),
                    chunk_text=text,
                    relevance_score=result.get("score", 0.0),
                    url=metadata.get("url"),
                    snippet=self._create_snippet(text, query_embedding)
                )

                source_citations.append(citation)

            except Exception as e:
                logger.warning(
                    "source_citation_conversion_failed",
                    result_id=result.get("id", "unknown"),
                    error=str(e)
                )
                continue

        return source_citations

    def _create_snippet(
        self,
        text: str,
        query_embedding: List[float],
        max_length: int = 200
    ) -> str:
        """Create a short snippet from the text"""
        try:
            if len(text) <= max_length:
                return text

            # Simple snippet creation - take first max_length characters
            # In a more sophisticated implementation, you might:
            # - Find most relevant sentences
            # - Use semantic similarity to find best passages
            # - Maintain context around key terms

            snippet = text[:max_length]
            if len(text) > max_length:
                snippet += "..."

            return snippet

        except Exception:
            # Fallback: return truncated text
            return text[:max_length] + ("..." if len(text) > max_length else "")

    async def hybrid_search(
        self,
        query: str,
        user_id: str,
        config: Optional[RetrievalConfig] = None
    ) -> List[SourceCitation]:
        """Perform hybrid search combining vector and keyword search"""
        try:
            retrieval_config = config or RetrievalConfig()

            # For now, implement vector search only
            # A full hybrid search would involve:
            # 1. Vector search (semantic)
            # 2. Keyword search (lexical)
            # 3. Score fusion (e.g., RRF - Reciprocal Rank Fusion)
            # 4. Deduplication and final ranking

            logger.info(
                "hybrid_search_performed",
                query=query[:50],
                user_id=user_id,
                note="Currently using vector search only"
            )

            return await self.retrieve_relevant_chunks(query, user_id, retrieval_config)

        except Exception as e:
            logger.error("hybrid_search_failed", error=str(e))
            raise

    async def search_by_document(
        self,
        document_ids: List[str],
        user_id: str,
        k: int = 10
    ) -> List[SourceCitation]:
        """Search within specific documents"""
        try:
            # Create filter for specific documents
            filter_dict = {
                "user_id": user_id,
                "doc_id": {"$in": document_ids}
            }

            # Perform search without query (returns all chunks from specified documents)
            search_results = await self.vector_db_service.search_vectors(
                # Use a dummy embedding for document-only search
                query_vector=[0.0] * settings.pinecone_dimension,
                top_k=k * 10,  # Get more results to account for filtering
                filter_dict=filter_dict,
                include_metadata=True
            )

            # Convert and return results
            source_citations = await self._convert_to_source_citations(
                search_results[:k],
                [0.0] * settings.pinecone_dimension
            )

            logger.info(
                "document_search_completed",
                user_id=user_id,
                document_count=len(document_ids),
                results_count=len(source_citations)
            )

            return source_citations

        except Exception as e:
            logger.error(
                "document_search_failed",
                user_id=user_id,
                document_ids=document_ids,
                error=str(e)
            )
            raise RetrievalError(
                f"Document search failed: {str(e)}",
                details={"document_ids": document_ids}
            )

    async def get_retrieval_stats(self, user_id: str) -> Dict[str, Any]:
        """Get retrieval statistics for a user"""
        try:
            # This would typically involve querying the database for retrieval metrics
            # For now, return placeholder data
            stats = {
                "user_id": user_id,
                "total_documents_indexed": 0,  # Would be fetched from database
                "total_chunks_indexed": 0,     # Would be fetched from database
                "average_retrieval_time": 0,   # Would be calculated from logs
                "total_queries_processed": 0,  # Would be fetched from analytics
                "average_relevance_score": 0   # Would be calculated from feedback
            }

            return stats

        except Exception as e:
            logger.error("retrieval_stats_failed", user_id=user_id, error=str(e))
            return {}

    async def validate_query(self, query: str) -> bool:
        """Validate and preprocess query"""
        try:
            if not query or not query.strip():
                return False

            # Check for malicious patterns or injection attempts
            suspicious_patterns = [
                " DROP ", " DELETE ", " UPDATE ", " INSERT ",
                "<script>", "</script>", "javascript:",
                "SELECT ", " FROM ", " WHERE "
            ]

            query_upper = query.upper()
            for pattern in suspicious_patterns:
                if pattern.upper() in query_upper:
                    logger.warning("suspicious_query_detected", query=query[:100])
                    return False

            return True

        except Exception as e:
            logger.error("query_validation_failed", error=str(e))
            return False

    async def get_context_for_query(
        self,
        query: str,
        user_id: str,
        config: Optional[RetrievalConfig] = None
    ) -> Dict[str, Any]:
        """Get comprehensive context for a query"""
        try:
            # Retrieve relevant chunks
            source_citations = await self.retrieve_relevant_chunks(
                query, user_id, config
            )

            # Combine chunks into context
            context_chunks = []
            for citation in source_citations:
                context_chunk = {
                    "text": citation.chunk_text,
                    "source": {
                        "document_id": str(citation.document_id),
                        "filename": citation.filename,
                        "page_number": citation.page_number,
                        "chunk_index": citation.chunk_index
                    },
                    "relevance_score": citation.relevance_score
                }
                context_chunks.append(context_chunk)

            # Create formatted context string
            formatted_context = self._format_context_for_llm(context_chunks)

            return {
                "query": query,
                "context_chunks": context_chunks,
                "formatted_context": formatted_context,
                "source_citations": source_citations,
                "total_chunks": len(context_chunks),
                "has_context": len(context_chunks) > 0
            }

        except Exception as e:
            logger.error("context_generation_failed", error=str(e))
            raise RetrievalError(f"Failed to generate context: {str(e)}")

    def _format_context_for_llm(
        self,
        context_chunks: List[Dict[str, Any]],
        max_context_length: int = 4000
    ) -> str:
        """Format context chunks for LLM prompt"""
        try:
            if not context_chunks:
                return "No relevant context found."

            formatted_parts = []
            current_length = 0

            for i, chunk in enumerate(context_chunks):
                source_info = (
                    f"[Source: {chunk['source']['filename']}"
                    f"{' - Page ' + str(chunk['source']['page_number']) if chunk['source']['page_number'] else ''}"
                    f"]"
                )

                chunk_text = f"{source_info}\n{chunk['text']}"

                # Check if adding this chunk would exceed the limit
                if current_length + len(chunk_text) > max_context_length:
                    break

                formatted_parts.append(chunk_text)
                current_length += len(chunk_text)

            return "\n\n".join(formatted_parts)

        except Exception as e:
            logger.error("context_formatting_failed", error=str(e))
            return "Context formatting failed."