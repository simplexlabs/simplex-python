"""Send command — send a message to a running session's browser agent."""

from __future__ import annotations

import typer

from simplex.cli.config import make_client_kwargs
from simplex.cli.output import console, print_error


def _resolve_workflow_id(client, target: str) -> str:
    """Resolve a target (workflow name or ID) to a workflow ID via the API."""
    # If it looks like a UUID, use it directly
    if len(target) >= 32 or "-" in target:
        return target

    # Search by name
    try:
        result = client.search_workflows(workflow_name=target)
        workflows = result.get("workflows", [])
        if workflows:
            wf = workflows[0]
            console.print(f"[dim]{wf.get('workflow_name', '')} ({wf['workflow_id'][:8]}...)[/dim]")
            return wf["workflow_id"]
    except Exception:
        pass

    # Fall back to treating it as an ID
    return target


def send(
    target: str = typer.Argument(help="Workflow name or ID"),
    message: str = typer.Argument(help="Message to send to the browser agent"),
) -> None:
    """Send a message to a running session's browser agent."""
    from simplex import SimplexClient, SimplexError

    try:
        client = SimplexClient(**make_client_kwargs())
    except (SimplexError, ValueError) as e:
        print_error(str(e))
        raise typer.Exit(1)

    workflow_id = _resolve_workflow_id(client, target)

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
        print_error(f"Could not find message URL for '{target}'. Is the session still running?")
        raise typer.Exit(1)

    try:
        client.send_message(message_url, message)
        console.print("[green]Message sent.[/green]")
    except Exception as e:
        print_error(f"Failed to send message: {e}")
        raise typer.Exit(1)
