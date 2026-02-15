"""Session commands: status, logs, download, replay."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from simplex.cli.config import list_sessions, make_client_kwargs, remove_session
from simplex.cli.output import console, print_error, print_json, print_kv, print_success, print_table

app = typer.Typer(help="Inspect sessions.")


@app.command("list")
def list_cmd() -> None:
    """List saved sessions."""
    sessions = list_sessions()
    if not sessions:
        console.print("[dim]No saved sessions.[/dim]")
        raise typer.Exit(0)

    rows = []
    for s in sessions:
        wid = s.get("workflow_id", "")
        rows.append([
            s.get("name", ""),
            wid[:12],
            s.get("url", ""),
        ])
    print_table(["Name", "Workflow ID", "URL"], rows)


@app.command("remove")
def remove(
    target: str = typer.Argument(help="Workflow name or ID prefix"),
) -> None:
    """Remove a saved session."""
    from simplex.cli.config import resolve_session

    session = resolve_session(target)
    if not session:
        print_error(f"No session matching '{target}'")
        raise typer.Exit(1)

    wid = session["workflow_id"]
    name = session.get("name", wid[:8])
    remove_session(wid)
    print_success(f"Removed session '{name}' ({wid[:8]}...)")


@app.command("status")
def status(
    session_id: str = typer.Argument(help="Session ID"),
) -> None:
    """Get the status of a session."""
    from simplex import SimplexClient, SimplexError

    try:
        client = SimplexClient(**make_client_kwargs())
        result = client.get_session_status(session_id)
    except SimplexError as e:
        print_error(str(e))
        raise typer.Exit(1)

    pairs = [
        ("In Progress", result.get("in_progress", "")),
        ("Success", result.get("success", "")),
        ("Paused", result.get("paused", False)),
    ]
    if result.get("metadata"):
        pairs.append(("Metadata", str(result["metadata"])))
    print_kv(pairs)

    outputs = result.get("scraper_outputs")
    if outputs:
        from rich.console import Console

        Console().print("\n[bold]Outputs:[/bold]")
        print_json(outputs)

    structured = result.get("structured_output")
    if structured:
        from rich.console import Console

        Console().print("\n[bold]Structured Output:[/bold]")
        print_json(structured)


@app.command("logs")
def logs(
    session_id: str = typer.Argument(help="Session ID"),
) -> None:
    """Retrieve session logs."""
    from simplex import SimplexClient, SimplexError

    try:
        client = SimplexClient(**make_client_kwargs())
        result = client.retrieve_session_logs(session_id)
    except SimplexError as e:
        print_error(str(e))
        raise typer.Exit(1)

    if result is None:
        print_error("Session is still running — logs not yet available.")
        raise typer.Exit(1)

    print_json(result)


@app.command("download")
def download(
    session_id: str = typer.Argument(help="Session ID"),
    filename: Optional[str] = typer.Option(None, "--filename", "-f", help="Specific file to download"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output path"),
) -> None:
    """Download files from a session."""
    from simplex import SimplexClient, SimplexError

    try:
        client = SimplexClient(**make_client_kwargs())
        data = client.download_session_files(session_id, filename=filename)
    except SimplexError as e:
        print_error(str(e))
        raise typer.Exit(1)

    if output:
        out_path = Path(output)
    elif filename:
        out_path = Path(filename)
    else:
        out_path = Path(f"{session_id}_files.zip")

    out_path.write_bytes(data)
    print_success(f"Downloaded to {out_path}")


@app.command("replay")
def replay(
    session_id: str = typer.Argument(help="Session ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output path"),
) -> None:
    """Download session replay video."""
    from simplex import SimplexClient, SimplexError

    try:
        client = SimplexClient(**make_client_kwargs())
        data = client.retrieve_session_replay(session_id)
    except SimplexError as e:
        print_error(str(e))
        raise typer.Exit(1)

    out_path = Path(output) if output else Path(f"{session_id}_replay.mp4")
    out_path.write_bytes(data)
    print_success(f"Replay saved to {out_path}")
