"""
Vector store configuration.
Loaded from storage.toml.
"""

import os
import toml
from dataclasses import dataclass


@dataclass
class VectorStoreConfig:
    from app.config import settings
    index_path: str = str(settings.data_dir / "vector_index")
    index_file: str = "index.faiss"
    metadata_db: str = "metadata.db"
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    chunk_size: int = 512
    chunk_overlap: int = 64
    max_chunks_per_document: int = 10000
    nprobe: int = 10
    top_k_default: int = 5
    use_gpu: bool = False
    index_type: str = "IVFFlat"  # "Flat", "IVFFlat", "IVFPQ"
    nlist: int = 100
    normalize_embeddings: bool = True

    @property
    def index_full_path(self) -> str:
        return os.path.join(self.index_path, self.index_file)

    @property
    def metadata_db_path(self) -> str:
        return os.path.join(self.index_path, self.metadata_db)


def load_vector_config(config_path: str = "config/storage.toml") -> VectorStoreConfig:
    """Load vector store config from TOML file."""
    if not os.path.exists(config_path):
        return VectorStoreConfig()

    config = toml.load(config_path)
    vs_config = config.get("vectorstore", {})

    from app.config import settings
    return VectorStoreConfig(
        index_path=vs_config.get("index_path", str(settings.data_dir / "vector_index")),
        index_file=vs_config.get("index_file", "index.faiss"),
        metadata_db=vs_config.get("metadata_db", "metadata.db"),
        embedding_model=vs_config.get("embedding_model", "all-MiniLM-L6-v2"),
        embedding_dimension=vs_config.get("embedding_dimension", 384),
        chunk_size=vs_config.get("chunk_size", 512),
        chunk_overlap=vs_config.get("chunk_overlap", 64),
        max_chunks_per_document=vs_config.get("max_chunks_per_document", 10000),
        nprobe=vs_config.get("nprobe", 10),
        top_k_default=vs_config.get("top_k_default", 5),
        use_gpu=vs_config.get("use_gpu", False),
        index_type=vs_config.get("index_type", "IVFFlat"),
        nlist=vs_config.get("nlist", 100),
        normalize_embeddings=vs_config.get("normalize_embeddings", True),
    )