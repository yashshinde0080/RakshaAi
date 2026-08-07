"""
FAISS index builder.
Handles index creation, training, and persistence.
Supports Flat, IVFFlat, and IVFPQ index types.
"""

import os
import logging
import numpy as np
import faiss

from .config import VectorStoreConfig

logger = logging.getLogger("sovereign.vectorstore.index")


class FAISSIndexBuilder:
    """
    Build and manage FAISS index.

    Index types:
    - Flat: Exact search. Best for small datasets (<100K vectors).
    - IVFFlat: Approximate. Good for medium datasets.
    - IVFPQ: Compressed. Good for large datasets.
    """

    def __init__(self, config: VectorStoreConfig):
        self.config = config
        self._index: faiss.Index = None
        self._is_trained = False
        self._total_vectors = 0

        # Ensure directory exists
        os.makedirs(config.index_path, exist_ok=True)

    def create_index(self) -> faiss.Index:
        """
        Create new FAISS index based on config.
        """
        dimension = self.config.embedding_dimension
        index_type = self.config.index_type

        logger.info(
            f"Creating FAISS index: type={index_type}, "
            f"dim={dimension}"
        )

        if index_type == "Flat":
            # Exact search. No training needed.
            if self.config.normalize_embeddings:
                self._index = faiss.IndexFlatIP(dimension)  # Inner product for normalized = cosine
            else:
                self._index = faiss.IndexFlatL2(dimension)
            self._is_trained = True

        elif index_type == "IVFFlat":
            nlist = self.config.nlist
            if self.config.normalize_embeddings:
                quantizer = faiss.IndexFlatIP(dimension)
                self._index = faiss.IndexIVFFlat(
                    quantizer, dimension, nlist,
                    faiss.METRIC_INNER_PRODUCT
                )
            else:
                quantizer = faiss.IndexFlatL2(dimension)
                self._index = faiss.IndexIVFFlat(
                    quantizer, dimension, nlist
                )
            self._is_trained = False

        elif index_type == "IVFPQ":
            nlist = self.config.nlist
            m = 8  # number of sub-quantizers
            bits = 8  # bits per sub-quantizer
            quantizer = faiss.IndexFlatL2(dimension)
            self._index = faiss.IndexIVFPQ(
                quantizer, dimension, nlist, m, bits
            )
            self._is_trained = False

        else:
            raise ValueError(f"Unknown index type: {index_type}")

        logger.info(f"FAISS index created: {index_type}")
        return self._index

    def train(self, vectors: np.ndarray):
        """
        Train index (required for IVF-based indices).
        """
        if self._index is None:
            self.create_index()

        if self._is_trained:
            logger.info("Index already trained (Flat type)")
            return

        n_vectors = vectors.shape[0]
        min_training = max(self.config.nlist * 40, 256)

        if n_vectors < min_training:
            logger.warning(
                f"Training vectors ({n_vectors}) < recommended "
                f"minimum ({min_training}). Index quality may suffer."
            )

        logger.info(f"Training FAISS index with {n_vectors} vectors")
        self._index.train(vectors)
        self._is_trained = True
        logger.info("FAISS index trained successfully")

    def add_vectors(self, vectors: np.ndarray):
        """
        Add vectors to index.
        Index must be trained first for IVF types.
        """
        if self._index is None:
            self.create_index()

        if not self._is_trained:
            raise RuntimeError(
                "Index not trained. Call train() first with "
                "representative vectors."
            )

        vectors = vectors.astype(np.float32)
        n_vectors = vectors.shape[0]

        self._index.add(vectors)
        self._total_vectors += n_vectors

        logger.info(
            f"Added {n_vectors} vectors. "
            f"Total: {self._total_vectors}"
        )

    def search(self, query_vectors: np.ndarray,
               top_k: int = 5) -> tuple:
        """
        Search index.

        Returns:
            (distances, indices) - both numpy arrays
            Shape: (n_queries, top_k)
        """
        if self._index is None or self._total_vectors == 0:
            empty_d = np.array([]).reshape(0, top_k)
            empty_i = np.array([], dtype=np.int64).reshape(0, top_k)
            return empty_d, empty_i

        query_vectors = query_vectors.astype(np.float32)

        # Set nprobe for IVF indices
        if hasattr(self._index, 'nprobe'):
            self._index.nprobe = self.config.nprobe

        distances, indices = self._index.search(query_vectors, top_k)
        return distances, indices

    def save(self):
        """Save index to disk."""
        if self._index is None:
            logger.warning("No index to save")
            return

        index_path = self.config.index_full_path
        faiss.write_index(self._index, index_path)
        logger.info(
            f"FAISS index saved: {index_path} "
            f"({self._total_vectors} vectors)"
        )

    def load(self) -> bool:
        """
        Load index from disk.
        Returns True if loaded successfully.
        """
        index_path = self.config.index_full_path

        if not os.path.exists(index_path):
            logger.info("No existing FAISS index found")
            return False

        try:
            self._index = faiss.read_index(index_path)
            self._total_vectors = self._index.ntotal
            self._is_trained = True  # If loaded, it's trained

            logger.info(
                f"FAISS index loaded: {self._total_vectors} vectors"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to load FAISS index: {e}")
            return False

    def reset(self):
        """Delete index and start fresh."""
        index_path = self.config.index_full_path
        if os.path.exists(index_path):
            os.remove(index_path)
            logger.info("FAISS index file deleted")

        self._index = None
        self._is_trained = False
        self._total_vectors = 0

    @property
    def total_vectors(self) -> int:
        if self._index is not None:
            return self._index.ntotal
        return 0

    @property
    def is_trained(self) -> bool:
        return self._is_trained

    @property
    def index(self) -> faiss.Index:
        return self._index