"""Connect command — stream SSE events from a live session."""

from __future__ import annotations

import json
from typing import Any, Optional

import typer
from rich.panel import Panel
from rich.text import Text

from simplex.cli.config import make_client_kwargs
from simplex.cli.output import console, print_error


def _resolve_workflow_id(client, target: str, quiet: bool = False) -> str:
    """Resolve a target (workflow name or ID) to a workflow ID via the API."""
    if len(target) >= 32 or "-" in target:
        return target

    try:
        result = client.search_workflows(workflow_name=target)
        workflows = result.get("workflows", [])
        if workflows:
            wf = workflows[0]
            if not quiet:
                console.print(f"[dim]{wf.get('workflow_name', '')} ({wf['workflow_id'][:8]}...)[/dim]")
            return wf["workflow_id"]
    except Exception:
        pass

    return target


def _derive_message_url(logs_url: str) -> str | None:
    """Derive the message URL from a logs/stream URL."""
    if logs_url and "/stream" in logs_url:
        return logs_url.rsplit("/stream", 1)[0] + "/message"
    return None


def connect(
    target: str = typer.Argument(help="Workflow name, ID, or logs URL"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON events (for piping)"),
) -> None:
    """Stream live events from a running session."""
    from simplex import SimplexClient, SimplexError

    try:
        client = SimplexClient(**make_client_kwargs())
    except (SimplexError, ValueError) as e:
        print_error(str(e))
        raise typer.Exit(1)

    # Determine if argument is a URL or a workflow name/ID
    if target.startswith("http://") or target.startswith("https://"):
        logs_url = target
    else:
        logs_url = None
        workflow_id = _resolve_workflow_id(client, target, quiet=json_output)

        # Try as workflow ID first (get active session), fall back to session ID
        try:
            result = client.get_workflow_active_session(workflow_id)
            logs_url = result.get("logs_url", "")
        except Exception:
            pass

        if not logs_url:
            try:
                status = client.get_session_status(workflow_id)
                logs_url = status.get("logs_url", "")
            except SimplexError:
                pass

        if not logs_url:
            print_error(f"No active session found for '{target}'")
            raise typer.Exit(1)

    message_url = _derive_message_url(logs_url)

    if not json_output:
        console.print()
        console.print("[bold]Streaming events...[/bold] (Ctrl+C to stop)\n")

    try:
        for event in client.stream_session(logs_url):
            if json_output:
                print(json.dumps(event), flush=True)
                continue

            event_type = event.get("event") or event.get("type", "")
            if event_type == "AskUserQuestion" and message_url:
                _render_event(event)
                _handle_ask_user_interactive(event, client, message_url)
            else:
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

    elif event_type == "AskUserQuestion":
        if _last_event_type == "RunContent":
            console.print()
        data = event.get("data", event)
        questions = data.get("questions", [])
        for i, q in enumerate(questions):
            header = q.get("header", "Question")
            question_text = q.get("question", "")
            options = q.get("options", [])
            multi = q.get("multiSelect", False)

            lines = Text()
            lines.append(f"{question_text}\n\n")
            for j, opt in enumerate(options):
                label = opt.get("label", "")
                desc = opt.get("description", "")
                lines.append(f"  [{j + 1}] ", style="bold cyan")
                lines.append(label)
                if desc:
                    lines.append(f" — {desc}", style="dim")
                lines.append("\n")
            if multi:
                lines.append("\nSelect multiple (comma-separated) or type a response:", style="dim")
            else:
                lines.append("\nEnter choice or type a response:", style="dim")

            console.print()
            console.print(Panel(
                lines,
                title=f"[bold yellow]{header}[/bold yellow]",
                border_style="yellow",
                padding=(0, 2),
            ))
        _last_event_type = event_type

    elif event_type in ("NewMessage", "AgentRunning"):
        pass  # Internal events, skip

    else:
        # Show unknown events dimmed so nothing gets silently lost
        if event_type:
            console.print(f"[dim][{event_type}][/dim]")
        _last_event_type = event_type


def _handle_ask_user_interactive(event: dict, client: Any, message_url: str) -> None:
    """Handle an AskUserQuestion event interactively: prompt the user and send the answer back."""
    data = event.get("data", event)
    tool_use_id = data.get("tool_use_id", "")
    questions = data.get("questions", [])
    answers: dict[str, str] = {}

    for i, q in enumerate(questions):
        options = q.get("options", [])
        multi = q.get("multiSelect", False)

        raw = console.input("[bold yellow]> [/bold yellow]").strip()
        if not raw:
            continue

        if multi:
            # Comma-separated numbers or free text
            parts = [p.strip() for p in raw.split(",")]
            selected: list[str] = []
            for part in parts:
                if part.isdigit() and 1 <= int(part) <= len(options):
                    selected.append(options[int(part) - 1].get("label", part))
                else:
                    selected.append(part)
            answers[str(i)] = ", ".join(selected)
        else:
            if raw.isdigit() and 1 <= int(raw) <= len(options):
                answers[str(i)] = options[int(raw) - 1].get("label", raw)
            else:
                answers[str(i)] = raw

    # Send the answer back
    answer_payload = json.dumps({
        "type": "ask_user_answer",
        "tool_use_id": tool_use_id,
        "answers": answers,
    })

    try:
        client.send_message(message_url, answer_payload)
        console.print("[green]Answer sent.[/green]\n")
    except Exception as e:
        print_error(f"Failed to send answer: {e}")


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
