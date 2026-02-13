"""Shared variable parsing and display for CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
from rich.table import Table

from simplex.cli.output import console, print_error


def parse_variables(
    var_list: list[str] | None = None,
    vars_json: str | None = None,
) -> dict[str, Any] | None:
    """Parse variables from --var key=value pairs and/or --vars JSON/file.

    Supports three input modes (can be combined):
      --var key=value          Individual key=value pairs (repeatable)
      --vars '{"key":"val"}'   Inline JSON string
      --vars vars.json         Path to a JSON file

    When both --var and --vars are provided, they are merged (--var wins on conflict).
    """
    result: dict[str, Any] = {}

    # Parse --vars (JSON string or file path)
    if vars_json:
        # Check if it's a file path
        path = Path(vars_json)
        if path.exists() and path.is_file():
            try:
                data = json.loads(path.read_text())
            except json.JSONDecodeError as e:
                print_error(f"Invalid JSON in {vars_json}: {e}")
                raise typer.Exit(1)
        else:
            # Try to parse as inline JSON
            try:
                data = json.loads(vars_json)
            except json.JSONDecodeError:
                print_error(f"--vars must be a JSON string or path to a .json file. Got: {vars_json}")
                raise typer.Exit(1)

        if not isinstance(data, dict):
            print_error("--vars JSON must be an object (key-value pairs)")
            raise typer.Exit(1)

        result.update(data)

    # Parse --var key=value pairs (override --vars on conflict)
    if var_list:
        for item in var_list:
            if "=" not in item:
                print_error(f"Invalid variable format: '{item}'. Use key=value.")
                raise typer.Exit(1)
            key, value = item.split("=", 1)
            result[key] = value

    return result if result else None


def display_variable_schema(variables: list[dict[str, Any]]) -> None:
    """Render a workflow's variable definitions as a Rich table."""
    if not variables:
        console.print("[dim]No variables defined for this workflow.[/dim]")
        return

    table = Table(title="Variables", show_lines=True)
    table.add_column("Name", style="bold cyan", no_wrap=True)
    table.add_column("Type", style="yellow", no_wrap=True)
    table.add_column("Required", no_wrap=True)
    table.add_column("Default", style="dim")
    table.add_column("Allowed Values", style="dim")

    for var in variables:
        name = var.get("name", "?")
        var_type = var.get("type", "string")
        required = var.get("required", False)
        default = var.get("defaultValue")
        enum_values = var.get("enumValues")

        req_str = "[green]yes[/green]" if required else "[dim]no[/dim]"
        default_str = json.dumps(default) if default is not None else ""
        enum_str = ", ".join(str(v) for v in enum_values) if enum_values else ""

        table.add_row(name, var_type, req_str, default_str, enum_str)

    console.print(table)
