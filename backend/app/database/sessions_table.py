"""
Session tracking.
Every inference session is logged.
"""

import sqlite3
import logging
from typing import Optional, List
from .connection import ConnectionPool
from app.schemas.db_schemas import SessionRecord, EngineMode

logger = logging.getLogger("sovereign.db.sessions")


class SessionsTable:

    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def create(self, session: SessionRecord) -> int:
        """Create new session record."""
        with self.pool.transaction() as pool:
            cursor = pool.execute(
                """
                INSERT INTO sessions (
                    session_id, model_name, engine_mode,
                    status
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    session.session_id, session.model_name,
                    session.engine_mode.value, session.status
                )
            )
            return cursor.lastrowid

    def update_tokens(self, session_id: str,
                      prompt_tokens: int,
                      completion_tokens: int,
                      tokens_per_sec: float):
        """Update token counts for active session."""
        with self.pool.transaction() as pool:
            pool.execute(
                """
                UPDATE sessions
                SET prompt_tokens = prompt_tokens + ?,
                    completion_tokens = completion_tokens + ?,
                    total_tokens = prompt_tokens + completion_tokens + ? + ?,
                    avg_tokens_per_sec = ?
                WHERE session_id = ?
                """,
                (
                    prompt_tokens, completion_tokens,
                    prompt_tokens, completion_tokens,
                    tokens_per_sec, session_id
                )
            )

    def update_peak_ram(self, session_id: str, peak_ram_mb: float):
        """Update peak RAM if higher than current."""
        with self.pool.transaction() as pool:
            pool.execute(
                """
                UPDATE sessions
                SET peak_ram_mb = MAX(peak_ram_mb, ?)
                WHERE session_id = ?
                """,
                (peak_ram_mb, session_id)
            )

    def end_session(self, session_id: str, status: str = "completed"):
        """Mark session as ended."""
        with self.pool.transaction() as pool:
            pool.execute(
                """
                UPDATE sessions
                SET ended_at = datetime('now'),
                    status = ?
                WHERE session_id = ?
                """,
                (status, session_id)
            )
        logger.info(f"Session ended: {session_id} ({status})")

    def get(self, session_id: str) -> Optional[SessionRecord]:
        """Get session by ID."""
        cursor = self.pool.execute(
            "SELECT * FROM sessions WHERE session_id = ?",
            (session_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

    def list_recent(self, limit: int = 20) -> List[SessionRecord]:
        """List most recent sessions."""
        cursor = self.pool.execute(
            """
            SELECT * FROM sessions
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (limit,)
        )
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def list_by_model(self, model_name: str,
                      limit: int = 50) -> List[SessionRecord]:
        """List sessions for a specific model."""
        cursor = self.pool.execute(
            """
            SELECT * FROM sessions
            WHERE model_name = ?
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (model_name, limit)
        )
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def get_active_sessions(self) -> List[SessionRecord]:
        """Get all currently active sessions."""
        cursor = self.pool.execute(
            "SELECT * FROM sessions WHERE status = 'active'"
        )
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def get_total_tokens_generated(self) -> int:
        """Total tokens ever generated across all sessions."""
        cursor = self.pool.execute(
            "SELECT COALESCE(SUM(total_tokens), 0) as t FROM sessions"
        )
        return cursor.fetchone()["t"]

    def get_average_tps(self, model_name: Optional[str] = None) -> float:
        """Average tokens per second across sessions."""
        if model_name:
            cursor = self.pool.execute(
                """
                SELECT COALESCE(AVG(avg_tokens_per_sec), 0.0) as avg_tps
                FROM sessions
                WHERE model_name = ? AND avg_tokens_per_sec > 0
                """,
                (model_name,)
            )
        else:
            cursor = self.pool.execute(
                """
                SELECT COALESCE(AVG(avg_tokens_per_sec), 0.0) as avg_tps
                FROM sessions
                WHERE avg_tokens_per_sec > 0
                """
            )
        return cursor.fetchone()["avg_tps"]

    def cleanup_old(self, max_sessions: int = 1000):
        """Remove oldest sessions beyond limit."""
        with self.pool.transaction() as pool:
            pool.execute(
                """
                DELETE FROM sessions
                WHERE id NOT IN (
                    SELECT id FROM sessions
                    ORDER BY started_at DESC
                    LIMIT ?
                )
                """,
                (max_sessions,)
            )

    def mark_crashed_sessions(self):
        """
        Mark any 'active' sessions as crashed.
        Called on startup to clean up after unexpected shutdown.
        """
        with self.pool.transaction() as pool:
            cursor = pool.execute(
                """
                UPDATE sessions
                SET status = 'crashed',
                    ended_at = datetime('now')
                WHERE status = 'active'
                """
            )
            count = cursor.rowcount
            if count > 0:
                logger.warning(
                    f"Marked {count} orphaned sessions as crashed"
                )

    def _row_to_record(self, row: sqlite3.Row) -> SessionRecord:
        return SessionRecord(
            id=row["id"],
            session_id=row["session_id"],
            model_name=row["model_name"],
            engine_mode=EngineMode(row["engine_mode"]),
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            total_tokens=row["total_tokens"],
            prompt_tokens=row["prompt_tokens"],
            completion_tokens=row["completion_tokens"],
            avg_tokens_per_sec=row["avg_tokens_per_sec"],
            peak_ram_mb=row["peak_ram_mb"],
            status=row["status"]
        )