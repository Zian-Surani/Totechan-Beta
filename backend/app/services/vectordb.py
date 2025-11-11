import asyncio
import time
from typing import List, Dict, Any, Optional, Tuple
import structlog
from pinecone import Pinecone, ServerlessSpec, PodSpec
from pinecone.exceptions import PineconeException

from app.config.settings import settings
from app.utils.exceptions import ExternalServiceError, RetrievalError

logger = structlog.get_logger()


class VectorDBService:
    """Service for managing vector database operations with Pinecone"""

    def __init__(self):
        self.api_key = settings.pinecone_api_key
        self.environment = settings.pinecone_environment
        self.index_name = settings.pinecone_index_name
        self.dimension = settings.pinecone_dimension

        # Initialize Pinecone client
        try:
            self.pc = Pinecone(api_key=self.api_key)
            self.index = self.pc.Index(self.index_name)
            logger.info(
                "pinecone_initialized",
                index_name=self.index_name,
                dimension=self.dimension
            )
        except Exception as e:
            logger.error("pinecone_initialization_failed", error=str(e))
            raise ExternalServiceError(
                f"Failed to initialize Pinecone: {str(e)}",
                service="pinecone"
            )

    async def create_index(
        self,
        index_name: Optional[str] = None,
        dimension: Optional[int] = None,
        metric: str = "cosine"
    ) -> bool:
        """Create a new Pinecone index"""
        try:
            target_index_name = index_name or self.index_name
            target_dimension = dimension or self.dimension

            # Check if index already exists
            if target_index_name in self.pc.list_indexes().names():
                logger.info("index_already_exists", index_name=target_index_name)
                return True

            # Create index with serverless spec (recommended)
            self.pc.create_index(
                name=target_index_name,
                dimension=target_dimension,
                metric=metric,
                spec=ServerlessSpec(
                    cloud="aws",
                    region=self.environment
                )
            )

            # Wait for index to be ready
            await self._wait_for_index_ready(target_index_name)

            logger.info(
                "index_created_successfully",
                index_name=target_index_name,
                dimension=target_dimension,
                metric=metric
            )

            return True

        except PineconeException as e:
            logger.error("pinecone_index_creation_failed", error=str(e))
            raise ExternalServiceError(
                f"Failed to create Pinecone index: {str(e)}",
                service="pinecone"
            )
        except Exception as e:
            logger.error("index_creation_failed", error=str(e))
            raise

    async def _wait_for_index_ready(self, index_name: str, timeout: int = 300) -> bool:
        """Wait for index to be ready"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                index_status = self.pc.describe_index(index_name)
                if index_status.status.ready:
                    return True
                await asyncio.sleep(5)
            except Exception as e:
                logger.warning("index_status_check_failed", error=str(e))
                await asyncio.sleep(5)

        raise ExternalServiceError(
            f"Index {index_name} not ready after {timeout} seconds",
            service="pinecone"
        )

    async def upsert_vectors(
        self,
        vectors: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """Upsert vectors into the database"""
        try:
            if not vectors:
                return {"upserted_count": 0, "errors": []}

            total_upserted = 0
            errors = []

            # Process in batches
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]

                try:
                    # Prepare vectors for Pinecone
                    pinecone_vectors = []
                    for vector_data in batch:
                        pinecone_vector = {
                            "id": vector_data["id"],
                            "values": vector_data["embedding"],
                            "metadata": vector_data.get("metadata", {})
                        }
                        pinecone_vectors.append(pinecone_vector)

                    # Upsert batch
                    response = self.index.upsert(vectors=pinecone_vectors)
                    batch_upserted = response.get("upserted_count", 0)
                    total_upserted += batch_upserted

                    logger.debug(
                        "batch_upsert_completed",
                        batch_index=i // batch_size,
                        upserted_count=batch_upserted,
                        batch_size=len(batch)
                    )

                    # Small delay to avoid rate limits
                    await asyncio.sleep(0.1)

                except Exception as e:
                    error_msg = f"Batch {i // batch_size} failed: {str(e)}"
                    errors.append(error_msg)
                    logger.error("batch_upsert_failed", batch_index=i // batch_size, error=str(e))

            logger.info(
                "vectors_upserted_completed",
                total_vectors=len(vectors),
                total_upserted=total_upserted,
                errors_count=len(errors)
            )

            return {
                "total_vectors": len(vectors),
                "upserted_count": total_upserted,
                "errors": errors
            }

        except Exception as e:
            logger.error("vector_upsert_failed", error=str(e))
            raise RetrievalError(
                f"Failed to upsert vectors: {str(e)}",
                details={"vector_count": len(vectors)}
            )

    async def search_vectors(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filter_dict: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True,
        include_values: bool = False
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors"""
        try:
            # Build search query
            search_params = {
                "vector": query_vector,
                "top_k": top_k,
                "include_metadata": include_metadata,
                "include_values": include_values
            }

            # Add filter if provided
            if filter_dict:
                search_params["filter"] = filter_dict

            # Execute search
            response = self.index.query(**search_params)

            # Process results
            results = []
            for match in response.get("matches", []):
                result = {
                    "id": match.get("id"),
                    "score": match.get("score", 0.0),
                    "metadata": match.get("metadata", {}),
                }

                if include_values:
                    result["values"] = match.get("values", [])

                results.append(result)

            logger.debug(
                "vector_search_completed",
                top_k=top_k,
                results_count=len(results),
                has_filter=filter_dict is not None
            )

            return results

        except PineconeException as e:
            logger.error("pinecone_search_failed", error=str(e))
            raise RetrievalError(
                f"Pinecone search failed: {str(e)}",
                details={"top_k": top_k, "has_filter": filter_dict is not None}
            )
        except Exception as e:
            logger.error("vector_search_failed", error=str(e))
            raise

    async def get_vector_by_id(
        self,
        vector_id: str,
        include_metadata: bool = True,
        include_values: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get a specific vector by ID"""
        try:
            response = self.index.fetch(
                ids=[vector_id],
                include_metadata=include_metadata,
                include_values=include_values
            )

            vectors = response.get("vectors", {})
            if vector_id in vectors:
                return vectors[vector_id]
            return None

        except Exception as e:
            logger.error("fetch_vector_failed", vector_id=vector_id, error=str(e))
            raise RetrievalError(
                f"Failed to fetch vector {vector_id}: {str(e)}"
            )

    async def delete_vectors(
        self,
        vector_ids: List[str],
        delete_all: bool = False,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Delete vectors from the database"""
        try:
            if delete_all:
                # Delete all vectors (with optional filter)
                response = self.index.delete(delete_all=True, filter=filter_dict)
            elif filter_dict:
                # Delete by filter
                response = self.index.delete(filter=filter_dict)
            else:
                # Delete by IDs
                response = self.index.delete(ids=vector_ids)

            deleted_count = response.get("deleted_count", 0)

            logger.info(
                "vectors_deleted",
                deleted_count=deleted_count,
                delete_all=delete_all,
                has_filter=filter_dict is not None,
                ids_count=len(vector_ids) if vector_ids else 0
            )

            return {
                "deleted_count": deleted_count,
                "delete_all": delete_all,
                "has_filter": filter_dict is not None,
                "ids_count": len(vector_ids) if vector_ids else 0
            }

        except Exception as e:
            logger.error("vector_deletion_failed", error=str(e))
            raise RetrievalError(
                f"Failed to delete vectors: {str(e)}",
                details={"delete_all": delete_all, "ids_count": len(vector_ids) if vector_ids else 0}
            )

    async def update_vector_metadata(
        self,
        vector_id: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """Update metadata for a specific vector"""
        try:
            # First, get the existing vector
            existing_vector = await self.get_vector_by_id(vector_id, include_values=True)
            if not existing_vector:
                raise RetrievalError(f"Vector {vector_id} not found")

            # Update metadata
            updated_metadata = existing_vector.get("metadata", {})
            updated_metadata.update(metadata)

            # Update the vector
            response = self.index.upsert(
                vectors=[{
                    "id": vector_id,
                    "values": existing_vector.get("values", []),
                    "metadata": updated_metadata
                }]
            )

            success = response.get("upserted_count", 0) > 0
            if success:
                logger.info("vector_metadata_updated", vector_id=vector_id)

            return success

        except Exception as e:
            logger.error("vector_metadata_update_failed", vector_id=vector_id, error=str(e))
            raise RetrievalError(
                f"Failed to update vector metadata: {str(e)}",
                details={"vector_id": vector_id}
            )

    async def get_index_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        try:
            stats = self.index.describe_index_stats()

            return {
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness,
                "total_vector_count": stats.total_vector_count,
                "namespaces": stats.namespaces
            }

        except Exception as e:
            logger.error("index_stats_failed", error=str(e))
            raise RetrievalError(f"Failed to get index stats: {str(e)}")

    async def create_user_filter(self, user_id: str) -> Dict[str, Any]:
        """Create a filter for user-specific vectors"""
        return {"user_id": user_id}

    async def create_document_filter(
        self,
        user_id: str,
        document_ids: Optional[List[str]] = None,
        file_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a filter for document-specific search"""
        filter_dict = {"user_id": user_id}

        if document_ids:
            filter_dict["doc_id"] = {"$in": document_ids}

        if file_types:
            filter_dict["file_type"] = {"$in": file_types}

        return filter_dict

    async def test_connection(self) -> bool:
        """Test connection to Pinecone"""
        try:
            # Try to get index stats
            stats = await self.get_index_stats()
            logger.info("pinecone_connection_test_success", stats=stats)
            return True

        except Exception as e:
            logger.error("pinecone_connection_test_failed", error=str(e))
            return False

    async def backup_index_data(
        self,
        backup_prefix: str = "backup"
    ) -> Dict[str, Any]:
        """Create a backup snapshot of index data"""
        try:
            timestamp = int(time.time())
            backup_name = f"{backup_prefix}_{timestamp}"

            # Note: This is a simplified backup approach
            # In production, you might want to use Pinecone's collection feature
            # or implement a more sophisticated backup strategy

            # Get all vectors (this might be expensive for large indexes)
            stats = await self.get_index_stats()
            total_vectors = stats.get("total_vector_count", 0)

            logger.info(
                "index_backup_initiated",
                backup_name=backup_name,
                total_vectors=total_vectors
            )

            return {
                "backup_name": backup_name,
                "total_vectors": total_vectors,
                "timestamp": timestamp,
                "status": "initiated"
                # Note: Actual backup implementation would go here
            }

        except Exception as e:
            logger.error("index_backup_failed", error=str(e))
            raise RetrievalError(f"Failed to create backup: {str(e)}")