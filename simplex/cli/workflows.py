"""Workflow commands: list, update, vars."""

from __future__ import annotations

from typing import Optional

import typer

from simplex.cli.config import make_client_kwargs
from simplex.cli.output import console, print_error, print_json, print_success, print_table
from simplex.cli.variables import display_variable_schema

app = typer.Typer(help="Manage workflows.")


@app.command("list")
def list_workflows(
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Filter by workflow name"),
    metadata: Optional[str] = typer.Option(None, "--metadata", "-m", help="Filter by metadata"),
) -> None:
    """List workflows. Shows all workflows if no filters given."""
    from simplex import SimplexClient, SimplexError

    try:
        client = SimplexClient(**make_client_kwargs())
        result = client.search_workflows(workflow_name=name, metadata=metadata)
    except SimplexError as e:
        print_error(str(e))
        raise typer.Exit(1)

    workflows = result.get("workflows", [])
    if not workflows:
        console.print("[dim]No workflows found.[/dim]")
        raise typer.Exit(0)

    rows = []
    for wf in workflows:
        rows.append([
            wf.get("workflow_id", "")[:12],
            wf.get("workflow_name", ""),
            wf.get("metadata", "") or "",
        ])
    print_table(["ID", "Name", "Metadata"], rows)


@app.command("vars")
def vars_command(
    workflow_id: str = typer.Argument(help="Workflow ID"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    """Show the variable schema for a workflow."""
    from simplex import SimplexClient, SimplexError

    try:
        client = SimplexClient(**make_client_kwargs())
        result = client.get_workflow(workflow_id)
    except SimplexError as e:
        print_error(str(e))
        raise typer.Exit(1)

    workflow = result.get("workflow", result)
    variables = workflow.get("variables", [])
    name = workflow.get("name", workflow_id)

    if json_output:
        print_json(variables)
        return

    console.print(f"\n[bold]{name}[/bold]\n")

    if not variables:
        console.print("[dim]No variables defined for this workflow.[/dim]")
        return

    display_variable_schema(variables)

    # Print example usage
    required_vars = [v for v in variables if v.get("required")]
    if required_vars:
        console.print(f"\n[dim]Example:[/dim]")
        parts = [f"simplex run {workflow_id[:12]}..."]
        for v in required_vars[:4]:
            parts.append(f'--var {v["name"]}=...')
        if len(required_vars) > 4:
            parts.append(f"  [dim]# +{len(required_vars) - 4} more required[/dim]")
        console.print(f"[dim]  {' '.join(parts)}[/dim]")
    console.print()


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
