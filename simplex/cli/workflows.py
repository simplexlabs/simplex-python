"""Workflow commands: list, update."""

from __future__ import annotations

from typing import Optional

import typer

from simplex.cli.config import make_client_kwargs
from simplex.cli.output import print_error, print_json, print_success, print_table

app = typer.Typer(help="Manage workflows.")


@app.command("list")
def list_workflows(
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Filter by workflow name"),
    metadata: Optional[str] = typer.Option(None, "--metadata", "-m", help="Filter by metadata"),
) -> None:
    """List workflows matching the given filters."""
    if name is None and metadata is None:
        print_error("At least one of --name or --metadata is required.")
        raise typer.Exit(1)

    from simplex import SimplexClient, SimplexError

    try:
        client = SimplexClient(**make_client_kwargs())
        result = client.search_workflows(workflow_name=name, metadata=metadata)
    except SimplexError as e:
        print_error(str(e))
        raise typer.Exit(1)

    workflows = result.get("workflows", [])
    if not workflows:
        print_error("No workflows found.")
        raise typer.Exit(0)

    rows = []
    for wf in workflows:
        rows.append([
            wf.get("workflow_id", ""),
            wf.get("workflow_name", ""),
            wf.get("metadata", ""),
        ])
    print_table(["ID", "Name", "Metadata"], rows)


@app.command("update")
def update_workflow(
    workflow_id: str = typer.Argument(help="Workflow ID to update"),
    metadata: str = typer.Option(..., "--metadata", "-m", help="New metadata value"),
) -> None:
    """Update a workflow's metadata."""
    from simplex import SimplexClient, SimplexError

    try:
        client = SimplexClient(**make_client_kwargs())
        result = client.update_workflow_metadata(workflow_id=workflow_id, metadata=metadata)
    except SimplexError as e:
        print_error(str(e))
        raise typer.Exit(1)

    print_success(f"Workflow {workflow_id} metadata updated.")
