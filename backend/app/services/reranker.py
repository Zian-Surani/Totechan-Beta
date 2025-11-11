import asyncio
from typing import List, Dict, Any, Optional, Tuple
import structlog
import numpy as np
from sentence_transformers import CrossEncoder
import torch

from app.config.settings import settings
from app.utils.exceptions import ExternalServiceError

logger = structlog.get_logger()


class RerankerService:
    """Service for reranking search results using cross-encoder models"""

    def __init__(self):
        self.model_name = settings.rerank_model
        self.top_k_to_rerank = settings.top_k_to_rerank
        self.final_k_results = settings.final_k_results
        self.batch_size = 16
        self.max_length = 512  # Maximum sequence length for cross-encoder

        # Initialize model
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._load_model()

    def _load_model(self):
        """Load the cross-encoder model"""
        try:
            logger.info(
                "loading_reranker_model",
                model_name=self.model_name,
                device=self.device
            )

            self.model = CrossEncoder(
                self.model_name,
                device=self.device,
                max_length=self.max_length
            )

            logger.info(
                "reranker_model_loaded_successfully",
                model_name=self.model_name,
                device=self.device
            )

        except Exception as e:
            logger.error(
                "reranker_model_loading_failed",
                model_name=self.model_name,
                error=str(e)
            )
            # Continue without reranking - will use original scores
            self.model = None

    async def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: Optional[int] = None
    ) -> List[float]:
        """Rerank documents based on query relevance"""
        try:
            if not self.model:
                logger.warning("reranker_model_not_available, returning_original_scores")
                return [0.5] * len(documents)  # Return neutral scores

            if not documents:
                return []

            target_k = top_k or self.final_k_results

            logger.info(
                "reranking_started",
                query_length=len(query),
                document_count=len(documents),
                target_k=target_k
            )

            # Prepare query-document pairs
            query_doc_pairs = [[query, doc] for doc in documents]

            # Predict relevance scores in batches
            scores = await self._predict_scores(query_doc_pairs)

            logger.info(
                "reranking_completed",
                document_count=len(documents),
                scores_generated=len(scores)
            )

            return scores

        except Exception as e:
            logger.error("reranking_failed", error=str(e))
            # Return neutral scores as fallback
            return [0.5] * len(documents)

    async def _predict_scores(self, query_doc_pairs: List[List[str]]) -> List[float]:
        """Predict relevance scores for query-document pairs"""
        try:
            all_scores = []

            # Process in batches to avoid memory issues
            for i in range(0, len(query_doc_pairs), self.batch_size):
                batch = query_doc_pairs[i:i + self.batch_size]

                # Predict scores for this batch
                batch_scores = self.model.predict(batch)
                all_scores.extend(batch_scores.tolist())

                # Small delay to prevent overwhelming the model
                await asyncio.sleep(0.01)

            return all_scores

        except Exception as e:
            logger.error("score_prediction_failed", error=str(e))
            raise ExternalServiceError(
                f"Failed to predict reranking scores: {str(e)}",
                service="reranker"
            )

    async def rerank_with_metadata(
        self,
        query: str,
        search_results: List[Dict[str, Any]],
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Rerank search results with their metadata"""
        try:
            if not self.model or not search_results:
                return search_results

            # Extract document texts
            documents = []
            for result in search_results:
                metadata = result.get("metadata", {})
                text = metadata.get("text", "")
                documents.append(text)

            # Get reranking scores
            scores = await self.rerank(query, documents, top_k)

            # Combine original results with new scores
            reranked_results = []
            for i, result in enumerate(search_results):
                if i < len(scores):
                    reranked_result = result.copy()
                    reranked_result.update({
                        "rerank_score": scores[i],
                        "original_score": result.get("score", 0),
                        "score_improvement": scores[i] - result.get("score", 0),
                        "reranked": True
                    })
                    reranked_results.append(reranked_result)

            # Sort by reranked scores
            target_k = top_k or len(reranked_results)
            reranked_results.sort(key=lambda x: x["rerank_score"], reverse=True)

            return reranked_results[:target_k]

        except Exception as e:
            logger.error("reranking_with_metadata_failed", error=str(e))
            return search_results

    async def calculate_reranking_improvement(
        self,
        original_scores: List[float],
        reranked_scores: List[float]
    ) -> Dict[str, Any]:
        """Calculate improvement metrics for reranking"""
        try:
            if len(original_scores) != len(reranked_scores):
                raise ValueError("Score lists must have the same length")

            # Calculate average scores
            avg_original = np.mean(original_scores)
            avg_reranked = np.mean(reranked_scores)

            # Calculate score improvements
            improvements = [reranked - original for original, reranked in zip(original_scores, reranked_scores)]
            avg_improvement = np.mean(improvements)

            # Calculate correlation
            correlation = np.corrcoef(original_scores, reranked_scores)[0, 1]

            # Calculate top-k precision improvement
            top_k = min(5, len(original_scores))
            original_top_k_indices = np.argsort(original_scores)[-top_k:]
            reranked_top_k_indices = np.argsort(reranked_scores)[-top_k:]

            overlap = len(set(original_top_k_indices) & set(reranked_top_k_indices))
            top_k_overlap_ratio = overlap / top_k

            return {
                "avg_original_score": float(avg_original),
                "avg_reranked_score": float(avg_reranked),
                "avg_improvement": float(avg_improvement),
                "correlation": float(correlation) if not np.isnan(correlation) else 0.0,
                "top_k_overlap_ratio": float(top_k_overlap_ratio),
                "total_items": len(original_scores)
            }

        except Exception as e:
            logger.error("reranking_improvement_calculation_failed", error=str(e))
            return {}

    async def get_reranker_info(self) -> Dict[str, Any]:
        """Get information about the reranker service"""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "top_k_to_rerank": self.top_k_to_rerank,
            "final_k_results": self.final_k_results,
            "batch_size": self.batch_size,
            "max_length": self.max_length,
            "is_available": self.model is not None
        }

    async def test_reranker(self, test_query: str, test_documents: List[str]) -> Dict[str, Any]:
        """Test the reranker with sample data"""
        try:
            if not self.model:
                return {
                    "status": "error",
                    "message": "Reranker model not available"
                }

            if not test_documents:
                return {
                    "status": "error",
                    "message": "No test documents provided"
                }

            logger.info(
                "testing_reranker",
                query_length=len(test_query),
                document_count=len(test_documents)
            )

            # Perform reranking
            scores = await self.rerank(test_query, test_documents)

            # Sort documents by score
            scored_documents = list(zip(test_documents, scores))
            scored_documents.sort(key=lambda x: x[1], reverse=True)

            return {
                "status": "success",
                "query": test_query,
                "results": [
                    {
                        "document": doc[:100] + "..." if len(doc) > 100 else doc,
                        "score": float(score)
                    }
                    for doc, score in scored_documents
                ],
                "total_documents": len(test_documents),
                "model_info": await self.get_reranker_info()
            }

        except Exception as e:
            logger.error("reranker_test_failed", error=str(e))
            return {
                "status": "error",
                "message": str(e)
            }

    def _truncate_text(self, text: str, max_length: int = 400) -> str:
        """Truncate text to maximum length for cross-encoder"""
        if len(text) <= max_length:
            return text

        # Try to truncate at word boundary
        truncated = text[:max_length]
        last_space = truncated.rfind(' ')

        if last_space > max_length * 0.8:  # Only use word boundary if it's not too far back
            return truncated[:last_space] + "..."
        else:
            return truncated + "..."

    async def prepare_documents_for_reranking(
        self,
        search_results: List[Dict[str, Any]]
    ) -> List[str]:
        """Prepare and clean documents for reranking"""
        prepared_docs = []

        for result in search_results:
            metadata = result.get("metadata", {})
            text = metadata.get("text", "")

            if not text.strip():
                continue

            # Clean and truncate text
            cleaned_text = text.strip()
            cleaned_text = self._truncate_text(cleaned_text, self.max_length - 100)  # Leave room for query

            if cleaned_text:
                prepared_docs.append(cleaned_text)

        return prepared_docs

    async def batch_rerank(
        self,
        queries: List[str],
        document_lists: List[List[str]],
        top_k: Optional[int] = None
    ) -> List[List[float]]:
        """Rerank multiple queries with their document lists"""
        try:
            if not self.model:
                return [[0.5] * len(docs) for docs in document_lists]

            if len(queries) != len(document_lists):
                raise ValueError("Number of queries must match number of document lists")

            logger.info(
                "batch_reranking_started",
                query_count=len(queries),
                total_documents=sum(len(docs) for docs in document_lists)
            )

            all_scores = []

            for query, documents in zip(queries, document_lists):
                scores = await self.rerank(query, documents, top_k)
                all_scores.append(scores)

            logger.info("batch_reranking_completed")

            return all_scores

        except Exception as e:
            logger.error("batch_reranking_failed", error=str(e))
            # Return neutral scores as fallback
            return [[0.5] * len(docs) for docs in document_lists]

    async def update_model(self, new_model_name: str) -> bool:
        """Update to a new reranker model"""
        try:
            logger.info(
                "updating_reranker_model",
                old_model=self.model_name,
                new_model=new_model_name
            )

            # Load new model
            old_model = self.model
            self.model_name = new_model_name

            try:
                self._load_model()

                # Test the new model
                test_result = await self.test_reranker("test query", ["test document"])
                if test_result.get("status") == "success":
                    logger.info("reranker_model_updated_successfully", new_model=new_model_name)
                    return True
                else:
                    # Revert to old model
                    self.model = old_model
                    self.model_name = settings.rerank_model
                    logger.warning("new_model_test_failed, reverting_to_old_model")
                    return False

            except Exception as e:
                # Revert to old model
                self.model = old_model
                self.model_name = settings.rerank_model
                logger.error("model_update_failed, reverting_to_old_model", error=str(e))
                return False

        except Exception as e:
            logger.error("reranker_model_update_failed", error=str(e))
            return False