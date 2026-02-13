"""Connect command — stream SSE events from a live session."""

from __future__ import annotations

import json
from typing import Optional

import typer
from rich.panel import Panel
from rich.text import Text

from simplex.cli.config import load_current_session, make_client_kwargs
from simplex.cli.output import console, print_error


def connect(
    session_id: Optional[str] = typer.Argument(None, help="Session ID, workflow ID, or logs_url (defaults to current session)"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON events (for piping)"),
) -> None:
    """Stream live events from a running session."""
    from simplex import SimplexClient, SimplexError

    # Resolve target — use current session if not provided
    if not session_id:
        current = load_current_session()
        if not current:
            print_error("No target specified and no current session. Start one with 'simplex editor' or pass a session/workflow ID.")
            raise typer.Exit(1)
        session_id = current["workflow_id"]
        if not json_output:
            console.print(f"[dim]Using current session ({session_id[:8]}...)[/dim]")

    try:
        client = SimplexClient(**make_client_kwargs())
    except (SimplexError, ValueError) as e:
        print_error(str(e))
        raise typer.Exit(1)

    # Determine if argument is a URL, workflow ID, or session ID
    if session_id.startswith("http://") or session_id.startswith("https://"):
        logs_url = session_id
    else:
        logs_url = None
        # Try as workflow ID first (get active session), fall back to session ID
        try:
            result = client.get_workflow_active_session(session_id)
            logs_url = result.get("logs_url", "")
        except Exception:
            pass

        if not logs_url:
            try:
                status = client.get_session_status(session_id)
                logs_url = status.get("logs_url", "")
            except SimplexError:
                pass

        if not logs_url:
            print_error(f"No active session found for '{session_id}'")
            raise typer.Exit(1)

    if not json_output:
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


# ── Event renderer ────────────────────────────────────────────────────────────

# Track state across events for cleaner rendering
_last_event_type: str = ""


def _render_event(event: dict) -> None:
    """Render an SSE event as clean, structured terminal output."""
    global _last_event_type
    event_type = event.get("event") or event.get("type", "")

    if event_type == "RunContent":
        content = event.get("content", "")
        if content and content != "SIMPLEX_AGENT_INITIALIZED":
            # Agent thinking/text — stream inline
            console.print(content, end="", highlight=False)
        _last_event_type = event_type

    elif event_type == "ToolCallStarted":
        tool = event.get("tool", {})
        tool_name = tool.get("tool_name", "unknown") if isinstance(tool, dict) else "unknown"
        tool_args = tool.get("tool_args", {}) if isinstance(tool, dict) else {}

        # Add spacing after agent text
        if _last_event_type == "RunContent":
            console.print()

        # Format tool call with icon and key argument
        detail = _format_tool_detail(tool_name, tool_args)
        if detail:
            console.print(f"  [cyan]>[/cyan] [bold]{tool_name}[/bold] [dim]{detail}[/dim]")
        else:
            console.print(f"  [cyan]>[/cyan] [bold]{tool_name}[/bold]")

        _last_event_type = event_type

    elif event_type == "ToolCallCompleted":
        # Show errors from tool results, skip normal completions
        tool = event.get("tool", {})
        if isinstance(tool, dict) and tool.get("tool_call_error"):
            content = tool.get("content", "")
            if content:
                console.print(f"    [red]error: {str(content)[:200]}[/red]")
        _last_event_type = event_type

    elif event_type == "FlowPaused":
        if _last_event_type == "RunContent":
            console.print()
        pause_type = event.get("pause_type", "")
        prompt = event.get("prompt", "")
        panel_content = Text()
        if prompt:
            panel_content.append(prompt)
            panel_content.append("\n\n")
        panel_content.append("Use ", style="dim")
        panel_content.append("simplex send \"message\"", style="bold")
        panel_content.append(" to respond.", style="dim")
        console.print()
        console.print(Panel(
            panel_content,
            title="[bold yellow]Paused[/bold yellow]" + (f" ({pause_type})" if pause_type else ""),
            border_style="yellow",
            padding=(0, 2),
        ))
        _last_event_type = event_type

    elif event_type == "FlowResumed":
        console.print("[green]Resumed[/green]\n")
        _last_event_type = event_type

    elif event_type in ("RunCompleted", "RunFinished"):
        if _last_event_type == "RunContent":
            console.print()
        metrics = event.get("metrics", {})
        duration = metrics.get("duration_ms", 0) / 1000 if metrics else 0
        succeeded = event.get("succeeded", None)

        if succeeded is False:
            status = "[bold red]Failed[/bold red]"
        else:
            status = "[bold green]Completed[/bold green]"

        duration_str = f" in {duration:.1f}s" if duration else ""
        console.print(f"\n{status}{duration_str}")
        _last_event_type = event_type

    elif event_type == "RunError":
        if _last_event_type == "RunContent":
            console.print()
        error = event.get("error", event.get("content", ""))
        console.print(f"\n[bold red]Error:[/bold red] {error}")
        _last_event_type = event_type

    elif event_type == "RunStarted":
        console.print("[dim]Agent started[/dim]\n")
        _last_event_type = event_type

    elif event_type in ("NewMessage", "AgentRunning"):
        pass  # Internal events, skip

    else:
        # Show unknown events dimmed so nothing gets silently lost
        if event_type:
            console.print(f"[dim][{event_type}][/dim]")
        _last_event_type = event_type


def _format_tool_detail(tool_name: str, tool_args: dict) -> str:
    """Extract the most useful argument to show inline for a tool call."""
    if not isinstance(tool_args, dict):
        return ""

    # File operations — show the path
    if "file_path" in tool_args:
        return tool_args["file_path"]

    # Shell commands — show the command (truncated)
    if "command" in tool_args:
        cmd = str(tool_args["command"])
        return cmd[:120] + ("..." if len(cmd) > 120 else "")

    # Browser actions — show selector or description
    if "selector" in tool_args:
        return tool_args["selector"]
    if "description" in tool_args:
        return str(tool_args["description"])[:100]

    # URL-based tools
    if "url" in tool_args:
        return str(tool_args["url"])[:120]

    # Text/content tools
    if "text" in tool_args:
        text = str(tool_args["text"])
        return text[:80] + ("..." if len(text) > 80 else "")

    # Search/pattern
    if "pattern" in tool_args:
        return tool_args["pattern"]

    # Generic: show first string arg
    for v in tool_args.values():
        if isinstance(v, str) and len(v) > 2:
            return v[:100]

    return ""
