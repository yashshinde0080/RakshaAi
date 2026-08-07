import sqlite3
import json
import os
from pathlib import Path
from typing import Optional
from .schemas import FullSettings, AgentConfig
from .defaults import DEFAULT_AGENTS
from app.config import settings


class SettingsDatabase:
    def __init__(self, db_path: Optional[str] = None):
        # Project-relative (portable USB): <project>/workspace/database/sovereign_settings.db
        self.db_path = db_path or str(settings.workspace_dir / "database" / "sovereign_settings.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self):
        conn = self._get_connection()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS settings (
                    section TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS agents (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    system_instruction TEXT DEFAULT '',
                    is_active INTEGER DEFAULT 0,
                    icon TEXT DEFAULT 'bot',
                    temperature REAL DEFAULT 0.7,
                    max_tokens INTEGER DEFAULT 2048,
                    enabled INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    section TEXT NOT NULL,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Ensure all sections exist
            defaults = FullSettings()
            for section in ["general", "personalization", "data_controls", "security", "parental_controls", "project"]:
                cursor = conn.execute("SELECT COUNT(*) as cnt FROM settings WHERE section = ?", (section,))
                if cursor.fetchone()["cnt"] == 0:
                    data = getattr(defaults, section).model_dump_json()
                    conn.execute(
                        "INSERT INTO settings (section, data) VALUES (?, ?)",
                        (section, data)
                    )



            # Insert default agents if not exist
            cursor = conn.execute("SELECT COUNT(*) as cnt FROM agents")
            count = cursor.fetchone()["cnt"]
            if count == 0:
                for agent in DEFAULT_AGENTS:
                    conn.execute(
                        """INSERT INTO agents (id, name, role, description, system_instruction, 
                           is_active, icon, temperature, max_tokens, enabled) 
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            agent.id, agent.name, agent.role.value,
                            agent.description, agent.system_instruction,
                            int(agent.is_active), agent.icon,
                            agent.temperature, agent.max_tokens,
                            int(agent.enabled)
                        )
                    )

            conn.commit()
        finally:
            conn.close()

    # ── Settings CRUD ──

    def get_section(self, section: str) -> Optional[dict]:
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT data FROM settings WHERE section = ?", (section,)
            )
            row = cursor.fetchone()
            if row:
                return json.loads(row["data"])
            return None
        finally:
            conn.close()

    def update_section(self, section: str, data: dict) -> bool:
        conn = self._get_connection()
        try:
            json_data = json.dumps(data)
            conn.execute(
                """INSERT INTO settings (section, data, updated_at) 
                   VALUES (?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(section) 
                   DO UPDATE SET data = excluded.data, updated_at = CURRENT_TIMESTAMP""",
                (section, json_data)
            )
            conn.execute(
                "INSERT INTO audit_log (action, section, details) VALUES (?, ?, ?)",
                ("update", section, json_data)
            )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_all_settings(self) -> dict:
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT section, data FROM settings")
            result = {}
            for row in cursor.fetchall():
                result[row["section"]] = json.loads(row["data"])
            return result
        finally:
            conn.close()

    def reset_section(self, section: str) -> bool:
        defaults = FullSettings()
        default_data = getattr(defaults, section, None)
        if default_data is None:
            return False
        return self.update_section(section, default_data.model_dump())

    def reset_all(self) -> bool:
        conn = self._get_connection()
        try:
            defaults = FullSettings()
            for section in ["general", "personalization", "data_controls", "security", "parental_controls", "project"]:
                data = getattr(defaults, section).model_dump_json()
                conn.execute(
                    """INSERT INTO settings (section, data, updated_at) 
                       VALUES (?, ?, CURRENT_TIMESTAMP)
                       ON CONFLICT(section) 
                       DO UPDATE SET data = excluded.data, updated_at = CURRENT_TIMESTAMP""",
                    (section, data)
                )


            # Reset agents
            conn.execute("DELETE FROM agents")
            for agent in DEFAULT_AGENTS:
                conn.execute(
                    """INSERT INTO agents (id, name, role, description, system_instruction, 
                       is_active, icon, temperature, max_tokens, enabled) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        agent.id, agent.name, agent.role.value,
                        agent.description, agent.system_instruction,
                        int(agent.is_active), agent.icon,
                        agent.temperature, agent.max_tokens,
                        int(agent.enabled)
                    )
                )

            conn.execute(
                "INSERT INTO audit_log (action, section, details) VALUES (?, ?, ?)",
                ("reset_all", "all", "Full settings reset to defaults")
            )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    # ── Agents CRUD ──

    def get_all_agents(self) -> list[dict]:
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT * FROM agents ORDER BY name")
            agents = []
            for row in cursor.fetchall():
                agents.append({
                    "id": row["id"],
                    "name": row["name"],
                    "role": row["role"],
                    "description": row["description"],
                    "system_instruction": row["system_instruction"],
                    "is_active": bool(row["is_active"]),
                    "icon": row["icon"],
                    "temperature": row["temperature"],
                    "max_tokens": row["max_tokens"],
                    "enabled": bool(row["enabled"]),
                })
            return agents
        finally:
            conn.close()

    def get_agent(self, agent_id: str) -> Optional[dict]:
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,))
            row = cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "name": row["name"],
                    "role": row["role"],
                    "description": row["description"],
                    "system_instruction": row["system_instruction"],
                    "is_active": bool(row["is_active"]),
                    "icon": row["icon"],
                    "temperature": row["temperature"],
                    "max_tokens": row["max_tokens"],
                    "enabled": bool(row["enabled"]),
                }
            return None
        finally:
            conn.close()

    def create_agent(self, agent: AgentConfig) -> bool:
        conn = self._get_connection()
        try:
            conn.execute(
                """INSERT INTO agents (id, name, role, description, system_instruction,
                   is_active, icon, temperature, max_tokens, enabled)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    agent.id, agent.name, agent.role.value,
                    agent.description, agent.system_instruction,
                    int(agent.is_active), agent.icon,
                    agent.temperature, agent.max_tokens,
                    int(agent.enabled)
                )
            )
            conn.execute(
                "INSERT INTO audit_log (action, section, details) VALUES (?, ?, ?)",
                ("create_agent", "agents", json.dumps({"agent_id": agent.id, "name": agent.name}))
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def update_agent(self, agent_id: str, agent: AgentConfig) -> bool:
        conn = self._get_connection()
        try:
            conn.execute(
                """UPDATE agents SET name=?, role=?, description=?, system_instruction=?,
                   is_active=?, icon=?, temperature=?, max_tokens=?, enabled=?,
                   updated_at=CURRENT_TIMESTAMP
                   WHERE id=?""",
                (
                    agent.name, agent.role.value,
                    agent.description, agent.system_instruction,
                    int(agent.is_active), agent.icon,
                    agent.temperature, agent.max_tokens,
                    int(agent.enabled), agent_id
                )
            )
            conn.execute(
                "INSERT INTO audit_log (action, section, details) VALUES (?, ?, ?)",
                ("update_agent", "agents", json.dumps({"agent_id": agent_id}))
            )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    def delete_agent(self, agent_id: str) -> bool:
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
            conn.execute(
                "INSERT INTO audit_log (action, section, details) VALUES (?, ?, ?)",
                ("delete_agent", "agents", json.dumps({"agent_id": agent_id}))
            )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    def set_active_agent(self, agent_id: str) -> bool:
        conn = self._get_connection()
        try:
            conn.execute("UPDATE agents SET is_active = 0")
            conn.execute("UPDATE agents SET is_active = 1 WHERE id = ?", (agent_id,))
            conn.execute(
                "INSERT INTO audit_log (action, section, details) VALUES (?, ?, ?)",
                ("activate_agent", "agents", json.dumps({"agent_id": agent_id}))
            )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    def deactivate_all_agents(self) -> bool:
        conn = self._get_connection()
        try:
            conn.execute("UPDATE agents SET is_active = 0")
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_active_agent(self) -> Optional[dict]:
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT * FROM agents WHERE is_active = 1 LIMIT 1")
            row = cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "name": row["name"],
                    "role": row["role"],
                    "description": row["description"],
                    "system_instruction": row["system_instruction"],
                    "is_active": True,
                    "icon": row["icon"],
                    "temperature": row["temperature"],
                    "max_tokens": row["max_tokens"],
                    "enabled": bool(row["enabled"]),
                }
            return None
        finally:
            conn.close()

    # ── Audit ──

    def get_audit_log(self, limit: int = 100) -> list[dict]:
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()