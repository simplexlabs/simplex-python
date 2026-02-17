"""Session commands: status, events, logs, download, replay."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import typer

from simplex.cli.config import make_client_kwargs
from simplex.cli.output import console, print_error, print_json, print_kv, print_success, print_table

app = typer.Typer(help="Inspect sessions.")


@app.command("status")
def status(
    session_id: str = typer.Argument(help="Session ID"),
    watch: bool = typer.Option(False, "--watch", "-w", help="Poll until session completes"),
) -> None:
    """Get the status of a session."""
    from simplex import SimplexClient, SimplexError

    try:
        client = SimplexClient(**make_client_kwargs())
        result = client.get_session_status(session_id)
    except SimplexError as e:
        print_error(str(e))
        raise typer.Exit(1)

    _print_status(result)

    if not watch:
        return

    if not result.get("in_progress", False):
        return

    # Poll until complete
    from rich.live import Live
    from rich.spinner import Spinner

    spinner = Spinner("dots", text="Waiting for session to complete...")
    try:
        with Live(spinner, console=console, refresh_per_second=4):
            while True:
                time.sleep(2)
                try:
                    result = client.get_session_status(session_id)
                except SimplexError as e:
                    print_error(str(e))
                    raise typer.Exit(1)
                if not result.get("in_progress", True):
                    break
    except KeyboardInterrupt:
        console.print("\n[yellow]Watch interrupted.[/yellow]")
        raise typer.Exit(0)

    console.print()
    _print_status(result)

    if not result.get("success", False):
        raise typer.Exit(1)


def _print_status(result: dict) -> None:
    """Print session status fields."""
    pairs = [
        ("In Progress", result.get("in_progress", "")),
        ("Success", result.get("success", "")),
        ("Paused", result.get("paused", False)),
    ]
    if result.get("metadata"):
        pairs.append(("Metadata", str(result["metadata"])))
    if result.get("workflow_metadata"):
        pairs.append(("Workflow Metadata", str(result["workflow_metadata"])))
    if result.get("final_message"):
        pairs.append(("Final Message", str(result["final_message"])))
    print_kv(pairs)

    outputs = result.get("scraper_outputs")
    if outputs:
        console.print("\n[bold]Outputs:[/bold]")
        print_json(outputs)

    structured = result.get("structured_output")
    if structured:
        console.print("\n[bold]Structured Output:[/bold]")
        print_json(structured)

    files = result.get("file_metadata")
    if files:
        console.print("\n[bold]Files:[/bold]")
        rows = []
        for f in files:
            size = f.get("file_size", 0)
            if size >= 1_048_576:
                size_str = f"{size / 1_048_576:.1f} MB"
            elif size >= 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size} B"
            rows.append([
                f.get("filename", ""),
                size_str,
                f.get("download_timestamp", ""),
            ])
        print_table(["Filename", "Size", "Downloaded"], rows)


@app.command("events")
def events(
    workflow_id: str = typer.Argument(help="Workflow ID"),
    since: int = typer.Option(0, "--since", "-s", help="Event index to start from"),
    limit: int = typer.Option(100, "--limit", "-l", help="Max events to return"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    """Poll events for a workflow's active session."""
    from simplex import SimplexClient, SimplexError

    try:
        client = SimplexClient(**make_client_kwargs())
    except (SimplexError, ValueError) as e:
        print_error(str(e))
        raise typer.Exit(1)

    # Look up active session to get logs_url
    try:
        active = client.get_workflow_active_session(workflow_id)
        logs_url = active.get("logs_url", "")
    except SimplexError as e:
        print_error(f"Could not find active session: {e}")
        raise typer.Exit(1)

    if not logs_url:
        print_error(f"No active session found for workflow {workflow_id}")
        raise typer.Exit(1)

    try:
        result = client.poll_events(logs_url, since=since, limit=limit)
    except SimplexError as e:
        print_error(str(e))
        raise typer.Exit(1)

    if json_output:
        print(json.dumps(result, indent=2, default=str), flush=True)
        return

    events_list = result.get("events", [])
    next_idx = result.get("next_index", 0)
    total = result.get("total", 0)
    has_more = result.get("has_more", False)

    for event in events_list:
        etype = event.get("event", "")
        if etype == "RunContent":
            content = event.get("content", "")
            if content and content != "SIMPLEX_AGENT_INITIALIZED":
                console.print(content, end="", highlight=False)
        elif etype == "ToolCallStarted":
            tool = event.get("tool", {})
            tool_name = tool.get("tool_name", "unknown") if isinstance(tool, dict) else "unknown"
            console.print(f"  [cyan]>[/cyan] [bold]{tool_name}[/bold]")
        elif etype == "ToolCallCompleted":
            tool = event.get("tool", {})
            if isinstance(tool, dict) and tool.get("tool_call_error"):
                console.print(f"    [red]error: {str(tool.get('content', ''))[:200]}[/red]")
        elif etype == "RunCompleted":
            console.print(f"\n[bold green]Completed[/bold green]")
        elif etype == "RunError":
            console.print(f"\n[bold red]Error:[/bold red] {event.get('content', '')}")
        elif etype == "RunStarted":
            console.print("[dim]Agent started[/dim]\n")

    console.print()
    print_kv([
        ("Next Index", next_idx),
        ("Total", total),
        ("Has More", has_more),
    ])


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
