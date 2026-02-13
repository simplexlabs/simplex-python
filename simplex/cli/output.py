"""Rich formatting helpers for CLI output."""

from __future__ import annotations

import json
import sys
from typing import Any

from rich.console import Console
from rich.table import Table

console = Console()
err_console = Console(stderr=True)


def print_error(message: str) -> None:
    err_console.print(f"[red]Error:[/red] {message}")


def print_success(message: str) -> None:
    console.print(f"[green]{message}[/green]")


def print_json(data: Any) -> None:
    console.print_json(json.dumps(data, indent=2, default=str))


def print_kv(pairs: list[tuple[str, Any]]) -> None:
    """Print key-value pairs as a two-column table."""
    table = Table(show_header=False, show_edge=False, pad_edge=False)
    table.add_column(style="bold cyan", no_wrap=True)
    table.add_column()
    for key, value in pairs:
        table.add_row(key, str(value))
    console.print(table)


def print_table(columns: list[str], rows: list[list[str]]) -> None:
    """Print a table with headers."""
    table = Table()
    for col in columns:
        table.add_column(col, style="bold")
    for row in rows:
        table.add_row(*row)
    console.print(table)
