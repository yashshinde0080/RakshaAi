"""Runnable checks for the ``chat`` command's server auto-start wiring.

Covers ``_server_healthy`` (probes /health), ``_ensure_server`` (skip start
when the server is already up; start + wait for healthy when it's down; refuse
auto-start under a SOVEREIGN_API_BASE override) and the ``_wait_for_server``
grace window (spawned process died, but the port owner becomes healthy).
``_start_server`` itself is stubbed so the test never boots the real backend.
"""
import asyncio
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

import app.cli.main as cli


class _HealthyHandler(BaseHTTPRequestHandler):
    """Serves /health like the real backend's root route."""

    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == "/health":
            body = b'{"status":"healthy"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _serve_forever(server):
    threading.Thread(target=server.serve_forever, daemon=True).start()


class _FakeProc:
    """Stand-in for subprocess.Popen — only poll() is used by _wait_for_server."""

    def poll(self):
        return None  # still running


class _DeadProc:
    """A spawned server that already exited (e.g. port was taken)."""

    def poll(self):
        return -1


@pytest.fixture
def healthy_server():
    server = HTTPServer(("127.0.0.1", 0), _HealthyHandler)
    _serve_forever(server)
    yield server
    server.shutdown()
    server.server_close()


def test_server_healthy_true_when_up(monkeypatch, healthy_server):
    port = healthy_server.server_address[1]
    monkeypatch.setattr(cli, "SERVER_ORIGIN", f"http://127.0.0.1:{port}")
    assert asyncio.run(cli._server_healthy()) is True


def test_server_healthy_false_when_down(monkeypatch):
    port = _free_port()  # nothing is listening there
    monkeypatch.setattr(cli, "SERVER_ORIGIN", f"http://127.0.0.1:{port}")
    assert asyncio.run(cli._server_healthy()) is False


def test_ensure_server_skips_start_when_already_up(monkeypatch, healthy_server):
    port = healthy_server.server_address[1]
    monkeypatch.setattr(cli, "SERVER_ORIGIN", f"http://127.0.0.1:{port}")
    calls = []
    monkeypatch.setattr(cli, "_start_server", lambda: calls.append("started"))
    healthy, started = asyncio.run(cli._ensure_server())
    assert healthy is True
    assert started is False
    assert calls == []


def test_ensure_server_starts_and_waits_when_down(monkeypatch):
    port = _free_port()
    monkeypatch.setattr(cli, "SERVER_ORIGIN", f"http://127.0.0.1:{port}")
    started = []
    holder = {}

    def _fake_start_server():
        started.append(True)
        holder["server"] = HTTPServer(("127.0.0.1", port), _HealthyHandler)
        _serve_forever(holder["server"])
        return _FakeProc()

    monkeypatch.setattr(cli, "_start_server", _fake_start_server)
    healthy, did_start = asyncio.run(cli._ensure_server())
    assert healthy is True
    assert did_start is True
    assert started == [True]
    holder["server"].shutdown()
    holder["server"].server_close()


def test_ensure_server_env_override_refuses_auto_start(monkeypatch):
    port = _free_port()
    monkeypatch.setattr(cli, "SERVER_ORIGIN", f"http://127.0.0.1:{port}")
    monkeypatch.setenv("SOVEREIGN_API_BASE", f"http://127.0.0.1:{port}")
    calls = []
    monkeypatch.setattr(cli, "_start_server", lambda: calls.append("started"))
    healthy, started = asyncio.run(cli._ensure_server())
    assert healthy is False
    assert started is False
    assert calls == []


def test_wait_for_server_grace_when_spawned_proc_dies(monkeypatch):
    """A dead spawned proc must not fail instantly: the port owner (a server
    that was already booting) becomes healthy within the grace window."""
    port = _free_port()
    monkeypatch.setattr(cli, "SERVER_ORIGIN", f"http://127.0.0.1:{port}")

    holder = {}

    def _late_server():
        time.sleep(2)  # the other server finishes booting ~2s later
        holder["server"] = HTTPServer(("127.0.0.1", port), _HealthyHandler)
        holder["server"].serve_forever()

    threading.Thread(target=_late_server, daemon=True).start()
    assert asyncio.run(cli._wait_for_server(_DeadProc(), timeout=10)) is True
    holder["server"].shutdown()
    holder["server"].server_close()
