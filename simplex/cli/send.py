"""Send command — send a message to a running session's browser agent."""

from __future__ import annotations

from typing import Optional

import typer

from simplex.cli.config import load_current_session, load_session_by_prefix, make_client_kwargs
from simplex.cli.output import console, print_error


def send(
    message: str = typer.Argument(help="Message to send to the browser agent"),
    target: Optional[str] = typer.Argument(None, help="Session ID or workflow ID (defaults to current session)"),
) -> None:
    """Send a message to a running session's browser agent."""
    from simplex import SimplexClient, SimplexError

    # Resolve target — use current session if not provided, or match prefix
    if not target:
        current = load_current_session()
        if not current:
            print_error("No target specified and no current session. Start one with 'simplex editor' or pass a session/workflow ID.")
            raise typer.Exit(1)
        target = current["workflow_id"]
        console.print(f"[dim]Using current session ({target[:8]}...)[/dim]")
    else:
        # Try prefix match against saved sessions
        matched = load_session_by_prefix(target)
        if matched:
            target = matched["workflow_id"]

    try:
        client = SimplexClient(**make_client_kwargs())
    except (SimplexError, ValueError) as e:
        print_error(str(e))
        raise typer.Exit(1)

    # Try as workflow ID first (get active session), fall back to session ID
    message_url = None
    try:
        result = client.get_workflow_active_session(target)
        message_url = result.get("message_url")
        if not message_url:
            logs_url = result.get("logs_url", "")
            if logs_url and "/stream" in logs_url:
                message_url = logs_url.rsplit("/stream", 1)[0] + "/message"
    except Exception:
        try:
            status = client.get_session_status(target)
            logs_url = status.get("logs_url", "")
            if logs_url and "/stream" in logs_url:
                message_url = logs_url.rsplit("/stream", 1)[0] + "/message"
        except SimplexError:
            pass

    if not message_url:
        print_error(f"Could not find message URL for '{target}'. Is the session still running?")
        raise typer.Exit(1)

    try:
        client.send_message(message_url, message)
        console.print(f"[green]Message sent.[/green]")
    except Exception as e:
        print_error(f"Failed to send message: {e}")
        raise typer.Exit(1)
