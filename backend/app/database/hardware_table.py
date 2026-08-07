"""
Hardware profile storage.
Tracks what machine this platform is running on.
Used for mode recommendation and model selection.
"""

import sqlite3
import logging
from typing import Optional, List
from .connection import ConnectionPool
from app.schemas.db_schemas import HardwareProfile, EngineMode

logger = logging.getLogger("sovereign.db.hardware")


class HardwareTable:

    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def save_profile(self, profile: HardwareProfile) -> int:
        """Save or update hardware profile."""
        with self.pool.transaction() as pool:
            cursor = pool.execute(
                """
                INSERT INTO hardware_profiles (
                    cpu_name, cpu_cores, cpu_threads,
                    has_avx2, has_avx512,
                    total_ram_mb, available_ram_mb,
                    gpu_name, gpu_vram_mb,
                    disk_type, disk_read_speed_mbps,
                    disk_write_speed_mbps,
                    recommended_mode, max_model_size_label
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile.cpu_name, profile.cpu_cores,
                    profile.cpu_threads,
                    int(profile.has_avx2), int(profile.has_avx512),
                    profile.total_ram_mb, profile.available_ram_mb,
                    profile.gpu_name, profile.gpu_vram_mb,
                    profile.disk_type, profile.disk_read_speed_mbps,
                    profile.disk_write_speed_mbps,
                    profile.recommended_mode.value,
                    profile.max_model_size_label
                )
            )
            row_id = cursor.lastrowid
            logger.info(f"Hardware profile saved (id={row_id})")
            return row_id

    def get_latest(self) -> Optional[HardwareProfile]:
        """Get most recent hardware profile."""
        cursor = self.pool.execute(
            """
            SELECT * FROM hardware_profiles
            ORDER BY profiled_at DESC
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_profile(row)

    def get_by_id(self, profile_id: int) -> Optional[HardwareProfile]:
        """Get specific profile by ID."""
        cursor = self.pool.execute(
            "SELECT * FROM hardware_profiles WHERE id = ?",
            (profile_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_profile(row)

    def list_all(self) -> List[HardwareProfile]:
        """List all recorded profiles."""
        cursor = self.pool.execute(
            "SELECT * FROM hardware_profiles ORDER BY profiled_at DESC"
        )
        return [self._row_to_profile(row) for row in cursor.fetchall()]

    def _row_to_profile(self, row: sqlite3.Row) -> HardwareProfile:
        return HardwareProfile(
            id=row["id"],
            cpu_name=row["cpu_name"],
            cpu_cores=row["cpu_cores"],
            cpu_threads=row["cpu_threads"],
            has_avx2=bool(row["has_avx2"]),
            has_avx512=bool(row["has_avx512"]),
            total_ram_mb=row["total_ram_mb"],
            available_ram_mb=row["available_ram_mb"],
            gpu_name=row["gpu_name"],
            gpu_vram_mb=row["gpu_vram_mb"],
            disk_type=row["disk_type"],
            disk_read_speed_mbps=row["disk_read_speed_mbps"],
            disk_write_speed_mbps=row["disk_write_speed_mbps"],
            recommended_mode=EngineMode(row["recommended_mode"]),
            max_model_size_label=row["max_model_size_label"],
            profiled_at=row["profiled_at"]
        )