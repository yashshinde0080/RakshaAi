"""
Vector metadata store.
Separate SQLite database for vector chunk metadata.
Maps FAISS index positions to chunk/document metadata.
"""

import os
import sqlite3
import json
import logging
from typing import Optional, List, Dict, Any

from app.schemas.vector_schemas import TextChunk, EmbeddingRecord

logger = logging.getLogger("sovereign.vectorstore.store")


class VectorMetadataStore:
    """
    SQLite store for vector metadata.
    Maps FAISS index positions → chunk content + document info.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_db()

    def _ensure_db(self):
        """Create database and tables if not exist."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA foreign_keys = ON")

        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                content TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                start_char INTEGER DEFAULT 0,
                end_char INTEGER DEFAULT 0,
                token_count INTEGER DEFAULT 0,
                metadata_json TEXT DEFAULT '{}',
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_chunks_document
            ON chunks(document_id);

            CREATE INDEX IF NOT EXISTS idx_chunks_index
            ON chunks(chunk_index);

            CREATE TABLE IF NOT EXISTS embeddings (
                embedding_id TEXT PRIMARY KEY,
                chunk_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                vector_index INTEGER NOT NULL UNIQUE,
                dimension INTEGER DEFAULT 384,
                norm REAL DEFAULT 0.0,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_embeddings_vector_index
            ON embeddings(vector_index);

            CREATE INDEX IF NOT EXISTS idx_embeddings_document
            ON embeddings(document_id);

            CREATE TABLE IF NOT EXISTS index_state (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        self._conn.commit()

    def insert_chunk(self, chunk: TextChunk):
        """Insert a text chunk."""
        metadata_json = json.dumps(chunk.metadata)
        self._conn.execute(
            """
            INSERT OR REPLACE INTO chunks (
                chunk_id, document_id, content,
                chunk_index, start_char, end_char,
                token_count, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chunk.chunk_id, chunk.document_id,
                chunk.content, chunk.chunk_index,
                chunk.start_char, chunk.end_char,
                chunk.token_count, metadata_json
            )
        )

    def insert_chunks_batch(self, chunks: List[TextChunk]):
        """Insert multiple chunks in one transaction."""
        data = [
            (
                c.chunk_id, c.document_id, c.content,
                c.chunk_index, c.start_char, c.end_char,
                c.token_count, json.dumps(c.metadata)
            )
            for c in chunks
        ]
        self._conn.executemany(
            """
            INSERT OR REPLACE INTO chunks (
                chunk_id, document_id, content,
                chunk_index, start_char, end_char,
                token_count, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            data
        )
        self._conn.commit()
        logger.info(f"Inserted {len(chunks)} chunks")

    def insert_embedding(self, record: EmbeddingRecord):
        """Insert embedding metadata."""
        self._conn.execute(
            """
            INSERT OR REPLACE INTO embeddings (
                embedding_id, chunk_id, document_id,
                vector_index, dimension, norm
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                record.embedding_id, record.chunk_id,
                record.document_id, record.vector_index,
                record.dimension, record.norm
            )
        )

    def insert_embeddings_batch(self, records: List[EmbeddingRecord]):
        """Insert multiple embedding records."""
        data = [
            (
                r.embedding_id, r.chunk_id, r.document_id,
                r.vector_index, r.dimension, r.norm
            )
            for r in records
        ]
        self._conn.executemany(
            """
            INSERT OR REPLACE INTO embeddings (
                embedding_id, chunk_id, document_id,
                vector_index, dimension, norm
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            data
        )
        self._conn.commit()
        logger.info(f"Inserted {len(records)} embedding records")

    def get_chunk_by_vector_index(
            self, vector_index: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get chunk content and metadata by FAISS vector index.
        This is the critical lookup during search.
        """
        cursor = self._conn.execute(
            """
            SELECT c.chunk_id, c.document_id, c.content,
                   c.chunk_index, c.start_char, c.end_char,
                   c.token_count, c.metadata_json
            FROM embeddings e
            JOIN chunks c ON e.chunk_id = c.chunk_id
            WHERE e.vector_index = ?
            """,
            (vector_index,)
        )
        row = cursor.fetchone()
        if row is None:
            return None

        return {
            "chunk_id": row["chunk_id"],
            "document_id": row["document_id"],
            "content": row["content"],
            "chunk_index": row["chunk_index"],
            "start_char": row["start_char"],
            "end_char": row["end_char"],
            "token_count": row["token_count"],
            "metadata": json.loads(row["metadata_json"])
        }

    def get_chunks_by_vector_indices(
            self, indices: List[int]
    ) -> List[Optional[Dict[str, Any]]]:
        """
        Batch lookup for multiple FAISS indices.
        Preserves order matching input indices.
        """
        if not indices:
            return []

        # Build lookup dict
        placeholders = ','.join('?' * len(indices))
        cursor = self._conn.execute(
            f"""
            SELECT e.vector_index, c.chunk_id, c.document_id,
                   c.content, c.chunk_index, c.start_char,
                   c.end_char, c.token_count, c.metadata_json
            FROM embeddings e
            JOIN chunks c ON e.chunk_id = c.chunk_id
            WHERE e.vector_index IN ({placeholders})
            """,
            tuple(int(i) for i in indices)
        )

        lookup = {}
        for row in cursor.fetchall():
            lookup[row["vector_index"]] = {
                "chunk_id": row["chunk_id"],
                "document_id": row["document_id"],
                "content": row["content"],
                "chunk_index": row["chunk_index"],
                "start_char": row["start_char"],
                "end_char": row["end_char"],
                "token_count": row["token_count"],
                "metadata": json.loads(row["metadata_json"])
            }

        # Return in order
        return [lookup.get(int(i)) for i in indices]

    def get_chunks_by_document(
            self, document_id: str
    ) -> List[Dict[str, Any]]:
        """Get all chunks for a document."""
        cursor = self._conn.execute(
            """
            SELECT chunk_id, content, chunk_index,
                   start_char, end_char, token_count,
                   metadata_json, created_at
            FROM chunks
            WHERE document_id = ?
            ORDER BY chunk_index
            """,
            (document_id,)
        )
        results = []
        for row in cursor.fetchall():
            results.append({
                "chunk_id": row["chunk_id"],
                "document_id": document_id,
                "content": row["content"],
                "chunk_index": row["chunk_index"],
                "start_char": row["start_char"],
                "end_char": row["end_char"],
                "token_count": row["token_count"],
                "metadata": json.loads(row["metadata_json"]),
                "created_at": row["created_at"]
            })
        return results

    def delete_document_data(self, document_id: str):
        """
        Delete all chunks and embeddings for a document.
        Note: FAISS index positions become stale.
        Full rebuild recommended after deletion.
        """
        self._conn.execute(
            "DELETE FROM embeddings WHERE document_id = ?",
            (document_id,)
        )
        self._conn.execute(
            "DELETE FROM chunks WHERE document_id = ?",
            (document_id,)
        )
        self._conn.commit()
        logger.info(
            f"Deleted all data for document: {document_id}"
        )

    def get_next_vector_index(self) -> int:
        """Get the next available vector index."""
        cursor = self._conn.execute(
            "SELECT COALESCE(MAX(vector_index), -1) + 1 as next_idx "
            "FROM embeddings"
        )
        return cursor.fetchone()["next_idx"]

    def get_total_embeddings(self) -> int:
        """Total number of embeddings stored."""
        cursor = self._conn.execute(
            "SELECT COUNT(*) as c FROM embeddings"
        )
        return cursor.fetchone()["c"]

    def get_total_chunks(self) -> int:
        """Total number of chunks stored."""
        cursor = self._conn.execute(
            "SELECT COUNT(*) as c FROM chunks"
        )
        return cursor.fetchone()["c"]

    def get_document_ids(self) -> List[str]:
        """Get all unique document IDs."""
        cursor = self._conn.execute(
            "SELECT DISTINCT document_id FROM chunks ORDER BY document_id"
        )
        return [row["document_id"] for row in cursor.fetchall()]

    def save_state(self, key: str, value: str):
        """Save key-value state."""
        self._conn.execute(
            "INSERT OR REPLACE INTO index_state (key, value) VALUES (?, ?)",
            (key, value)
        )
        self._conn.commit()

    def get_state(self, key: str) -> Optional[str]:
        """Get saved state value."""
        cursor = self._conn.execute(
            "SELECT value FROM index_state WHERE key = ?",
            (key,)
        )
        row = cursor.fetchone()
        return row["value"] if row else None

    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None