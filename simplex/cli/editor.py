"""Editor command — create a workflow + editor session, then auto-connect."""

from __future__ import annotations

import json
from typing import Any, Optional

import typer

from simplex.cli.config import make_client_kwargs
from simplex.cli.connect import _render_event
from simplex.cli.output import console, print_error, print_kv


def _parse_variables(var_list: list[str] | None) -> dict[str, Any] | None:
    """Parse --var key=value pairs into a dict."""
    if not var_list:
        return None
    variables: dict[str, Any] = {}
    for item in var_list:
        if "=" not in item:
            print_error(f"Invalid variable format: '{item}'. Use key=value.")
            raise typer.Exit(1)
        key, value = item.split("=", 1)
        variables[key] = value
    return variables


def editor(
    name: str = typer.Option(..., "--name", "-n", help="Workflow name"),
    url: str = typer.Option(..., "--url", "-u", help="Starting URL"),
    var: Optional[list[str]] = typer.Option(None, "--var", "-v", help="Test data variable as key=value (repeatable)"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON events (for piping)"),
) -> None:
    """Create a workflow and start an editor session, then stream events."""
    from simplex import SimplexClient, SimplexError

    test_data = _parse_variables(var)

    try:
        client = SimplexClient(**make_client_kwargs())
    except (SimplexError, ValueError) as e:
        print_error(str(e))
        raise typer.Exit(1)

    # Start editor session (creates workflow + session)
    try:
        result = client.start_editor_session(name=name, url=url, test_data=test_data)
    except SimplexError as e:
        print_error(str(e))
        raise typer.Exit(1)

    session_id = result["session_id"]
    workflow_id = result["workflow_id"]
    vnc_url = result.get("vnc_url", "")
    logs_url = result.get("logs_url", "")
    message_url = result.get("message_url", "")

    if json_output:
        # Print session info as first JSON line
        print(json.dumps({
            "type": "SessionStarted",
            "session_id": session_id,
            "workflow_id": workflow_id,
            "vnc_url": vnc_url,
            "logs_url": logs_url,
            "message_url": message_url,
        }), flush=True)
    else:
        print_kv([
            ("Workflow ID", workflow_id),
            ("Session ID", session_id),
            ("VNC URL", vnc_url),
            ("Logs URL", logs_url),
            ("Message URL", message_url or "N/A"),
        ])
        console.print()
        console.print("[bold]Streaming events...[/bold] (Ctrl+C to stop)\n")

    if not logs_url:
        print_error("No logs_url returned — cannot stream events.")
        raise typer.Exit(1)

    # Auto-connect: stream SSE events
    try:
        for event in client.stream_session(logs_url):
            if json_output:
                print(json.dumps(event, default=str), flush=True)
            else:
                _render_event(event)
    except KeyboardInterrupt:
        if not json_output:
            console.print("\n[yellow]Disconnected.[/yellow]")
        raise typer.Exit(0)
    except Exception as e:
        print_error(f"Stream error: {e}")
        raise typer.Exit(1)
