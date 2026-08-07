"""
Vector Store Manager.
Single entry point for all vector operations.
Document ingestion → Chunking → Embedding → Indexing → Search.
"""

import os
import uuid
import hashlib
import logging
import numpy as np
from typing import List, Optional

from .config import VectorStoreConfig, load_vector_config
from .chunker import DocumentChunker
from .embedding_pipeline import EmbeddingPipeline
from .index_builder import FAISSIndexBuilder
from .store import VectorMetadataStore
from .retriever import Retriever
from app.schemas.vector_schemas import (
    TextChunk, EmbeddingRecord, SearchQuery,
    SearchResult, RAGContext
)

logger = logging.getLogger("sovereign.vectorstore")


class VectorStoreManager:
    """
    Central vector store manager.

    Usage:
        vs = VectorStoreManager()
        vs.initialize()

        # Ingest document
        doc_id = vs.ingest_text("Full document text here", "doc.pdf")

        # Search
        results = vs.search("What is the main idea?")

        # RAG context
        context = vs.build_context("What is the main idea?")

        vs.shutdown()
    """

    def __init__(self, config_path: str = "config/storage.toml"):
        self.config = load_vector_config(config_path)
        self.chunker = DocumentChunker(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            max_chunks=self.config.max_chunks_per_document
        )
        self.embedding_pipeline = EmbeddingPipeline(self.config)
        self.index_builder = FAISSIndexBuilder(self.config)
        self.metadata_store = VectorMetadataStore(
            self.config.metadata_db_path
        )
        self.retriever = Retriever(
            config=self.config,
            index=self.index_builder,
            metadata_store=self.metadata_store,
            embedding_pipeline=self.embedding_pipeline
        )
        self._initialized = False

    def initialize(self):
        """
        Initialize vector store.
        Load existing index or create new.
        """
        logger.info("Initializing vector store")

        # Try to load existing index
        loaded = self.index_builder.load()

        if not loaded:
            logger.info("No existing index. Will create on first ingest.")

        self._initialized = True
        logger.info(
            f"Vector store initialized. "
            f"Vectors: {self.index_builder.total_vectors}"
        )

    def ingest_text(self, text: str, filename: str,
                    document_id: Optional[str] = None,
                    metadata: Optional[dict] = None) -> str:
        """
        Full ingestion pipeline:
        1. Generate document ID
        2. Chunk text
        3. Generate embeddings
        4. Add to FAISS index
        5. Store metadata

        Returns: document_id
        """
        if not self._initialized:
            raise RuntimeError("Vector store not initialized")

        # Generate document ID
        if document_id is None:
            document_id = self._generate_document_id(text, filename)

        logger.info(
            f"Ingesting document: {filename} (id={document_id})"
        )

        # Step 1: Chunk
        chunks = self.chunker.chunk_text(text, document_id)
        if not chunks:
            logger.warning(f"No chunks generated for {filename}")
            return document_id

        # Add filename to chunk metadata
        if metadata:
            for chunk in chunks:
                chunk.metadata.update(metadata)
                chunk.metadata["filename"] = filename
        else:
            for chunk in chunks:
                chunk.metadata["filename"] = filename

        # Step 2: Store chunks in metadata DB
        self.metadata_store.insert_chunks_batch(chunks)

        # Step 3: Generate embeddings
        texts = [chunk.content for chunk in chunks]
        embeddings = self.embedding_pipeline.embed_texts(
            texts, batch_size=32, show_progress=True
        )

        # Step 4: Handle FAISS index
        start_index = self.metadata_store.get_next_vector_index()

        # If index doesn't exist or needs training
        if self.index_builder.index is None:
            self.index_builder.create_index()

        # Train if needed (IVF indices)
        if not self.index_builder.is_trained:
            if embeddings.shape[0] >= self.config.nlist:
                self.index_builder.train(embeddings)
            else:
                # Not enough vectors for IVF training
                # Fall back to Flat index
                logger.warning(
                    "Not enough vectors for IVF training. "
                    "Using Flat index instead."
                )
                self.config.index_type = "Flat"
                self.index_builder.reset()
                self.index_builder.create_index()

        # Add to FAISS
        self.index_builder.add_vectors(embeddings)

        # Step 5: Store embedding metadata
        embedding_records = []
        for i, chunk in enumerate(chunks):
            vector_index = start_index + i
            norm = float(np.linalg.norm(embeddings[i]))
            embedding_records.append(EmbeddingRecord(
                embedding_id=f"{chunk.chunk_id}_emb",
                chunk_id=chunk.chunk_id,
                document_id=document_id,
                vector_index=vector_index,
                dimension=self.config.embedding_dimension,
                norm=norm
            ))

        self.metadata_store.insert_embeddings_batch(embedding_records)

        # Step 6: Save index to disk
        self.index_builder.save()

        # Save state
        self.metadata_store.save_state(
            "total_vectors",
            str(self.index_builder.total_vectors)
        )

        logger.info(
            f"Document ingested: {filename} "
            f"({len(chunks)} chunks, "
            f"{len(embedding_records)} embeddings)"
        )
        return document_id

    def search(self, query_text: str,
               top_k: int = 5,
               score_threshold: float = 0.0,
               filter_document_id: Optional[str] = None
               ) -> List[SearchResult]:
        """
        Search for relevant chunks.
        """
        if not self._initialized:
            raise RuntimeError("Vector store not initialized")

        query = SearchQuery(
            query_text=query_text,
            top_k=top_k,
            score_threshold=score_threshold,
            filter_document_id=filter_document_id
        )
        return self.retriever.search(query)

    def build_context(self, query_text: str,
                      top_k: int = 5,
                      max_tokens: int = 2048,
                      score_threshold: float = 0.0) -> RAGContext:
        """
        Build RAG context for prompt construction.
        """
        if not self._initialized:
            raise RuntimeError("Vector store not initialized")

        query = SearchQuery(
            query_text=query_text,
            top_k=top_k,
            score_threshold=score_threshold
        )
        return self.retriever.build_rag_context(query, max_tokens)

    def delete_document(self, document_id: str):
        """
        Delete a document and its vectors.
        WARNING: Requires index rebuild for consistency.
        """
        self.metadata_store.delete_document_data(document_id)
        logger.warning(
            f"Document {document_id} deleted from metadata. "
            f"FAISS index rebuild recommended."
        )

    def rebuild_index(self):
        """
        Full index rebuild from metadata store.
        Use after document deletion.
        """
        logger.info("Starting full index rebuild")

        # Get all documents
        doc_ids = self.metadata_store.get_document_ids()

        if not doc_ids:
            logger.info("No documents. Resetting index.")
            self.index_builder.reset()
            return

        # Reset FAISS index
        self.index_builder.reset()
        self.index_builder.create_index()

        # Re-embed all chunks
        all_embeddings = []
        all_chunks = []
        new_embedding_records = []

        for doc_id in doc_ids:
            chunks_data = self.metadata_store.get_chunks_by_document(doc_id)
            texts = [c["content"] for c in chunks_data]

            if not texts:
                continue

            embeddings = self.embedding_pipeline.embed_texts(texts)

            for i, chunk_data in enumerate(chunks_data):
                vector_index = len(all_embeddings) + i
                norm = float(np.linalg.norm(embeddings[i]))
                new_embedding_records.append(EmbeddingRecord(
                    embedding_id=f"{chunk_data['chunk_id']}_emb",
                    chunk_id=chunk_data["chunk_id"],
                    document_id=doc_id,
                    vector_index=vector_index,
                    dimension=self.config.embedding_dimension,
                    norm=norm
                ))

            all_embeddings.append(embeddings)

        if not all_embeddings:
            logger.info("No embeddings to rebuild")
            return

        # Concatenate all embeddings
        combined = np.vstack(all_embeddings)

        # Train if needed
        if not self.index_builder.is_trained:
            if combined.shape[0] >= self.config.nlist:
                self.index_builder.train(combined)
            else:
                self.config.index_type = "Flat"
                self.index_builder.reset()
                self.index_builder.create_index()

        # Add all vectors
        self.index_builder.add_vectors(combined)

        # Update embedding records
        self.metadata_store.insert_embeddings_batch(new_embedding_records)

        # Save
        self.index_builder.save()

        logger.info(
            f"Index rebuilt: {self.index_builder.total_vectors} vectors"
        )

    def get_document_chunks(self, document_id: str) -> List[dict]:
        """Get all chunks (content + metadata) for a document, in order."""
        if not self._initialized:
            raise RuntimeError("Vector store not initialized")
        return self.metadata_store.get_chunks_by_document(document_id)

    def get_stats(self) -> dict:
        """Get vector store statistics."""
        return {
            "total_vectors": self.index_builder.total_vectors,
            "total_chunks": self.metadata_store.get_total_chunks(),
            "total_embeddings": self.metadata_store.get_total_embeddings(),
            "total_documents": len(self.metadata_store.get_document_ids()),
            "index_trained": self.index_builder.is_trained,
            "index_type": self.config.index_type,
            "embedding_model": self.config.embedding_model,
            "embedding_dimension": self.config.embedding_dimension,
            "chunk_size": self.config.chunk_size,
        }

    def shutdown(self):
        """Clean shutdown."""
        if self.index_builder.total_vectors > 0:
            self.index_builder.save()
        self.metadata_store.close()
        self.embedding_pipeline.unload_model()
        logger.info("Vector store shut down")

    def _generate_document_id(self, text: str, filename: str) -> str:
        """Generate deterministic document ID."""
        content_hash = hashlib.sha256(
            text.encode('utf-8')
        ).hexdigest()[:12]
        return f"doc_{content_hash}"

    def list_documents(self) -> List[dict]:
        """List all indexed documents."""
        if not self._initialized:
            raise RuntimeError("Vector store not initialized")
            
        doc_ids = self.metadata_store.get_document_ids()
        result = []
        for doc_id in doc_ids:
            chunks = self.metadata_store.get_chunks_by_document(doc_id)
            if not chunks:
                continue
            first_chunk = chunks[0]
            metadata = first_chunk.get("metadata", {})
            result.append({
                "id": doc_id,
                "filename": metadata.get("filename", "Unknown"),
                "chunks": len(chunks),
                "created_at": first_chunk.get("created_at", "Unknown")
            })
        return result
