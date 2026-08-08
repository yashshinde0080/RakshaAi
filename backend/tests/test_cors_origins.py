"""CORS regression: every renderer origin must pass the configured regex.

Electron loads the frontend from app://- and the Expo app from exp://…; if the
CORS regex misses them, every fetch from those clients is blocked and the app
looks "not connected to backend". Web dev (http://localhost) must keep working.
Reads the live middleware config so a regex edit without a test update fails.
"""
import re

from app.main import app
from fastapi.middleware.cors import CORSMiddleware

RENDERER_ORIGINS = (
    "app://-",                       # Electron shell
    "http://localhost:3000",         # web dev server
    "exp://192.168.1.5:8081",        # Expo app on LAN
)


def test_cors_origin_regex_covers_all_renderer_origins():
    mw = next(m for m in app.user_middleware if m.cls is CORSMiddleware)
    pattern = re.compile(mw.kwargs["allow_origin_regex"])
    for origin in RENDERER_ORIGINS:
        assert pattern.match(origin), f"{origin} not allowed by CORS regex"
