"""
Database Manager.
Single entry point for all database operations.
Initialize once. Use everywhere.
"""

import os
import logging
import toml
from typing import Optional

from .connection import ConnectionPool
from .migrations import MigrationRunner
from .models_table import ModelsTable
from .sessions_table import SessionsTable
from .hardware_table import HardwareTable
from .documents_table import DocumentsTable
from .plugins_table import PluginsTable
from .audit_table import AuditTable

logger = logging.getLogger("sovereign.db")


class DatabaseManager:
    """
    Central database manager.

    Usage:
        db = DatabaseManager()  # -> workspace/database/sovereign.db (shared with model registry)
        db.initialize()

        db.models.insert(...)
        db.sessions.create(...)
        db.audit.log(...)

        db.shutdown()
    """

    def __init__(self, config_path: str = "config/storage.toml"):
        # Load config
        if os.path.exists(config_path):
            config = toml.load(config_path)
            db_config = config.get("database", {})
        else:
            db_config = {}

        from app.config import settings
        # One DB file for the whole app: <project>/workspace/database/sovereign.db
        self.db_path = str(db_config.get("path", settings.database_path))
        journal_mode = db_config.get("journal_mode", "WAL")
        busy_timeout = db_config.get("busy_timeout", 5000)
        cache_size = db_config.get("cache_size", -64000)

        # Create connection pool
        self._pool = ConnectionPool(
            db_path=self.db_path,
            journal_mode=journal_mode,
            busy_timeout=busy_timeout,
            cache_size=cache_size
        )

        # Table interfaces
        self.models = ModelsTable(self._pool)
        self.sessions = SessionsTable(self._pool)
        self.hardware = HardwareTable(self._pool)
        self.documents = DocumentsTable(self._pool)
        self.plugins = PluginsTable(self._pool)
        self.audit = AuditTable(self._pool)

        # Migration runner
        self._migrator = MigrationRunner(self._pool)

        self._initialized = False

    def initialize(self):
        """
        Initialize database.
        Run migrations.
        Clean up orphaned sessions.
        Verify integrity.
        """
        logger.info(f"Initializing database: {self.db_path}")

        # Run migrations
        self._migrator.run_all()

        # Verify integrity
        if not self._migrator.verify_integrity():
            logger.error("DATABASE INTEGRITY CHECK FAILED")
            raise RuntimeError("Database corruption detected")

        # Clean up orphaned sessions from crash
        self.sessions.mark_crashed_sessions()

        self._initialized = True
        self.audit.log(
            event_type="system",
            message="Database initialized",
            source="database_manager"
        )
        logger.info("Database initialized successfully")

    def get_stats(self) -> dict:
        """Get database statistics."""
        return {
            "models_count": self.models.count(),
            "total_storage_bytes": self.models.get_total_storage_bytes(),
            "documents_count": self.documents.count(),
            "total_chunks": self.documents.get_total_chunks(),
            "total_tokens_generated": self.sessions.get_total_tokens_generated(),
            "average_tps": self.sessions.get_average_tps(),
            "db_path": self.db_path,
            "db_size_bytes": os.path.getsize(self.db_path)
                if os.path.exists(self.db_path) else 0
        }

    def vacuum(self):
        """Reclaim space. Run periodically."""
        self._pool.execute("VACUUM")
        self._pool.commit()
        logger.info("Database vacuumed")

    def checkpoint(self):
        """Force WAL checkpoint."""
        self._pool.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        self._pool.commit()

    def backup(self, backup_path: str):
        """Create database backup."""
        import shutil
        self.checkpoint()
        shutil.copy2(self.db_path, backup_path)
        logger.info(f"Database backed up to: {backup_path}")

    def shutdown(self):
        """Clean shutdown."""
        if self._initialized:
            self.audit.log(
                event_type="system",
                message="Database shutting down",
                source="database_manager"
            )
        self.checkpoint()
        self._pool.close_all()
        logger.info("Database connection closed")

    @property
    def pool(self) -> ConnectionPool:
        return self._pool