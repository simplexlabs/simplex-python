"""Editor command — create a workflow + editor session."""

from __future__ import annotations

import json
from typing import Any, Optional

import typer
from rich.panel import Panel
from rich.text import Text

from simplex.cli.config import make_client_kwargs, save_current_session
from simplex.cli.output import console, print_error
from simplex.cli.variables import parse_variables


def editor(
    name: str = typer.Option(..., "--name", "-n", help="Workflow name"),
    url: str = typer.Option(..., "--url", "-u", help="Starting URL"),
    vars_json: Optional[str] = typer.Option(None, "--vars", help="Variables as JSON string or path to .json file"),
    json_output: bool = typer.Option(False, "--json", help="Output session info as JSON"),
) -> None:
    """Create a workflow and start an editor session."""
    from simplex import SimplexClient, SimplexError

    test_data = parse_variables(vars_json=vars_json)

    try:
        client = SimplexClient(**make_client_kwargs())
    except (SimplexError, ValueError) as e:
        print_error(str(e))
        raise typer.Exit(1)

    # Start editor session (creates workflow + session)
    if not json_output:
        console.print()
        with console.status("[bold]Starting editor session...[/bold]", spinner="dots"):
            try:
                result = client.start_editor_session(name=name, url=url, test_data=test_data)
            except SimplexError as e:
                print_error(str(e))
                raise typer.Exit(1)
    else:
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

    # Pin this as the current session
    save_current_session(workflow_id, session_id)

    workflow_link = f"https://simplex.sh/workflow/{workflow_id}"

    if json_output:
        print(json.dumps({
            "type": "SessionStarted",
            "session_id": session_id,
            "workflow_id": workflow_id,
            "vnc_url": vnc_url,
            "logs_url": logs_url,
            "message_url": message_url,
        }), flush=True)
    else:
        # Build the session info panel
        info = Text()
        info.append("Workflow  ", style="bold cyan")
        info.append(workflow_link, style="underline blue link " + workflow_link)
        info.append("\n")
        info.append("Session   ", style="bold cyan")
        info.append(session_id, style="dim")
        if vnc_url:
            info.append("\n")
            info.append("VNC       ", style="bold cyan")
            info.append(vnc_url, style="dim")

        panel = Panel(
            info,
            title="[bold green]Session Started[/bold green]",
            subtitle="[dim]Use 'simplex send' and 'simplex connect'[/dim]",
            border_style="green",
            padding=(1, 2),
        )
        console.print(panel)
        console.print()
