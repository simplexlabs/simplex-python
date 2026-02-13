"""Send command — send a message to a running session's browser agent."""

from __future__ import annotations

import typer

from simplex.cli.config import make_client_kwargs
from simplex.cli.output import console, print_error


def send(
    session_id: str = typer.Argument(help="Session ID to send a message to"),
    message: str = typer.Argument(help="Message to send to the browser agent"),
) -> None:
    """Send a message to a running session's browser agent."""
    from simplex import SimplexClient, SimplexError

    try:
        client = SimplexClient(**make_client_kwargs())
    except (SimplexError, ValueError) as e:
        print_error(str(e))
        raise typer.Exit(1)

    # Look up session to get logs_url, derive message_url
    try:
        status = client.get_session_status(session_id)
        logs_url = status.get("logs_url", "")
        if not logs_url:
            print_error(f"No logs_url found for session {session_id}")
            raise typer.Exit(1)
    except SimplexError as e:
        print_error(f"Failed to look up session: {e}")
        raise typer.Exit(1)

    if "/stream" not in logs_url:
        print_error("Cannot derive message URL from session")
        raise typer.Exit(1)

    message_url = logs_url.rsplit("/stream", 1)[0] + "/message"

    try:
        client.send_message(message_url, message)
        console.print(f"[green]Message sent.[/green]")
    except Exception as e:
        print_error(f"Failed to send message: {e}")
        raise typer.Exit(1)
