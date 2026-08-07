"""
Retriever.
Takes a query, searches FAISS, returns ranked results with content.
Handles score thresholds, document filtering, and context construction.
"""

import logging
import numpy as np
from typing import List, Optional

from .config import VectorStoreConfig
from .index_builder import FAISSIndexBuilder
from .store import VectorMetadataStore
from .embedding_pipeline import EmbeddingPipeline
from app.schemas.vector_schemas import SearchQuery, SearchResult, RAGContext

logger = logging.getLogger("sovereign.vectorstore.retriever")


class Retriever:
    """
    Retrieve relevant chunks for a query.
    Combines FAISS search with metadata lookup.
    """

    def __init__(self, config: VectorStoreConfig,
                 index: FAISSIndexBuilder,
                 metadata_store: VectorMetadataStore,
                 embedding_pipeline: EmbeddingPipeline):
        self.config = config
        self.index = index
        self.metadata_store = metadata_store
        self.embedding_pipeline = embedding_pipeline

    def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Search for relevant chunks.

        Steps:
        1. Embed query text
        2. Search FAISS index
        3. Lookup metadata for results
        4. Apply filters and thresholds
        5. Return ranked results
        """
        if self.index.total_vectors == 0:
            logger.warning("Index is empty. No results.")
            return []

        # Step 1: Embed query
        query_vector = self.embedding_pipeline.embed_single(
            query.query_text
        )
        query_vector = query_vector.reshape(1, -1)

        # Step 2: Search FAISS
        top_k = query.top_k or self.config.top_k_default
        distances, indices = self.index.search(query_vector, top_k)

        distances = distances[0]  # First (only) query
        indices = indices[0]

        # Step 3: Lookup metadata
        valid_indices = [int(i) for i in indices if i >= 0]
        if not valid_indices:
            return []

        chunk_data_list = self.metadata_store.get_chunks_by_vector_indices(
            valid_indices
        )

        # Step 4: Build results with filtering
        results = []
        for i, (idx, dist) in enumerate(zip(indices, distances)):
            if idx < 0:
                continue

            # Score conversion
            # For IP (normalized = cosine similarity): higher is better
            # For L2: lower is better, convert to similarity
            if self.config.normalize_embeddings:
                score = float(dist)  # Already cosine similarity
            else:
                score = 1.0 / (1.0 + float(dist))  # Convert L2 to similarity

            # Apply threshold
            if query.score_threshold > 0 and score < query.score_threshold:
                continue

            # Get chunk data
            position = valid_indices.index(int(idx)) if int(idx) in valid_indices else -1
            if position < 0 or position >= len(chunk_data_list):
                continue

            chunk_data = chunk_data_list[position]
            if chunk_data is None:
                continue

            # Apply document filter
            if (query.filter_document_id and
                    chunk_data["document_id"] != query.filter_document_id):
                continue

            results.append(SearchResult(
                chunk_id=chunk_data["chunk_id"],
                document_id=chunk_data["document_id"],
                content=chunk_data["content"],
                score=score,
                chunk_index=chunk_data["chunk_index"],
                metadata=chunk_data["metadata"]
            ))

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)

        logger.info(
            f"Search returned {len(results)} results "
            f"for query: '{query.query_text[:50]}...'"
        )
        return results

    def build_rag_context(self, query: SearchQuery,
                          max_tokens: int = 2048) -> RAGContext:
        """
        Build RAG context from search results.
        Respects token budget.
        Deduplicates content.
        """
        results = self.search(query)

        context_parts = []
        total_tokens = 0
        seen_chunks = set()
        filtered_results = []

        for result in results:
            if result.chunk_id in seen_chunks:
                continue
            seen_chunks.add(result.chunk_id)

            # Estimate tokens (rough: 4 chars per token)
            chunk_tokens = len(result.content) // 4

            if total_tokens + chunk_tokens > max_tokens:
                # Check if we can fit a partial chunk
                remaining_tokens = max_tokens - total_tokens
                if remaining_tokens > 50:  # Worth including partial
                    doc_name = result.metadata.get("filename", result.document_id)
                    truncated = result.content[:remaining_tokens * 4]
                    formatted_chunk = f"[Source: {doc_name}]\n{truncated}"
                    context_parts.append(formatted_chunk)
                    total_tokens += remaining_tokens
                    filtered_results.append(result)
                break

            doc_name = result.metadata.get("filename", result.document_id)
            formatted_chunk = f"[Source: {doc_name}]\n{result.content}"
            context_parts.append(formatted_chunk)
            total_tokens += chunk_tokens
            filtered_results.append(result)

        context_text = "\n\n---\n\n".join(context_parts)

        return RAGContext(
            query=query.query_text,
            results=filtered_results,
            total_tokens=total_tokens,
            context_text=context_text
        )