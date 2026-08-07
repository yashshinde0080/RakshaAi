"""
Audit log.
Every significant system event is recorded.
Security. Debugging. Compliance.
"""

import sqlite3
import json
import logging
from typing import Optional, List, Dict, Any
from .connection import ConnectionPool
from app.schemas.db_schemas import AuditRecord

logger = logging.getLogger("sovereign.db.audit")


class AuditTable:

    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def log(self, event_type: str, message: str,
            severity: str = "info",
            source: str = "",
            metadata: Optional[Dict[str, Any]] = None):
        """
        Log an audit event.
        Non-blocking. Best effort.
        """
        try:
            metadata_json = json.dumps(metadata) if metadata else None
            self.pool.execute(
                """
                INSERT INTO audit_log (
                    event_type, severity, source,
                    message, metadata_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (event_type, severity, source, message, metadata_json)
            )
            self.pool.commit()
        except Exception as e:
            # Audit logging should never crash the system
            logger.error(f"Audit log write failed: {e}")

    def log_model_load(self, model_name: str, mode: str):
        """Log model load event."""
        self.log(
            event_type="model_load",
            message=f"Model loaded: {model_name} in {mode} mode",
            source="engine",
            metadata={"model": model_name, "mode": mode}
        )

    def log_query(self, model_name: str, tokens: int, tps: float):
        """Log inference query."""
        self.log(
            event_type="query",
            message=f"Query completed: {tokens} tokens at {tps:.1f} TPS",
            source="inference",
            metadata={
                "model": model_name,
                "tokens": tokens,
                "tps": tps
            }
        )

    def log_download(self, model_name: str, source: str, size_bytes: int):
        """Log model download."""
        self.log(
            event_type="download",
            message=f"Downloaded {model_name} from {source}",
            source="model_manager",
            metadata={
                "model": model_name,
                "source": source,
                "size_bytes": size_bytes
            }
        )

    def log_error(self, source: str, message: str,
                  metadata: Optional[Dict] = None):
        """Log error event."""
        self.log(
            event_type="error",
            severity="error",
            source=source,
            message=message,
            metadata=metadata
        )

    def log_security(self, message: str,
                     severity: str = "warning",
                     metadata: Optional[Dict] = None):
        """Log security event."""
        self.log(
            event_type="security",
            severity=severity,
            source="security",
            message=message,
            metadata=metadata
        )

    def get_recent(self, limit: int = 100) -> List[AuditRecord]:
        """Get recent audit events."""
        cursor = self.pool.execute(
            """
            SELECT * FROM audit_log
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,)
        )
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def get_by_type(self, event_type: str,
                    limit: int = 100) -> List[AuditRecord]:
        """Get events by type."""
        cursor = self.pool.execute(
            """
            SELECT * FROM audit_log
            WHERE event_type = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (event_type, limit)
        )
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def get_by_severity(self, severity: str,
                        limit: int = 100) -> List[AuditRecord]:
        """Get events by severity."""
        cursor = self.pool.execute(
            """
            SELECT * FROM audit_log
            WHERE severity = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (severity, limit)
        )
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def get_errors(self, limit: int = 50) -> List[AuditRecord]:
        """Get error and critical events."""
        cursor = self.pool.execute(
            """
            SELECT * FROM audit_log
            WHERE severity IN ('error', 'critical')
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,)
        )
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def count_by_type(self) -> Dict[str, int]:
        """Count events grouped by type."""
        cursor = self.pool.execute(
            """
            SELECT event_type, COUNT(*) as c
            FROM audit_log
            GROUP BY event_type
            """
        )
        return {row["event_type"]: row["c"] for row in cursor.fetchall()}

    def cleanup(self, keep_days: int = 30):
        """Remove audit entries older than N days."""
        with self.pool.transaction() as pool:
            cursor = pool.execute(
                """
                DELETE FROM audit_log
                WHERE timestamp < datetime('now', ? || ' days')
                """,
                (f"-{keep_days}",)
            )
            count = cursor.rowcount
            if count > 0:
                logger.info(f"Cleaned up {count} old audit entries")

    def _row_to_record(self, row: sqlite3.Row) -> AuditRecord:
        return AuditRecord(
            id=row["id"],
            timestamp=row["timestamp"],
            event_type=row["event_type"],
            severity=row["severity"],
            source=row["source"],
            message=row["message"],
            metadata_json=row["metadata_json"]
        )