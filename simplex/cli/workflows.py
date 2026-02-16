"""Workflow commands: list, update, vars, set-vars, outputs, set-outputs."""

from __future__ import annotations

import json
from typing import List, Optional

import typer

from simplex.cli.config import make_client_kwargs
from simplex.cli.output import console, print_error, print_json, print_success, print_table
from simplex.cli.variables import display_variable_schema

VALID_OUTPUT_TYPES = {"string", "number", "boolean", "array", "object", "enum"}

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
        var_obj = {v["name"]: "..." for v in required_vars[:4]}
        import json
        vars_str = json.dumps(var_obj)
        example = f"simplex run {workflow_id[:12]}... --vars '{vars_str}'"
        if len(required_vars) > 4:
            example += f"  # +{len(required_vars) - 4} more required"
        console.print(f"[dim]  {example}[/dim]")
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


@app.command("outputs")
def outputs_command(
    workflow_id: str = typer.Argument(help="Workflow ID"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    """Show the structured output schema for a workflow."""
    from simplex import SimplexClient, SimplexError

    try:
        client = SimplexClient(**make_client_kwargs())
        result = client.get_workflow(workflow_id)
    except SimplexError as e:
        print_error(str(e))
        raise typer.Exit(1)

    workflow = result.get("workflow", result)
    outputs = workflow.get("structured_output", [])
    name = workflow.get("name", workflow_id)

    if json_output:
        print_json(outputs)
        return

    console.print(f"\n[bold]{name}[/bold]\n")

    if not outputs:
        console.print("[dim]No structured outputs defined for this workflow.[/dim]\n")
        return

    rows = []
    for out in outputs:
        out_type = out.get("type", "string")
        desc = out.get("description", "") or ""
        if out_type == "enum":
            vals = out.get("enumValues", [])
            if vals:
                desc = f"[{', '.join(vals)}]" + (f" — {desc}" if desc else "")
        rows.append([out.get("name", ""), out_type, desc])
    print_table(["Name", "Type", "Description"], rows)
    console.print()


VALID_VAR_TYPES = {"string", "number", "boolean", "array", "object", "enum"}


def _parse_var_field(field_str: str) -> dict:
    """Parse a variable spec like 'name:type', 'name!:type' (required), or 'name:enum:a,b,c'.

    A trailing '!' on the name marks it as required:
      email!:string          → required string
      status:enum:a,b,c      → optional enum
      count!:number:Total     → required number with description
    """
    parts = field_str.split(":", 2)
    if len(parts) < 2:
        raise typer.BadParameter(f"Invalid variable format '{field_str}'. Use name:type or name:type:description")

    name = parts[0].strip()
    ftype = parts[1].strip().lower()

    required = name.endswith("!")
    if required:
        name = name[:-1]

    if ftype not in VALID_VAR_TYPES:
        raise typer.BadParameter(f"Invalid type '{ftype}'. Must be one of: {', '.join(sorted(VALID_VAR_TYPES))}")

    var: dict = {"name": name, "type": ftype, "required": required}

    if len(parts) == 3:
        extra = parts[2].strip()
        if ftype == "enum":
            var["enumValues"] = [v.strip() for v in extra.split(",") if v.strip()]
        else:
            var["description"] = extra

    return var


def _parse_field(field_str: str) -> dict:
    """Parse a field spec like 'name:type' or 'name:type:description' or 'name:enum:a,b,c'."""
    parts = field_str.split(":", 2)
    if len(parts) < 2:
        raise typer.BadParameter(f"Invalid field format '{field_str}'. Use name:type or name:type:description")

    name = parts[0].strip()
    ftype = parts[1].strip().lower()

    if ftype not in VALID_OUTPUT_TYPES:
        raise typer.BadParameter(f"Invalid type '{ftype}'. Must be one of: {', '.join(sorted(VALID_OUTPUT_TYPES))}")

    field: dict = {"name": name, "type": ftype}

    if len(parts) == 3:
        extra = parts[2].strip()
        if ftype == "enum":
            field["enumValues"] = [v.strip() for v in extra.split(",") if v.strip()]
        else:
            field["description"] = extra
    return field


@app.command("set-outputs")
def set_outputs(
    workflow_id: str = typer.Argument(help="Workflow ID"),
    field: Optional[List[str]] = typer.Option(None, "--field", "-f", help="Field as name:type or name:type:description (repeatable). Enum: name:enum:val1,val2"),
    file: Optional[str] = typer.Option(None, "--file", help="JSON file with structured output schema"),
    clear: bool = typer.Option(False, "--clear", help="Clear all structured outputs"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON response"),
) -> None:
    """Set the structured output schema for a workflow.

    Examples:

      simplex workflows set-outputs <id> --field title:string --field price:number

      simplex workflows set-outputs <id> --field status:enum:pending,active,closed

      simplex workflows set-outputs <id> --file schema.json

      simplex workflows set-outputs <id> --clear
    """
    from simplex import SimplexClient, SimplexError

    if clear and (field or file):
        print_error("Cannot combine --clear with --field or --file.")
        raise typer.Exit(1)
    if field and file:
        print_error("Cannot combine --field with --file.")
        raise typer.Exit(1)
    if not clear and not field and not file:
        print_error("Provide --field, --file, or --clear.")
        raise typer.Exit(1)

    if clear:
        schema: list = []
    elif file:
        try:
            with open(file) as f:
                schema = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print_error(f"Could not read schema file: {e}")
            raise typer.Exit(1)
        if not isinstance(schema, list):
            print_error("Schema file must contain a JSON array of field objects.")
            raise typer.Exit(1)
    else:
        schema = [_parse_field(f) for f in (field or [])]

    try:
        client = SimplexClient(**make_client_kwargs())
        result = client.update_workflow(workflow_id, structured_output=schema)
    except SimplexError as e:
        print_error(str(e))
        raise typer.Exit(1)

    if json_output:
        print_json(result)
        return

    if clear:
        print_success(f"Cleared structured outputs for workflow {workflow_id}.")
    else:
        print_success(f"Set {len(schema)} structured output(s) for workflow {workflow_id}.")


@app.command("set-vars")
def set_vars(
    workflow_id: str = typer.Argument(help="Workflow ID"),
    field: Optional[List[str]] = typer.Option(None, "--field", "-f", help="Variable as name:type or name!:type (required). Enum: name:enum:val1,val2"),
    file: Optional[str] = typer.Option(None, "--file", help="JSON file with variable schema"),
    clear: bool = typer.Option(False, "--clear", help="Clear all variables"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON response"),
) -> None:
    """Set the variable schema for a workflow.

    Use '!' after the name to mark a variable as required.

    Examples:

      simplex workflows set-vars <id> --field email!:string --field limit:number

      simplex workflows set-vars <id> --field status:enum:pending,active,closed

      simplex workflows set-vars <id> --field query!:string:"Search query to use"

      simplex workflows set-vars <id> --file vars_schema.json

      simplex workflows set-vars <id> --clear
    """
    from simplex import SimplexClient, SimplexError

    if clear and (field or file):
        print_error("Cannot combine --clear with --field or --file.")
        raise typer.Exit(1)
    if field and file:
        print_error("Cannot combine --field with --file.")
        raise typer.Exit(1)
    if not clear and not field and not file:
        print_error("Provide --field, --file, or --clear.")
        raise typer.Exit(1)

    if clear:
        schema: list = []
    elif file:
        try:
            with open(file) as f:
                schema = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print_error(f"Could not read schema file: {e}")
            raise typer.Exit(1)
        if not isinstance(schema, list):
            print_error("Schema file must contain a JSON array of variable objects.")
            raise typer.Exit(1)
    else:
        schema = [_parse_var_field(f) for f in (field or [])]

    try:
        client = SimplexClient(**make_client_kwargs())
        result = client.update_workflow(workflow_id, variables=schema)
    except SimplexError as e:
        print_error(str(e))
        raise typer.Exit(1)

    if json_output:
        print_json(result)
        return

    if clear:
        print_success(f"Cleared variables for workflow {workflow_id}.")
    else:
        print_success(f"Set {len(schema)} variable(s) for workflow {workflow_id}.")
