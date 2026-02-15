"""Send command — send a message to a running session's browser agent."""

from __future__ import annotations

import typer

from simplex.cli.config import make_client_kwargs
from simplex.cli.output import console, print_error


def send(
    workflow_id: str = typer.Argument(help="Workflow ID"),
    message: str = typer.Argument(help="Message to send to the browser agent"),
) -> None:
    """Send a message to a running session's browser agent."""
    from simplex import SimplexClient, SimplexError

    try:
        client = SimplexClient(**make_client_kwargs())
    except (SimplexError, ValueError) as e:
        print_error(str(e))
        raise typer.Exit(1)

    # Get active session's message URL
    message_url = None
    try:
        result = client.get_workflow_active_session(workflow_id)
        message_url = result.get("message_url")
        if not message_url:
            logs_url = result.get("logs_url", "")
            if logs_url and "/stream" in logs_url:
                message_url = logs_url.rsplit("/stream", 1)[0] + "/message"
    except Exception:
        try:
            status = client.get_session_status(workflow_id)
            logs_url = status.get("logs_url", "")
            if logs_url and "/stream" in logs_url:
                message_url = logs_url.rsplit("/stream", 1)[0] + "/message"
        except SimplexError:
            pass

    if not message_url:
        print_error(f"Could not find message URL for workflow {workflow_id}. Is the session still running?")
        raise typer.Exit(1)

    try:
        client.send_message(message_url, message)
        console.print("[green]Message sent.[/green]")
    except Exception as e:
        print_error(f"Failed to send message: {e}")
        raise typer.Exit(1)
