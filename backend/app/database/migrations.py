"""
Schema migrations.
Version tracked. Idempotent. No manual SQL files.
"""

import sqlite3
import logging
from .connection import ConnectionPool

logger = logging.getLogger("sovereign.db.migrations")


MIGRATIONS = [
    # Version 1: Core tables
    {
        "version": 1,
        "description": "Create core tables",
        "sql": [
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT DEFAULT (datetime('now')),
                description TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                family TEXT NOT NULL,
                size_label TEXT NOT NULL,
                quant TEXT NOT NULL,
                file_path TEXT NOT NULL UNIQUE,
                file_size_bytes INTEGER NOT NULL DEFAULT 0,
                checksum_sha256 TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'local',
                repo_id TEXT,
                status TEXT NOT NULL DEFAULT 'ready',
                engines_supported TEXT NOT NULL DEFAULT 'fullram,layerstream',
                context_length INTEGER DEFAULT 4096,
                hidden_size INTEGER DEFAULT 4096,
                num_layers INTEGER DEFAULT 32,
                ram_required_mb INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                last_used_at TEXT,
                use_count INTEGER DEFAULT 0
            )
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_models_name_quant
            ON models(name, quant)
            """,
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL UNIQUE,
                model_name TEXT NOT NULL,
                engine_mode TEXT NOT NULL,
                started_at TEXT DEFAULT (datetime('now')),
                ended_at TEXT,
                total_tokens INTEGER DEFAULT 0,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                avg_tokens_per_sec REAL DEFAULT 0.0,
                peak_ram_mb REAL DEFAULT 0.0,
                status TEXT DEFAULT 'active',
                FOREIGN KEY (model_name) REFERENCES models(name)
                    ON DELETE SET NULL
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_sessions_model
            ON sessions(model_name)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_sessions_status
            ON sessions(status)
            """,
            """
            CREATE TABLE IF NOT EXISTS hardware_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cpu_name TEXT DEFAULT '',
                cpu_cores INTEGER DEFAULT 0,
                cpu_threads INTEGER DEFAULT 0,
                has_avx2 INTEGER DEFAULT 0,
                has_avx512 INTEGER DEFAULT 0,
                total_ram_mb INTEGER DEFAULT 0,
                available_ram_mb INTEGER DEFAULT 0,
                gpu_name TEXT,
                gpu_vram_mb INTEGER DEFAULT 0,
                disk_type TEXT DEFAULT 'unknown',
                disk_read_speed_mbps REAL DEFAULT 0.0,
                disk_write_speed_mbps REAL DEFAULT 0.0,
                recommended_mode TEXT DEFAULT 'auto',
                max_model_size_label TEXT DEFAULT '',
                profiled_at TEXT DEFAULT (datetime('now'))
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL UNIQUE,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size_bytes INTEGER DEFAULT 0,
                mime_type TEXT DEFAULT 'application/pdf',
                total_chunks INTEGER DEFAULT 0,
                total_embeddings INTEGER DEFAULT 0,
                checksum_sha256 TEXT DEFAULT '',
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now')),
                processed_at TEXT
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_documents_status
            ON documents(status)
            """,
        ]
    },
    # Version 2: Plugins and Audit
    {
        "version": 2,
        "description": "Add plugins and audit tables",
        "sql": [
            """
            CREATE TABLE IF NOT EXISTS plugins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plugin_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                version TEXT NOT NULL,
                author TEXT DEFAULT '',
                description TEXT DEFAULT '',
                entry_point TEXT NOT NULL,
                is_active INTEGER DEFAULT 0,
                permissions TEXT DEFAULT '',
                signature TEXT,
                installed_at TEXT DEFAULT (datetime('now'))
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT (datetime('now')),
                event_type TEXT NOT NULL,
                severity TEXT DEFAULT 'info',
                source TEXT DEFAULT '',
                message TEXT DEFAULT '',
                metadata_json TEXT
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_audit_type
            ON audit_log(event_type)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_audit_severity
            ON audit_log(severity)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp
            ON audit_log(timestamp)
            """,
        ]
    },
    # Version 3: Benchmark results
    {
        "version": 3,
        "description": "Add benchmark results table",
        "sql": [
            """
            CREATE TABLE IF NOT EXISTS benchmark_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT NOT NULL,
                engine_mode TEXT NOT NULL,
                tokens_per_sec REAL DEFAULT 0.0,
                first_token_latency_ms REAL DEFAULT 0.0,
                peak_ram_mb REAL DEFAULT 0.0,
                avg_ram_mb REAL DEFAULT 0.0,
                disk_io_mbps REAL DEFAULT 0.0,
                total_tokens INTEGER DEFAULT 0,
                duration_sec REAL DEFAULT 0.0,
                hardware_profile_id INTEGER,
                run_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (hardware_profile_id)
                    REFERENCES hardware_profiles(id)
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_benchmark_model
            ON benchmark_results(model_name)
            """,
        ]
    },
]


class MigrationRunner:
    """
    Runs migrations in order.
    Tracks applied versions.
    Never re-runs a migration.
    """

    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def get_current_version(self) -> int:
        """Get the highest applied migration version."""
        try:
            cursor = self.pool.execute(
                "SELECT MAX(version) as v FROM schema_version"
            )
            row = cursor.fetchone()
            if row and row["v"] is not None:
                return row["v"]
            return 0
        except sqlite3.OperationalError:
            # Table doesn't exist yet
            return 0

    def run_all(self):
        """
        Apply all pending migrations.
        Atomic per migration.
        """
        current = self.get_current_version()
        applied_count = 0

        for migration in MIGRATIONS:
            version = migration["version"]
            if version <= current:
                continue

            description = migration["description"]
            logger.info(
                f"Applying migration v{version}: {description}"
            )

            try:
                with self.pool.transaction() as pool:
                    for sql in migration["sql"]:
                        pool.execute(sql)

                    pool.execute(
                        "INSERT INTO schema_version (version, description) "
                        "VALUES (?, ?)",
                        (version, description)
                    )

                applied_count += 1
                logger.info(f"Migration v{version} applied successfully")

            except Exception as e:
                logger.error(
                    f"Migration v{version} FAILED: {e}"
                )
                raise

        if applied_count == 0:
            logger.info("Database schema is up to date")
        else:
            logger.info(f"Applied {applied_count} migration(s)")

    def verify_integrity(self) -> bool:
        """Verify database integrity."""
        try:
            cursor = self.pool.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            return result[0] == "ok"
        except Exception:
            return False