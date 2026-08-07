"""
Embedding generation pipeline.
Converts text chunks into vectors using sentence-transformers.
Handles batching. Handles memory.
"""

import logging
import numpy as np
from typing import List, Optional

from .config import VectorStoreConfig

logger = logging.getLogger("sovereign.vectorstore.embeddings")


class EmbeddingPipeline:
    """
    Generate embeddings from text.
    Loads model once. Reuses.
    Batch processing.
    """

    def __init__(self, config: VectorStoreConfig):
        self.config = config
        self._model = None
        self._dimension = config.embedding_dimension

    def load_model(self):
        """
        Load embedding model.
        Lazy loading - only when first needed.
        """
        if self._model is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer
            from app.config import settings

            logger.info(
                f"Loading embedding model: {self.config.embedding_model}"
            )
            self._model = SentenceTransformer(
                self.config.embedding_model,
                cache_folder=str(settings.models_dir)
            )
            # Verify dimension
            test_embedding = self._model.encode(["test"])
            actual_dim = test_embedding.shape[1]

            if actual_dim != self._dimension:
                logger.warning(
                    f"Embedding dimension mismatch: "
                    f"config={self._dimension}, actual={actual_dim}. "
                    f"Using actual."
                )
                self._dimension = actual_dim

            logger.info(
                f"Embedding model loaded. Dimension: {self._dimension}"
            )

        except ImportError:
            logger.error(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
            raise
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    def embed_texts(self, texts: List[str],
                    batch_size: int = 32,
                    show_progress: bool = False) -> np.ndarray:
        """
        Generate embeddings for a list of texts.

        Returns:
            numpy array of shape (len(texts), dimension)
        """
        self.load_model()

        if not texts:
            return np.array([]).reshape(0, self._dimension)

        logger.info(f"Embedding {len(texts)} texts (batch_size={batch_size})")

        embeddings = self._model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            normalize_embeddings=self.config.normalize_embeddings,
            convert_to_numpy=True
        )

        # Ensure float32
        embeddings = embeddings.astype(np.float32)

        logger.info(
            f"Generated embeddings: shape={embeddings.shape}"
        )
        return embeddings

    def embed_single(self, text: str) -> np.ndarray:
        """Embed a single text. Returns 1D vector."""
        self.load_model()
        embedding = self._model.encode(
            [text],
            normalize_embeddings=self.config.normalize_embeddings,
            convert_to_numpy=True
        )
        return embedding[0].astype(np.float32)

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimension

    def unload_model(self):
        """Unload model to free memory."""
        self._model = None
        logger.info("Embedding model unloaded")