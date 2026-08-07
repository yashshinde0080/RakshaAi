import uvicorn
import sqlite3
import json
import os
from pathlib import Path

def get_server_config():
    """Read server config directly from the settings DB if it exists"""
    db_path = str(Path(__file__).parent.parent / "workspace" / "database" / "sovereign_settings.db")
    
    # Defaults
    host = "0.0.0.0"
    port = 8000
    
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT data FROM settings WHERE section = ?", ("security",))
            row = cursor.fetchone()
            if row:
                security = json.loads(row["data"])
                port = security.get("api_port", 8000)
                if security.get("bind_localhost_only", True):
                    host = "127.0.0.1"
                else:
                    host = "0.0.0.0"
            conn.close()
        except Exception as e:
            print(f"Warning: Could not read settings DB for server config: {e}")
            
    return host, port

if __name__ == "__main__":
    host, port = get_server_config()
    print(f"Launching SovereignAI Server on {host}:{port}")
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True
    )
