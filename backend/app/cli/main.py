#!/usr/bin/env python3
"""SovereignAI CLI Entry Point"""
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich import box
import httpx
import asyncio
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

from . import __version__

# Windows pipes default to cp1252, which crashes on unicode glyphs (✓, ·, box chars).
# Force UTF-8 output so the rich UI renders in pipes, CI logs and modern terminals.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

app = typer.Typer(
    name="sovereign",
    help=(
        "SovereignAI Edge - Portable Offline AI Platform\n"
        "Server URL: settings DB by default, override with SOVEREIGN_API_BASE env"
    ),
    add_completion=False
)

console = Console()


def _api_base() -> str:
    """Server origin: SOVEREIGN_API_BASE env wins, else the port from the settings DB."""
    env = os.environ.get("SOVEREIGN_API_BASE")
    if env:
        return env.rstrip("/") + "/v1"
    port = 8000
    db = Path(__file__).resolve().parents[3] / "workspace" / "database" / "sovereign_settings.db"
    if db.exists():
        try:
            conn = sqlite3.connect(str(db))
            row = conn.execute(
                "SELECT data FROM settings WHERE section = ?", ("security",)
            ).fetchone()
            conn.close()
            if row:
                port = json.loads(row[0]).get("api_port", 8000)
        except Exception:
            pass
    return f"http://127.0.0.1:{port}/v1"


API_BASE = _api_base()
SERVER_ORIGIN = API_BASE[: -len("/v1")]


def _sse_delta(line: str) -> tuple:
    """Parse one SSE data payload -> (content, reasoning). Empty when absent."""
    try:
        delta = json.loads(line)["choices"][0]["delta"]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        return "", ""
    return delta.get("content") or "", delta.get("reasoning") or ""


def _chat_banner(model: str, mode: str, ram: float | None = None) -> Panel:
    """Header panel for the chat TUI (model, mode, optional RAM)."""
    ram_txt = f"  [dim]RAM {ram:.1f} GB[/dim]" if ram is not None else ""
    return Panel.fit(
        f"[bold green]✓[/bold green] [bold]SovereignAI Edge[/bold]  "
        f"[cyan]{model}[/cyan] · [magenta]{mode}[/magenta]{ram_txt}",
        border_style="green", box=box.ROUNDED
    )


@app.command()
def version():
    """Show version information"""
    console.print(Panel.fit(
        f"[bold blue]SovereignAI Edge[/bold blue] v{__version__}\n"
        "Portable Offline AI Platform",
        title="Version", border_style="blue", box=box.ROUNDED
    ))


@app.command()
def help():
    """Show the full command reference"""
    table = Table(title="SovereignAI Edge — Commands", box=box.ROUNDED)
    table.add_column("Command", style="cyan")
    table.add_column("What it does")
    table.add_column("Example")

    for cmd, desc, example in [
        ("version", "Show version", "sovereign version"),
        ("system", "Hardware profile, server status, model recommendations", "sovereign system"),
        ("list", "List installed models", "sovereign list"),
        ("pull <model>", "Download a model (-q/--quant)", "sovereign pull llama3:8b"),
        ("run <model>", "Load a model + chat TUI (server must be running)", "sovereign run llama3:8b"),
        ("chat <model>", "Auto-start the server if needed, then chat", "sovereign chat llama3:8b"),
        ("benchmark", "Run inference benchmark (-n iters, -t tokens)", "sovereign benchmark -n 5"),
        ("remove <model>", "Delete a model (-f to skip confirm)", "sovereign remove llama3:8b"),
        ("serve", "Start the API server (settings-DB host/port)", "sovereign serve"),
        ("benchmark-turboquant <model>", "KV-compression benchmark", "sovereign benchmark-turboquant m.gguf"),
    ]:
        table.add_row(cmd, desc, example)

    console.print(table)
    console.print(Panel.fit(
        "[bold]Chat slash commands:[/bold] /help /stats /clear /mode <m> /model <n> /exit\n"
        "[bold]Env:[/bold] SOVEREIGN_API_BASE overrides the server URL "
        "(default: api_port from the settings DB)\n"
        "[bold]From the project root:[/bold] sovereign <command> "
        "(or: cd backend/app && python -m cli.main <command>)",
        title="Tips", border_style="blue", box=box.ROUNDED
    ))


@app.command()
def system():
    """Show system information"""
    async def _get_system():
        async with httpx.AsyncClient() as client:
            try:
                hw = await client.get(f"{API_BASE}/system/hardware")
                status = await client.get(f"{API_BASE}/system/status")
                rec = await client.get(f"{API_BASE}/system/recommendation")

                if hw.status_code == 200:
                    data = hw.json()
                    gpu = data.get("gpu_name") or "None"
                    if data.get("gpu_vram_gb"):
                        gpu += f" ({data['gpu_vram_gb']} GB)"
                    avx2 = "[green]✓[/green]" if data.get("has_avx2") else "[red]✗[/red]"
                    avx512 = "[green]✓[/green]" if data.get("has_avx512") else "[red]✗[/red]"
                    console.print(Panel.fit(
                        f"[bold]CPU:[/bold] {data.get('cpu_name', 'Unknown')} "
                        f"({data.get('cpu_cores', 0)}c/{data.get('cpu_threads', 0)}t)\n"
                        f"[bold]AVX2:[/bold] {avx2}   [bold]AVX512:[/bold] {avx512}\n"
                        f"[bold]RAM:[/bold] {data.get('ram_total_gb', 0):.1f} GB\n"
                        f"[bold]GPU:[/bold] {gpu}\n"
                        f"[bold]Disk:[/bold] {data.get('disk_type', '?')} "
                        f"({data.get('disk_speed_mb_s', 0):.0f} MB/s)",
                        title="[bold blue]Hardware[/bold blue]",
                        border_style="blue", box=box.ROUNDED
                    ))

                if status.status_code == 200:
                    data = status.json()
                    loaded = "[green]Loaded[/green]" if data.get("model_loaded") else "[dim]None[/dim]"
                    console.print(Panel.fit(
                        f"[bold]Model:[/bold] {data.get('current_model') or 'none'} ({loaded})\n"
                        f"[bold]Mode:[/bold] {data.get('current_mode') or 'n/a'}\n"
                        f"[bold]RAM:[/bold] {data.get('ram_used_gb', 0):.2f} / "
                        f"{data.get('ram_total_gb', 0):.1f} GB\n"
                        f"[bold]Disk free:[/bold] {data.get('disk_free_gb', 0):.1f} GB",
                        title="[bold cyan]Status[/bold cyan]",
                        border_style="cyan", box=box.ROUNDED
                    ))

                if rec.status_code == 200:
                    recs = rec.json().get("recommendations", [])
                    if recs:
                        table = Table(title="Recommended Models", box=box.ROUNDED)
                        table.add_column("Model", style="cyan")
                        table.add_column("Mode")
                        table.add_column("Confidence", justify="center")
                        for r in recs[:5]:
                            conf = r.get("confidence", "")
                            style = "green" if conf == "high" else "yellow"
                            table.add_row(
                                r.get("model", ""),
                                r.get("mode", ""),
                                f"[{style}]{conf}[/{style}]"
                            )
                        console.print(table)
            except httpx.ConnectError:
                console.print("[red]Error: Cannot connect to server[/red]")
                console.print("Make sure the backend is running: 'sovereign serve'")

    asyncio.run(_get_system())


@app.command(name="list")
def list_models():
    """List installed models"""
    async def _list():
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{API_BASE}/models/")

                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])

                    if not models:
                        console.print("[dim]No models installed[/dim]")
                        console.print("Use 'sovereign pull <model>' to download")
                        return

                    table = Table(title="Installed Models", box=box.ROUNDED)
                    table.add_column("Name", style="cyan")
                    table.add_column("Size", justify="right")
                    table.add_column("Quant")
                    table.add_column("Family")
                    table.add_column("Modes")

                    for model in models:
                        modes = ", ".join(model.get("modes_supported", []))
                        table.add_row(
                            model.get("name", ""),
                            f"{model.get('size_gb', 0):.1f} GB",
                            model.get("quant", ""),
                            model.get("family", "?"),
                            modes
                        )

                    console.print(table)
            except httpx.ConnectError:
                console.print("[red]Error: Cannot connect to server[/red]")

    asyncio.run(_list())


@app.command()
def pull(
    model: str = typer.Argument(..., help="Model to download (e.g., llama3:8b)"),
    quant: str = typer.Option("Q4_K_M", "--quant", "-q", help="Quantization")
):
    """Download a model"""
    async def _pull():
        console.print(f"[bold blue]Pulling:[/bold blue] [cyan]{model}[/cyan] [dim]({quant})[/dim]")

        async with httpx.AsyncClient(timeout=600) as client:
            try:
                # Start download
                response = await client.post(
                    f"{API_BASE}/models/pull",
                    json={"model": model, "quant": quant}
                )

                if response.status_code != 200:
                    console.print(f"[red]Error:[/red] {response.text}")
                    return

                result = response.json()

                if result["status"] == "exists":
                    console.print("[green]✓ Model already exists[/green]")
                    return

                # Poll for progress with a live bar
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=console
                ) as progress:
                    task = progress.add_task("Downloading...", total=100)
                    while True:
                        status_resp = await client.get(
                            f"{API_BASE}/models/pull/status/{model}"
                        )
                        if status_resp.status_code != 200:
                            break

                        status = status_resp.json()
                        st = status["status"]

                        if st == "complete":
                            progress.update(
                                task, completed=100,
                                description="[green]✓ Download complete[/green]"
                            )
                            break

                        if st == "error":
                            progress.update(
                                task, description=f"[red]Error: {status.get('error')}[/red]"
                            )
                            break

                        if st == "downloading":
                            progress.update(
                                task,
                                completed=status.get("progress", 0),
                                description=(
                                    f"Downloading ({status.get('downloaded_gb', 0):.2f} GB)"
                                )
                            )
                        elif st in ("verifying", "encrypting"):
                            progress.update(task, description=f"{st.capitalize()}...")

                        await asyncio.sleep(1)

            except httpx.ConnectError:
                console.print("[red]Error: Cannot connect to server[/red]")
                console.print("Make sure the backend is running: 'sovereign serve'")

    asyncio.run(_pull())


@app.command()
def run(
    model: str = typer.Argument(..., help="Model to run"),
    mode: str = typer.Option("auto", "--mode", "-m", help="Execution mode")
):
    """Run a model and start interactive chat (server must be running)"""
    asyncio.run(_run_chat(model, mode))


async def _run_chat(model: str, mode: str) -> None:
    """Load the model and run the interactive chat TUI."""
    async with httpx.AsyncClient(timeout=300) as client:
        try:
            # Load model
            console.print(
                f"[bold blue]Loading[/bold blue] [cyan]{model}[/cyan] "
                f"[dim](mode: {mode})[/dim] ..."
            )
            response = await client.post(
                f"{API_BASE}/models/load",
                json={"model": model, "mode": mode}
            )

            if response.status_code != 200:
                error = response.json().get("detail", "Unknown error")
                console.print(f"[red]Error:[/red] {error}")
                return

            result = response.json()
            ram = result.get("ram_usage", {}).get("ram_used_gb", 0)
            console.print(_chat_banner(result.get("model"), result.get("mode"), ram))
            console.print("[dim]Type a message · /help for commands · /exit to quit[/dim]")

            messages = []

            while True:
                try:
                    user_input = console.input("[bold cyan]You >[/bold cyan] ")
                except (KeyboardInterrupt, EOFError):
                    console.print("\n[dim]Goodbye![/dim]")
                    break

                cmd = user_input.strip().lower()
                if cmd in ("exit", "quit", "/exit", "/quit"):
                    console.print("[dim]Goodbye![/dim]")
                    break
                if cmd == "/help":
                    console.print(Panel.fit(
                        "[bold]/stats[/bold]     - Model / RAM / disk status\n"
                        "[bold]/clear[/bold]     - Clear conversation\n"
                        "[bold]/mode <m>[/bold]  - Switch mode (fullram/layerstream/auto)\n"
                        "[bold]/model <n>[/bold] - Switch model\n"
                        "[bold]/exit[/bold]      - Quit chat",
                        title="Commands", border_style="blue", box=box.ROUNDED
                    ))
                    continue
                if cmd == "/clear":
                    messages.clear()
                    console.clear()
                    console.print(_chat_banner(result.get("model"), result.get("mode"), ram))
                    console.print("[dim]Conversation cleared[/dim]")
                    continue
                if cmd == "/stats":
                    await _show_stats(client)
                    continue
                if cmd.startswith("/mode "):
                    await _switch_mode(client, cmd.split(" ", 1)[1])
                    continue
                if cmd.startswith("/model "):
                    await _switch_model(client, cmd.split(" ", 1)[1], mode, messages)
                    continue
                if cmd.startswith("/"):
                    console.print(f"[red]Unknown command:[/red] {cmd} [dim](try /help)[/dim]")
                    continue
                if not user_input.strip():
                    continue

                messages.append({"role": "user", "content": user_input})
                console.print(f"\n[bold cyan]You >[/bold cyan] {user_input}")
                console.print("[bold green]AI >[/bold green] ", end="")

                # Stream response
                full_response = ""
                started = time.perf_counter()
                try:
                    async with client.stream(
                        "POST",
                        f"{API_BASE}/chat/completions",
                        json={
                            "messages": messages,
                            "stream": True,
                            "max_tokens": 512
                        }
                    ) as response:
                        if response.status_code != 200:
                            console.print(f"[red]Error: {response.status_code}[/red]")
                            continue
                        async for line in response.aiter_lines():
                            if not line.startswith("data: "):
                                continue
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            content, reasoning = _sse_delta(data)
                            if content:
                                console.print(content, end="")
                                full_response += content
                            elif reasoning:
                                # thinking models (e.g. Qwen3.5) send reasoning deltas first
                                console.print(f"[dim]{reasoning}[/dim]", end="")
                except httpx.HTTPError as e:
                    console.print(f"\n[red]Error: {e}[/red]")
                    continue

                elapsed = time.perf_counter() - started
                console.print(
                    f"\n[dim]· {elapsed:.1f}s · {len(full_response.split())} words[/dim]"
                )
                console.rule(style="dim")
                if full_response.strip():
                    messages.append({"role": "assistant", "content": full_response})

        except httpx.ConnectError:
            console.print("[red]Error: Cannot connect to server[/red]")
            console.print("Make sure the backend is running: 'sovereign serve'")


async def _show_stats(client: httpx.AsyncClient) -> None:
    """/stats — show model, mode, RAM and disk usage."""
    response = await client.get(f"{API_BASE}/system/status")
    if response.status_code != 200:
        console.print("[red]Could not fetch stats[/red]")
        return
    s = response.json()
    console.print(Panel.fit(
        f"[bold]Model:[/bold] {s.get('current_model') or 'none'}  "
        f"[bold]Mode:[/bold] {s.get('current_mode') or 'n/a'}\n"
        f"[bold]RAM:[/bold] {s.get('ram_used_gb', 0):.1f} / {s.get('ram_total_gb', 0):.1f} GB  "
        f"[bold]Disk free:[/bold] {s.get('disk_free_gb', 0):.1f} GB",
        title="System", border_style="cyan", box=box.ROUNDED
    ))


async def _switch_mode(client: httpx.AsyncClient, new_mode: str) -> None:
    """/mode <m> — switch execution mode."""
    if new_mode not in ("fullram", "layerstream", "auto"):
        console.print("[red]Invalid mode. Use: fullram, layerstream, auto[/red]")
        return
    response = await client.post(f"{API_BASE}/chat/mode/switch", params={"mode": new_mode})
    if response.status_code == 200:
        console.print(f"[green]✓ Switched to {new_mode} mode[/green]")
    else:
        console.print(f"[red]Failed to switch mode: {response.status_code}[/red]")


async def _switch_model(client: httpx.AsyncClient, name: str, mode: str, messages: list) -> None:
    """/model <n> — load a different model, resetting the conversation."""
    response = await client.post(f"{API_BASE}/models/load", json={"model": name, "mode": mode})
    if response.status_code == 200:
        messages.clear()
        console.clear()
        console.print(_chat_banner(name, mode))
        console.print("[dim]Conversation reset[/dim]")
    else:
        detail = response.json().get("detail", response.status_code)
        console.print(f"[red]Failed:[/red] {detail}")


def _server_log_path() -> Path:
    """Log file for a CLI-started server (workspace/logs, portable)."""
    return Path(__file__).resolve().parents[3] / "workspace" / "logs" / "server_cli.log"


async def _server_healthy() -> bool:
    """True if the backend responds on /health."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{SERVER_ORIGIN}/health")
            return response.status_code < 500
    except httpx.HTTPError:
        return False


def _start_server():
    """Launch the backend server in the background, logging to workspace/logs."""
    import subprocess
    backend_dir = Path(__file__).resolve().parents[2]
    log_dir = _server_log_path().parent
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = open(_server_log_path(), "ab", buffering=0)
    return subprocess.Popen(
        [sys.executable, str(backend_dir / "main.py")],
        cwd=str(backend_dir),
        stdout=log_file,
        stderr=log_file,
    )


async def _wait_for_server(proc, timeout: float = 90.0) -> bool:
    """Poll /health until the server responds. True when healthy."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console, transient=True
    ) as progress:
        progress.add_task("Waiting for server to start...", total=None)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if await _server_healthy():
                return True
            if proc is not None and proc.poll() is not None:
                # The process died — most likely the port is already bound by a
                # server that is still booting. Give it a few seconds to come up.
                grace = time.monotonic() + 5
                while time.monotonic() < grace:
                    if await _server_healthy():
                        return True
                    await asyncio.sleep(1)
                return False
            await asyncio.sleep(1)
    return False


async def _ensure_server() -> tuple[bool, bool]:
    """Start the backend if it isn't running. Returns (healthy, started_now)."""
    if await _server_healthy():
        return True, False
    if os.environ.get("SOVEREIGN_API_BASE"):
        # Auto-start boots the local backend on the settings-DB port, which may
        # differ from the env override — refuse rather than wait 90s on the wrong port.
        console.print("[red]Server not reachable at SOVEREIGN_API_BASE.[/red]")
        console.print(
            "[dim]Auto-start only applies to the settings-DB origin — start the "
            "server manually with 'sovereign serve'.[/dim]"
        )
        return False, False
    console.print("[yellow]Server is not running — starting it...[/yellow]")
    proc = _start_server()
    if await _wait_for_server(proc):
        console.print("[green]✓ Server is running[/green]")
        return True, True
    console.print("[red]Server failed to start.[/red]")
    console.print(f"[dim]Check the log: {_server_log_path()}[/dim]")
    return False, True


async def _chat(model: str, mode: str) -> None:
    """Auto-start the server if needed, then run the chat TUI."""
    healthy, started = await _ensure_server()
    if not healthy:
        raise typer.Exit(code=1)
    await _run_chat(model, mode)
    if started:
        console.print(
            f"[dim]Server left running in the background (log: {_server_log_path()}).[/dim]"
        )


@app.command()
def chat(
    model: str = typer.Argument(..., help="Model to run (starts the server automatically if needed)"),
    mode: str = typer.Option("auto", "--mode", "-m", help="Execution mode")
):
    """Start the server if needed, then load a model and chat"""
    asyncio.run(_chat(model, mode))


@app.command()
def benchmark(
    iterations: int = typer.Option(3, "--iterations", "-n"),
    tokens: int = typer.Option(100, "--tokens", "-t")
):
    """Run inference benchmark"""
    async def _benchmark():
        async with httpx.AsyncClient(timeout=300) as client:
            try:
                # Check if model is loaded
                status = await client.get(f"{API_BASE}/system/status")
                if status.status_code == 200:
                    data = status.json()
                    if not data.get("model_loaded"):
                        console.print("[red]No model loaded. Use 'sovereign run <model>' first[/red]")
                        return

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console, transient=True
                ) as progress:
                    progress.add_task("Benchmarking...", total=None)
                    response = await client.post(
                        f"{API_BASE}/benchmark/run",
                        json={"iterations": iterations, "max_tokens": tokens}
                    )

                if response.status_code == 200:
                    result = response.json()

                    # Results table
                    table = Table(title="Benchmark Results", box=box.ROUNDED)
                    table.add_column("Iteration")
                    table.add_column("Tokens", justify="right")
                    table.add_column("Time (s)", justify="right")
                    table.add_column("TPS", justify="right", style="green")

                    for run in result.get("runs", []):
                        table.add_row(
                            str(run["iteration"]),
                            str(run["tokens"]),
                            f"{run['time_seconds']:.3f}",
                            f"{run['tokens_per_second']:.2f}"
                        )

                    console.print(table)

                    # Summary
                    summary = result.get("summary", {})
                    console.print(Panel.fit(
                        f"[bold]Average TPS:[/bold] [green]{summary.get('average_tokens_per_second', 0):.2f}[/green]  "
                        f"[bold]Total Tokens:[/bold] {summary.get('total_tokens', 0)}  "
                        f"[bold]Peak RAM:[/bold] {summary.get('peak_ram_gb', 0):.2f} GB",
                        title="Summary", border_style="green", box=box.ROUNDED
                    ))
                else:
                    console.print(f"[red]Error:[/red] {response.text}")

            except httpx.ConnectError:
                console.print("[red]Error: Cannot connect to server[/red]")

    asyncio.run(_benchmark())


@app.command()
def remove(
    model: str = typer.Argument(..., help="Model to remove"),
    force: bool = typer.Option(False, "--force", "-f")
):
    """Remove a model"""
    async def _remove():
        if not force:
            confirm = typer.confirm(f"Remove model '{model}'?")
            if not confirm:
                console.print("[dim]Cancelled[/dim]")
                return

        async with httpx.AsyncClient() as client:
            try:
                response = await client.delete(f"{API_BASE}/models/{model}")

                if response.status_code == 200:
                    console.print(f"[green]✓ Model removed: {model}[/green]")
                elif response.status_code == 404:
                    console.print(f"[red]Model not found: {model}[/red]")
                else:
                    console.print(f"[red]Error:[/red] {response.text}")

            except httpx.ConnectError:
                console.print("[red]Error: Cannot connect to server[/red]")

    asyncio.run(_remove())


@app.command()
def serve(
    host: str = typer.Option(None, "--host", "-h", help="Bind host (default: from settings DB)"),
    port: int = typer.Option(None, "--port", "-p", help="Bind port (default: from settings DB)")
):
    """Start the API server (honors settings DB host/port by default)"""
    import subprocess

    backend_dir = Path(__file__).resolve().parents[2]
    if host is None and port is None:
        console.print("[bold]Starting server with settings DB config...[/bold]")
        subprocess.run([sys.executable, str(backend_dir / "main.py")])
    else:
        console.print(f"[bold]Starting server at {host or '0.0.0.0'}:{port or 8000}[/bold]")
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", host or "0.0.0.0",
            "--port", str(port or 8000)
        ], cwd=str(backend_dir))


@app.command()
def benchmark_turboquant(
    model: str = typer.Argument(..., help="Model path or name"),
    bits: float = typer.Option(3.5, "--bits", "-b", help="Bits per coordinate"),
    context_len: int = typer.Option(32768, "--context", "-c", help="Context length"),
    compare: bool = typer.Option(True, "--compare/--no-compare", help="Compare with FP16 baseline"),
):
    """Benchmark TurboQuant KV compression vs standard FP16 cache."""
    from app.engines.shared.turboquant import TurboQuantConfig, TurboQuantKVCacheManager

    console.print(f"[bold]TurboQuant Benchmark[/bold]")
    console.print(f"  Model: {model}")
    console.print(f"  Bits: {bits}")
    console.print(f"  Context: {context_len}")
    console.print(f"  Compare FP16: {compare}")

    # Synthetic benchmark: measure compression ratio and reconstruction error
    import torch
    import numpy as np

    head_dim = 128
    num_heads = 32
    num_layers = 32
    seq_len = min(context_len, 4096)  # synthetic limit

    console.print("\n[bold]Generating synthetic K/V data...[/bold]")
    k = torch.randn(1, num_heads, seq_len, head_dim, dtype=torch.float16)
    v = torch.randn(1, num_heads, seq_len, head_dim, dtype=torch.float16)

    # Baseline FP16 size (across all layers)
    layer_fp16 = (k.numel() + v.numel()) * 2  # 2 bytes per fp16
    total_fp16 = layer_fp16 * num_layers
    console.print(f"  FP16 cache size ({num_layers} layers): {total_fp16 / 1024**3:.3f} GB")

    # TurboQuant
    config = TurboQuantConfig(bits_per_coord=bits, device="cpu")
    tq_mgr = TurboQuantKVCacheManager(config, num_layers, num_heads, head_dim, "cpu")

    console.print(f"\n[bold]Running TurboQuant compression...[/bold]")
    start = time.perf_counter()
    for layer in range(num_layers):
        tq_mgr.update(layer, k, v)
    elapsed = time.perf_counter() - start

    compressed_mb = tq_mgr.get_size_mb()
    compressed_gb = compressed_mb / 1024
    # ponytail: without bit-packing, indices use 1 byte + QJL 1 byte = 2 bytes = same as FP16
    # Target 3-6x requires packing 3.5-bit indices into int32 words (9 indices/word)
    ratio = total_fp16 / (compressed_mb * 1024 * 1024)

    console.print(f"  Compressed size ({num_layers} layers): {compressed_gb:.3f} GB")
    console.print(f"  Naive compression ratio: {ratio:.1f}x")
    console.print(f"  Estimated (bit-packed 3.5-bit indices): {ratio * 4:.1f}x")
    console.print(f"  Quantization time: {elapsed:.3f}s")

    # Reconstruction error
    k_recon, v_recon = tq_mgr.get(0)
    if k_recon is not None:
        mse = torch.mean((k_recon.to(torch.float32) - k.to(torch.float32)) ** 2).item()
        console.print(f"  K reconstruction MSE: {mse:.6f} (target <0.2 for raw K/V)")

    # Results table
    table = Table(title="Benchmark Results")
    table.add_column("Metric", style="cyan")
    table.add_column("FP16", justify="right")
    table.add_column(f"TurboQuant {bits}-bit", justify="right", style="green")
    table.add_column("Ratio", justify="right")

    table.add_row(
        f"KV Cache Size ({num_layers} layers)",
        f"{total_fp16 / 1024**3:.3f} GB",
        f"{compressed_gb:.3f} GB",
        f"{ratio:.1f}x"
    )

    console.print(table)
    console.print(f"\n[dim]Synthetic data only. Real model accuracy depends on attention distribution.[/dim]")
    console.print(f"[dim]With bit-packing + QJL pruning, expected real ratio: 3-6x at {bits} bits/coord.[/dim]")


if __name__ == "__main__":
    app()
