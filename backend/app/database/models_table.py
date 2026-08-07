"""
Model registry operations.
Every model that enters the system is tracked here.
"""

import sqlite3
import logging
from typing import Optional, List
from datetime import datetime

from .connection import ConnectionPool
from app.schemas.db_schemas import ModelRecord, ModelStatus, QuantType

logger = logging.getLogger("sovereign.db.models")


class ModelsTable:

    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def insert(self, model: ModelRecord) -> int:
        """
        Register a new model.
        Returns row id.
        Raises on duplicate.
        """
        try:
            with self.pool.transaction() as pool:
                cursor = pool.execute(
                    """
                    INSERT INTO models (
                        name, family, size_label, quant, file_path,
                        file_size_bytes, checksum_sha256, source, repo_id,
                        status, engines_supported, context_length,
                        hidden_size, num_layers, ram_required_mb
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        model.name, model.family, model.size_label,
                        model.quant.value, model.file_path,
                        model.file_size_bytes, model.checksum_sha256,
                        model.source, model.repo_id,
                        model.status.value, model.engines_supported,
                        model.context_length, model.hidden_size,
                        model.num_layers, model.ram_required_mb
                    )
                )
                row_id = cursor.lastrowid
                logger.info(f"Model registered: {model.name} (id={row_id})")
                return row_id

        except sqlite3.IntegrityError as e:
            logger.error(f"Model already exists: {model.name} - {e}")
            raise ValueError(f"Model {model.name} with quant {model.quant} already registered")

    def get_by_name(self, name: str) -> Optional[ModelRecord]:
        """Get model by name. Returns latest quant if multiple exist."""
        cursor = self.pool.execute(
            """
            SELECT * FROM models
            WHERE name = ? AND status != 'removed'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (name,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

    def get_by_name_and_quant(self, name: str, quant: str) -> Optional[ModelRecord]:
        """Get specific model variant."""
        cursor = self.pool.execute(
            """
            SELECT * FROM models
            WHERE name = ? AND quant = ? AND status != 'removed'
            LIMIT 1
            """,
            (name, quant)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

    def get_by_id(self, model_id: int) -> Optional[ModelRecord]:
        """Get model by database id."""
        cursor = self.pool.execute(
            "SELECT * FROM models WHERE id = ?",
            (model_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

    def list_all(self, include_removed: bool = False) -> List[ModelRecord]:
        """List all registered models."""
        if include_removed:
            cursor = self.pool.execute(
                "SELECT * FROM models ORDER BY family, size_label, quant"
            )
        else:
            cursor = self.pool.execute(
                """
                SELECT * FROM models
                WHERE status != 'removed'
                ORDER BY family, size_label, quant
                """
            )
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def list_by_family(self, family: str) -> List[ModelRecord]:
        """List all models of a family (e.g., 'llama3')."""
        cursor = self.pool.execute(
            """
            SELECT * FROM models
            WHERE family = ? AND status != 'removed'
            ORDER BY size_label, quant
            """,
            (family,)
        )
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def list_ready(self) -> List[ModelRecord]:
        """List only ready-to-use models."""
        cursor = self.pool.execute(
            """
            SELECT * FROM models
            WHERE status = 'ready'
            ORDER BY last_used_at DESC
            """
        )
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def update_status(self, name: str, status: ModelStatus):
        """Update model status."""
        with self.pool.transaction() as pool:
            pool.execute(
                "UPDATE models SET status = ? WHERE name = ?",
                (status.value, name)
            )
        logger.info(f"Model {name} status -> {status.value}")

    def update_last_used(self, name: str):
        """Update last used timestamp and increment use count."""
        with self.pool.transaction() as pool:
            pool.execute(
                """
                UPDATE models
                SET last_used_at = datetime('now'),
                    use_count = use_count + 1
                WHERE name = ?
                """,
                (name,)
            )

    def update_checksum(self, name: str, checksum: str):
        """Update checksum after verification."""
        with self.pool.transaction() as pool:
            pool.execute(
                "UPDATE models SET checksum_sha256 = ? WHERE name = ?",
                (checksum, name)
            )

    def mark_removed(self, name: str):
        """Soft delete. Never hard delete from registry."""
        with self.pool.transaction() as pool:
            pool.execute(
                """
                UPDATE models
                SET status = 'removed'
                WHERE name = ?
                """,
                (name,)
            )
        logger.info(f"Model marked removed: {name}")

    def hard_delete(self, name: str):
        """
        Permanent deletion. Use only for cleanup.
        """
        with self.pool.transaction() as pool:
            pool.execute(
                "DELETE FROM models WHERE name = ? AND status = 'removed'",
                (name,)
            )
        logger.warning(f"Model hard deleted: {name}")

    def search(self, query: str) -> List[ModelRecord]:
        """Search models by name or family."""
        cursor = self.pool.execute(
            """
            SELECT * FROM models
            WHERE (name LIKE ? OR family LIKE ?)
                AND status != 'removed'
            ORDER BY use_count DESC
            """,
            (f"%{query}%", f"%{query}%")
        )
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def get_total_storage_bytes(self) -> int:
        """Total storage used by all ready models."""
        cursor = self.pool.execute(
            """
            SELECT COALESCE(SUM(file_size_bytes), 0) as total
            FROM models
            WHERE status = 'ready'
            """
        )
        row = cursor.fetchone()
        return row["total"]

    def get_least_recently_used(self, limit: int = 5) -> List[ModelRecord]:
        """Get LRU models for potential cleanup."""
        cursor = self.pool.execute(
            """
            SELECT * FROM models
            WHERE status = 'ready'
            ORDER BY last_used_at ASC NULLS FIRST, use_count ASC
            LIMIT ?
            """,
            (limit,)
        )
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def count(self) -> int:
        """Count of active models."""
        cursor = self.pool.execute(
            "SELECT COUNT(*) as c FROM models WHERE status != 'removed'"
        )
        return cursor.fetchone()["c"]

    def _row_to_record(self, row: sqlite3.Row) -> ModelRecord:
        """Convert database row to Pydantic model."""
        return ModelRecord(
            id=row["id"],
            name=row["name"],
            family=row["family"],
            size_label=row["size_label"],
            quant=QuantType(row["quant"]),
            file_path=row["file_path"],
            file_size_bytes=row["file_size_bytes"],
            checksum_sha256=row["checksum_sha256"],
            source=row["source"],
            repo_id=row["repo_id"],
            status=ModelStatus(row["status"]),
            engines_supported=row["engines_supported"],
            context_length=row["context_length"],
            hidden_size=row["hidden_size"],
            num_layers=row["num_layers"],
            ram_required_mb=row["ram_required_mb"],
            created_at=row["created_at"],
            last_used_at=row["last_used_at"],
            use_count=row["use_count"]
        )