"""Connect command — stream SSE events from a live session."""

from __future__ import annotations

import json
from typing import Optional

import typer

from simplex.cli.config import make_client_kwargs
from simplex.cli.output import console, print_error, print_kv


def connect(
    session_id: str = typer.Argument(help="Session ID or logs_url to connect to"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON events (for piping)"),
) -> None:
    """Stream live events from a running session."""
    from simplex import SimplexClient, SimplexError

    try:
        client = SimplexClient(**make_client_kwargs())
    except (SimplexError, ValueError) as e:
        print_error(str(e))
        raise typer.Exit(1)

    # Determine if argument is a URL or session ID
    if session_id.startswith("http://") or session_id.startswith("https://"):
        logs_url = session_id
    else:
        # Look up session to get logs_url
        try:
            status = client.get_session_status(session_id)
            logs_url = status.get("logs_url", "")
            if not logs_url:
                print_error(f"No logs_url found for session {session_id}")
                raise typer.Exit(1)
        except SimplexError as e:
            print_error(f"Failed to look up session: {e}")
            raise typer.Exit(1)

    # Derive message_url from logs_url (replace /stream with /message)
    message_url = logs_url.rsplit("/stream", 1)[0] + "/message" if "/stream" in logs_url else None

    if not json_output:
        print_kv([
            ("Logs URL", logs_url),
            ("Message URL", message_url or "N/A"),
        ])
        console.print()
        console.print("[bold]Streaming events...[/bold] (Ctrl+C to stop)\n")

    try:
        for event in client.stream_session(logs_url):
            if json_output:
                print(json.dumps(event), flush=True)
                continue

            _render_event(event)

    except KeyboardInterrupt:
        if not json_output:
            console.print("\n[yellow]Disconnected.[/yellow]")
        raise typer.Exit(0)
    except Exception as e:
        print_error(f"Stream error: {e}")
        raise typer.Exit(1)


def _render_event(event: dict) -> None:
    """Render an SSE event with Rich formatting."""
    event_type = event.get("event") or event.get("type", "")

    if event_type == "RunContent":
        content = event.get("content", "")
        if content:
            console.print(content, end="")

    elif event_type == "ToolCallStarted":
        tool_name = event.get("tool_name", "unknown")
        args = event.get("arguments", {})
        console.print(f"\n[dim]--- Tool: {tool_name} ---[/dim]")
        if args:
            for k, v in (args.items() if isinstance(args, dict) else []):
                val = str(v)[:200]
                console.print(f"  [dim]{k}:[/dim] {val}")

    elif event_type == "ToolCallCompleted":
        result = event.get("result", "")
        if result:
            text = str(result)[:500]
            console.print(f"  [green]Result:[/green] {text}")
        console.print("[dim]---[/dim]\n")

    elif event_type == "FlowPaused":
        pause_type = event.get("pause_type", "")
        console.print(f"\n[bold yellow]Session paused[/bold yellow] ({pause_type})")
        prompt = event.get("prompt", "")
        if prompt:
            console.print(f"  Prompt: {prompt}")

    elif event_type in ("RunCompleted", "RunFinished"):
        console.print("\n[bold green]Session completed.[/bold green]")

    elif event_type == "RunError":
        error = event.get("error", "")
        console.print(f"\n[bold red]Session error:[/bold red] {error}")

    else:
        # Print other event types as-is for visibility
        console.print(f"[dim][{event_type}][/dim] {json.dumps(event, default=str)[:200]}")
