"""
SQLite connection management.
WAL mode. Busy timeout. Foreign keys enforced.
No amateur YOLO connections.
"""

import sqlite3
import os
import threading
from typing import Optional


class ConnectionPool:
    """
    Thread-safe SQLite connection pool.
    Each thread gets its own connection.
    WAL mode for concurrent reads.
    """

    def __init__(self, db_path: str, journal_mode: str = "WAL",
                 busy_timeout: int = 5000, cache_size: int = -64000):
        self.db_path = db_path
        self.journal_mode = journal_mode
        self.busy_timeout = busy_timeout
        self.cache_size = cache_size
        self._local = threading.local()
        self._lock = threading.Lock()

        # Ensure directory exists
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """
        Get thread-local connection.
        Creates one if not exists for current thread.
        """
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = self._create_connection()
        return self._local.connection

    def _create_connection(self) -> sqlite3.Connection:
        """
        Create properly configured SQLite connection.
        """
        conn = sqlite3.connect(
            self.db_path,
            timeout=self.busy_timeout / 1000.0,
            check_same_thread=False
        )

        # Row factory for dict-like access
        conn.row_factory = sqlite3.Row

        # Enforce foreign keys
        conn.execute("PRAGMA foreign_keys = ON")

        # WAL mode for concurrent reads
        conn.execute(f"PRAGMA journal_mode = {self.journal_mode}")

        # Cache size (negative = KB)
        conn.execute(f"PRAGMA cache_size = {self.cache_size}")

        # Synchronous mode - NORMAL for balance
        conn.execute("PRAGMA synchronous = NORMAL")

        # Temp store in memory
        conn.execute("PRAGMA temp_store = MEMORY")

        # Memory-mapped I/O (256MB)
        conn.execute("PRAGMA mmap_size = 268435456")

        return conn

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute with automatic connection handling."""
        conn = self.get_connection()
        return conn.execute(sql, params)

    def executemany(self, sql: str, params_list: list) -> sqlite3.Cursor:
        """Execute many with automatic connection handling."""
        conn = self.get_connection()
        return conn.executemany(sql, params_list)

    def commit(self):
        """Commit current transaction."""
        conn = self.get_connection()
        conn.commit()

    def rollback(self):
        """Rollback current transaction."""
        conn = self.get_connection()
        conn.rollback()

    def close(self):
        """Close thread-local connection."""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None

    def close_all(self):
        """Close connection for current thread."""
        self.close()

    def transaction(self):
        """Context manager for transactions."""
        return TransactionContext(self)


class TransactionContext:
    """
    Atomic transaction context manager.
    Commits on success. Rolls back on failure.
    No half-written state.
    """

    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def __enter__(self):
        self.pool.execute("BEGIN IMMEDIATE")
        return self.pool

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.pool.commit()
        else:
            self.pool.rollback()
        return False  # Don't suppress exceptions