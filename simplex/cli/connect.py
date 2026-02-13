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
    """Render an SSE event as clean, structured log output."""
    event_type = event.get("event") or event.get("type", "")

    if event_type == "RunContent":
        content = event.get("content", "")
        if content and content != "SIMPLEX_AGENT_INITIALIZED":
            console.print(content, end="")

    elif event_type == "ToolCallStarted":
        tool = event.get("tool", {})
        tool_name = tool.get("tool_name", "unknown") if isinstance(tool, dict) else "unknown"
        tool_args = tool.get("tool_args", {}) if isinstance(tool, dict) else {}
        console.print(f"\n  [cyan]{tool_name}[/cyan]", end="")
        # Show key args inline for common tools
        if isinstance(tool_args, dict):
            if "file_path" in tool_args:
                console.print(f" [dim]{tool_args['file_path']}[/dim]", end="")
            elif "command" in tool_args:
                cmd = str(tool_args["command"])[:120]
                console.print(f" [dim]{cmd}[/dim]", end="")
            elif "selector" in tool_args:
                console.print(f" [dim]{tool_args['selector']}[/dim]", end="")
        console.print()

    elif event_type == "ToolCallCompleted":
        pass  # Agent text after tool calls is more useful than raw results

    elif event_type == "FlowPaused":
        pause_type = event.get("pause_type", "")
        console.print(f"\n[bold yellow]Paused[/bold yellow] ({pause_type})")
        prompt = event.get("prompt", "")
        if prompt:
            console.print(f"  {prompt}")
        console.print("[dim]Use 'simplex send <session_id> \"message\"' to respond.[/dim]")

    elif event_type in ("RunCompleted", "RunFinished"):
        metrics = event.get("metrics", {})
        duration = metrics.get("duration_ms", 0) / 1000 if metrics else 0
        succeeded = event.get("succeeded", None)
        if succeeded is False:
            console.print(f"\n[bold red]Failed[/bold red]", end="")
        else:
            console.print(f"\n[bold green]Completed[/bold green]", end="")
        if duration:
            console.print(f" [dim]({duration:.1f}s)[/dim]")
        else:
            console.print()

    elif event_type == "RunError":
        error = event.get("error", event.get("content", ""))
        console.print(f"\n[bold red]Error:[/bold red] {error}")

    elif event_type == "RunStarted":
        console.print("[dim]Agent running...[/dim]")

    elif event_type in ("NewMessage", "AgentRunning"):
        pass  # Internal events, skip

    else:
        console.print(f"[dim][{event_type}][/dim]")
