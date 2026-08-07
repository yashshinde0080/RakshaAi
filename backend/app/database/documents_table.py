"""
Document tracking for RAG pipeline.
Every document uploaded is tracked from ingestion to indexing.
"""

import sqlite3
import logging
from typing import Optional, List
from .connection import ConnectionPool
from app.schemas.db_schemas import DocumentRecord

logger = logging.getLogger("sovereign.db.documents")


class DocumentsTable:

    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def insert(self, doc: DocumentRecord) -> int:
        """Register new document."""
        with self.pool.transaction() as pool:
            cursor = pool.execute(
                """
                INSERT INTO documents (
                    document_id, filename, file_path,
                    file_size_bytes, mime_type,
                    checksum_sha256, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc.document_id, doc.filename, doc.file_path,
                    doc.file_size_bytes, doc.mime_type,
                    doc.checksum_sha256, doc.status
                )
            )
            return cursor.lastrowid

    def update_status(self, document_id: str, status: str,
                      total_chunks: int = 0,
                      total_embeddings: int = 0):
        """Update document processing status."""
        with self.pool.transaction() as pool:
            if status in ("embedded", "indexed"):
                pool.execute(
                    """
                    UPDATE documents
                    SET status = ?,
                        total_chunks = ?,
                        total_embeddings = ?,
                        processed_at = datetime('now')
                    WHERE document_id = ?
                    """,
                    (status, total_chunks, total_embeddings, document_id)
                )
            else:
                pool.execute(
                    """
                    UPDATE documents
                    SET status = ?
                    WHERE document_id = ?
                    """,
                    (status, document_id)
                )

    def get(self, document_id: str) -> Optional[DocumentRecord]:
        """Get document by ID."""
        cursor = self.pool.execute(
            "SELECT * FROM documents WHERE document_id = ?",
            (document_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

    def list_all(self) -> List[DocumentRecord]:
        """List all documents."""
        cursor = self.pool.execute(
            "SELECT * FROM documents ORDER BY created_at DESC"
        )
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def list_by_status(self, status: str) -> List[DocumentRecord]:
        """List documents by status."""
        cursor = self.pool.execute(
            "SELECT * FROM documents WHERE status = ?",
            (status,)
        )
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def delete(self, document_id: str):
        """Delete document record."""
        with self.pool.transaction() as pool:
            pool.execute(
                "DELETE FROM documents WHERE document_id = ?",
                (document_id,)
            )
        logger.info(f"Document deleted: {document_id}")

    def count(self) -> int:
        """Total document count."""
        cursor = self.pool.execute(
            "SELECT COUNT(*) as c FROM documents"
        )
        return cursor.fetchone()["c"]

    def get_total_chunks(self) -> int:
        """Total chunks across all documents."""
        cursor = self.pool.execute(
            "SELECT COALESCE(SUM(total_chunks), 0) as t FROM documents"
        )
        return cursor.fetchone()["t"]

    def _row_to_record(self, row: sqlite3.Row) -> DocumentRecord:
        return DocumentRecord(
            id=row["id"],
            document_id=row["document_id"],
            filename=row["filename"],
            file_path=row["file_path"],
            file_size_bytes=row["file_size_bytes"],
            mime_type=row["mime_type"],
            total_chunks=row["total_chunks"],
            total_embeddings=row["total_embeddings"],
            checksum_sha256=row["checksum_sha256"],
            status=row["status"],
            created_at=row["created_at"],
            processed_at=row["processed_at"]
        )