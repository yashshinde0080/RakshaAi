"""Audit Logging"""
from datetime import datetime
from typing import Optional
import json

from app.database.connection import get_database


class AuditLogger:
    """Log security-relevant events"""
    
    SEVERITY_INFO = "info"
    SEVERITY_WARNING = "warning"
    SEVERITY_ERROR = "error"
    SEVERITY_CRITICAL = "critical"
    
    async def log(
        self,
        event_type: str,
        details: Optional[dict] = None,
        severity: str = SEVERITY_INFO
    ):
        """Log audit event"""
        db = await get_database()
        
        await db.execute(
            """
            INSERT INTO audit_log (timestamp, event_type, details, severity)
            VALUES (?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(),
                event_type,
                json.dumps(details) if details else None,
                severity
            )
        )
        await db.commit()
    
    async def get_logs(
        self,
        limit: int = 100,
        severity: Optional[str] = None
    ) -> list:
        """Get audit logs"""
        db = await get_database()
        
        if severity:
            cursor = await db.execute(
                """
                SELECT * FROM audit_log 
                WHERE severity = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (severity, limit)
            )
        else:
            cursor = await db.execute(
                """
                SELECT * FROM audit_log 
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,)
            )
        
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


# Global instance
audit_logger = AuditLogger()