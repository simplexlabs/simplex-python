"""Send command — send a message to a running session's browser agent."""

from __future__ import annotations

import typer

from simplex.cli.config import make_client_kwargs
from simplex.cli.output import console, print_error


def send(
    target: str = typer.Argument(help="Session ID or workflow ID"),
    message: str = typer.Argument(help="Message to send to the browser agent"),
) -> None:
    """Send a message to a running session's browser agent."""
    from simplex import SimplexClient, SimplexError

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
        session_id = result.get("session_id", target)
        if not message_url:
            # Derive from logs_url
            logs_url = result.get("logs_url", "")
            if logs_url and "/stream" in logs_url:
                message_url = logs_url.rsplit("/stream", 1)[0] + "/message"
    except Exception:
        # Not a workflow ID or lookup failed — try as session ID
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
