"""
Schemas for vector store operations.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class TextChunk(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    chunk_index: int
    start_char: int
    end_char: int
    token_count: int = 0
    metadata: Dict[str, Any] = {}


class EmbeddingRecord(BaseModel):
    embedding_id: str
    chunk_id: str
    document_id: str
    vector_index: int  # position in FAISS index
    dimension: int = 384
    norm: float = 0.0
    created_at: Optional[str] = None


class SearchQuery(BaseModel):
    query_text: str
    top_k: int = 5
    score_threshold: float = 0.0
    filter_document_id: Optional[str] = None


class SearchResult(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    score: float
    chunk_index: int
    metadata: Dict[str, Any] = {}


class RAGContext(BaseModel):
    query: str
    results: List[SearchResult]
    total_tokens: int = 0
    context_text: str = ""