"""Run, pause, and resume commands."""

from __future__ import annotations

import time
from typing import Any, Optional

import typer

from simplex.cli.config import make_client_kwargs
from simplex.cli.output import console, print_error, print_json, print_kv, print_success
from simplex.cli.variables import parse_variables


def run(
    workflow_id: str = typer.Argument(help="Workflow ID to run"),
    vars_json: Optional[str] = typer.Option(None, "--vars", help="Variables as JSON string or path to .json file"),
    metadata: Optional[str] = typer.Option(None, "--metadata", "-m", help="Metadata string"),
    webhook_url: Optional[str] = typer.Option(None, "--webhook-url", help="Webhook URL for status updates"),
    watch: bool = typer.Option(False, "--watch", "-w", help="Poll until completion"),
) -> None:
    """Run a workflow."""
    from simplex import SimplexClient, SimplexError

    variables = parse_variables(vars_json=vars_json)

    try:
        client = SimplexClient(**make_client_kwargs())
        result = client.run_workflow(
            workflow_id=workflow_id,
            variables=variables,
            metadata=metadata,
            webhook_url=webhook_url,
        )
    except SimplexError as e:
        print_error(str(e))
        raise typer.Exit(1)

    session_id = result["session_id"]
    print_kv([
        ("Session ID", session_id),
        ("VNC URL", result.get("vnc_url", "")),
        ("Logs URL", result.get("logs_url", "")),
    ])

    if not watch:
        return

    _watch_session(client, session_id)


def _watch_session(client: Any, session_id: str) -> None:
    """Poll session status until completion with a spinner."""
    from rich.live import Live
    from rich.spinner import Spinner

    from simplex import SimplexError

    console.print()
    spinner = Spinner("dots", text="Waiting for session to complete...")
    try:
        with Live(spinner, console=console, refresh_per_second=4):
            while True:
                try:
                    status = client.get_session_status(session_id)
                except SimplexError as e:
                    print_error(str(e))
                    raise typer.Exit(1)

                if not status.get("in_progress", True):
                    break
                time.sleep(2)
    except KeyboardInterrupt:
        console.print("\n[yellow]Watch interrupted.[/yellow]")
        raise typer.Exit(0)

    console.print()
    success = status.get("success", False)
    if success:
        print_success("Session completed successfully.")
    else:
        print_error("Session failed.")

    print_kv([
        ("Success", status.get("success", "")),
        ("Paused", status.get("paused", False)),
    ])

    outputs = status.get("scraper_outputs")
    if outputs:
        console.print("\n[bold]Outputs:[/bold]")
        print_json(outputs)

    structured = status.get("structured_output")
    if structured:
        console.print("\n[bold]Structured Output:[/bold]")
        print_json(structured)

    if not success:
        raise typer.Exit(1)


def pause(
    session_id: str = typer.Argument(help="Session ID to pause"),
) -> None:
    """Pause a running session."""
    from simplex import SimplexClient, SimplexError

    try:
        client = SimplexClient(**make_client_kwargs())
        result = client.pause(session_id)
    except SimplexError as e:
        print_error(str(e))
        raise typer.Exit(1)

    print_success(f"Session {session_id} paused.")
    if result.get("pause_key"):
        print_kv([("Pause Key", result["pause_key"])])


def resume(
    session_id: str = typer.Argument(help="Session ID to resume"),
) -> None:
    """Resume a paused session."""
    from simplex import SimplexClient, SimplexError

    try:
        client = SimplexClient(**make_client_kwargs())
        result = client.resume(session_id)
    except SimplexError as e:
        print_error(str(e))
        raise typer.Exit(1)

    print_success(f"Session {session_id} resumed.")
    if result.get("pause_type"):
        print_kv([("Pause Type", result["pause_type"])])
