"""Vector Store Service"""
import uuid
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
from datetime import datetime


class VectorStore:
    """Simple vector store for RAG"""
    
    def __init__(self, store_dir: Path):
        self.store_dir = store_dir
        self.store_dir.mkdir(parents=True, exist_ok=True)
        
        self.index_path = store_dir / "index.json"
        self.vectors_path = store_dir / "vectors.npy"
        
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.vectors: Optional[np.ndarray] = None
        self.doc_ids: List[str] = []
        
        self._load()
    
    def _load(self):
        """Load existing index"""
        if self.index_path.exists():
            with open(self.index_path) as f:
                data = json.load(f)
                self.documents = data.get("documents", {})
                self.doc_ids = data.get("doc_ids", [])
        
        if self.vectors_path.exists():
            self.vectors = np.load(self.vectors_path)
    
    def _save(self):
        """Save index"""
        with open(self.index_path, "w") as f:
            json.dump({
                "documents": self.documents,
                "doc_ids": self.doc_ids
            }, f)
        
        if self.vectors is not None:
            np.save(self.vectors_path, self.vectors)
    
    async def add_document(
        self,
        text: str,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Add document to store"""
        doc_id = str(uuid.uuid4())
        
        # Chunk text
        chunks = self._chunk_text(text, chunk_size=500, overlap=50)
        
        # Generate embeddings (simplified)
        embeddings = [self._embed(chunk) for chunk in chunks]
        
        # Store
        self.documents[doc_id] = {
            "id": doc_id,
            "chunks": chunks,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat()
        }
        
        # Add to vector index
        new_vectors = np.array(embeddings)
        
        if self.vectors is None:
            self.vectors = new_vectors
        else:
            self.vectors = np.vstack([self.vectors, new_vectors])
        
        # Track doc IDs per vector
        for _ in chunks:
            self.doc_ids.append(doc_id)
        
        self._save()
        
        return doc_id
    
    def _chunk_text(
        self,
        text: str,
        chunk_size: int = 500,
        overlap: int = 50
    ) -> List[str]:
        """Split text into chunks"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - overlap
        
        return chunks
    
    def _embed(self, text: str) -> np.ndarray:
        """Generate embedding (placeholder)"""
        # Real implementation would use sentence-transformers
        np.random.seed(hash(text) % (2**32))
        return np.random.randn(384).astype(np.float32)
    
    async def search(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks"""
        if self.vectors is None or len(self.vectors) == 0:
            return []
        
        # Generate query embedding
        query_vec = self._embed(query)
        
        # Compute cosine similarity
        similarities = np.dot(self.vectors, query_vec) / (
            np.linalg.norm(self.vectors, axis=1) * np.linalg.norm(query_vec)
        )
        
        # Get top-k
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            doc_id = self.doc_ids[idx]
            doc = self.documents[doc_id]
            chunk_idx = sum(1 for i, d in enumerate(self.doc_ids[:idx]) if d == doc_id)
            
            results.append({
                "text": doc["chunks"][chunk_idx] if chunk_idx < len(doc["chunks"]) else "",
                "score": float(similarities[idx]),
                "metadata": doc["metadata"],
                "document_id": doc_id
            })
        
        return results
    
    async def list_documents(self) -> List[Dict[str, Any]]:
        """List all documents"""
        return [
            {
                "id": doc_id,
                "filename": doc["metadata"].get("filename", "Unknown"),
                "chunks": len(doc["chunks"]),
                "created_at": doc["created_at"]
            }
            for doc_id, doc in self.documents.items()
        ]
    
    async def delete_document(self, doc_id: str) -> bool:
        """Delete document"""
        if doc_id not in self.documents:
            return False
        
        # Remove vectors
        indices_to_remove = [i for i, d in enumerate(self.doc_ids) if d == doc_id]
        
        if self.vectors is not None:
            self.vectors = np.delete(self.vectors, indices_to_remove, axis=0)
        
        self.doc_ids = [d for d in self.doc_ids if d != doc_id]
        del self.documents[doc_id]
        
        self._save()
        
        return True