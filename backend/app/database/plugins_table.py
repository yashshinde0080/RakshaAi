"""
Plugin registry.
Track installed plugins, their permissions, and activation status.
"""

import sqlite3
import logging
from typing import Optional, List
from .connection import ConnectionPool
from app.schemas.db_schemas import PluginRecord

logger = logging.getLogger("sovereign.db.plugins")


class PluginsTable:

    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def install(self, plugin: PluginRecord) -> int:
        """Register a new plugin."""
        with self.pool.transaction() as pool:
            cursor = pool.execute(
                """
                INSERT INTO plugins (
                    plugin_id, name, version, author,
                    description, entry_point, is_active,
                    permissions, signature
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    plugin.plugin_id, plugin.name, plugin.version,
                    plugin.author, plugin.description,
                    plugin.entry_point, int(plugin.is_active),
                    plugin.permissions, plugin.signature
                )
            )
            return cursor.lastrowid

    def activate(self, plugin_id: str):
        """Activate a plugin."""
        with self.pool.transaction() as pool:
            pool.execute(
                "UPDATE plugins SET is_active = 1 WHERE plugin_id = ?",
                (plugin_id,)
            )

    def deactivate(self, plugin_id: str):
        """Deactivate a plugin."""
        with self.pool.transaction() as pool:
            pool.execute(
                "UPDATE plugins SET is_active = 0 WHERE plugin_id = ?",
                (plugin_id,)
            )

    def get(self, plugin_id: str) -> Optional[PluginRecord]:
        """Get plugin by ID."""
        cursor = self.pool.execute(
            "SELECT * FROM plugins WHERE plugin_id = ?",
            (plugin_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

    def list_all(self) -> List[PluginRecord]:
        """List all plugins."""
        cursor = self.pool.execute(
            "SELECT * FROM plugins ORDER BY name"
        )
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def list_active(self) -> List[PluginRecord]:
        """List only active plugins."""
        cursor = self.pool.execute(
            "SELECT * FROM plugins WHERE is_active = 1 ORDER BY name"
        )
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def uninstall(self, plugin_id: str):
        """Remove plugin from registry."""
        with self.pool.transaction() as pool:
            pool.execute(
                "DELETE FROM plugins WHERE plugin_id = ?",
                (plugin_id,)
            )
        logger.info(f"Plugin uninstalled: {plugin_id}")

    def _row_to_record(self, row: sqlite3.Row) -> PluginRecord:
        return PluginRecord(
            id=row["id"],
            plugin_id=row["plugin_id"],
            name=row["name"],
            version=row["version"],
            author=row["author"],
            description=row["description"],
            entry_point=row["entry_point"],
            is_active=bool(row["is_active"]),
            permissions=row["permissions"],
            signature=row["signature"],
            installed_at=row["installed_at"]
        )