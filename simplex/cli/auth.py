"""Authentication commands: login, whoami, logout."""

from __future__ import annotations

import sys

import typer

from simplex.cli.config import (
    delete_credentials,
    get_api_key_source,
    save_api_key,
)
from simplex.cli.output import console, print_error, print_kv, print_success

API_KEYS_URL = "https://simplex.sh/api-keys"


def _read_api_key(prompt: str = "│  ") -> str:
    """Read an API key from stdin, masking each character with *."""
    import tty
    import termios

    sys.stdout.write(prompt)
    sys.stdout.flush()

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    chars: list[str] = []
    try:
        tty.setraw(fd)
        while True:
            ch = sys.stdin.read(1)
            if ch in ("\r", "\n"):
                sys.stdout.write("\n")
                break
            elif ch in ("\x7f", "\x08"):  # backspace / delete
                if chars:
                    chars.pop()
                    sys.stdout.write("\b \b")
            elif ch == "\x03":  # Ctrl+C
                sys.stdout.write("\n")
                raise KeyboardInterrupt
            elif ch == "\x04":  # Ctrl+D
                sys.stdout.write("\n")
                raise EOFError
            elif ch >= " ":  # printable
                chars.append(ch)
                sys.stdout.write("*")
            sys.stdout.flush()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    return "".join(chars)


def login() -> None:
    """Authenticate with your Simplex API key."""
    console.print()
    console.print("[bold]┌  ⚡ Simplex Login[/bold]")
    console.print("[dim]│[/dim]")
    console.print("[dim]│[/dim]  Please visit the following URL to create a personal API key:")
    console.print("[dim]│[/dim]")
    console.print(f"[dim]●[/dim]  [bold cyan underline]{API_KEYS_URL}[/bold cyan underline]")
    console.print("[dim]│[/dim]")
    console.print("[dim]│[/dim]")
    console.print("[bold]◆[/bold]  Enter your API key")

    try:
        api_key = _read_api_key()
    except (KeyboardInterrupt, EOFError):
        console.print("[dim]│[/dim]")
        console.print("[dim]└[/dim]  [dim]Login cancelled.[/dim]")
        raise typer.Exit(0)

    if not api_key.strip():
        console.print("[dim]│[/dim]")
        console.print("[red]└  API key cannot be empty.[/red]")
        raise typer.Exit(1)

    # Validate the key by making a test request
    try:
        from simplex import SimplexClient

        client = SimplexClient(api_key=api_key.strip())
        client.search_workflows(workflow_name="__simplex_cli_auth_check__")
    except Exception as e:
        from simplex.errors import AuthenticationError

        if isinstance(e, AuthenticationError):
            console.print("[dim]│[/dim]")
            console.print("[red]└  Invalid API key.[/red]")
            raise typer.Exit(1)
        # Other errors (network, etc.) are fine — key format is valid

    save_api_key(api_key.strip())
    console.print("[dim]│[/dim]")
    console.print("[green]└  Authenticated successfully. Credentials saved to ~/.simplex/credentials[/green]")


def whoami() -> None:
    """Show current authentication status."""
    info = get_api_key_source()
    if info is None:
        print_error("Not authenticated. Run 'simplex login' or set SIMPLEX_API_KEY.")
        raise typer.Exit(1)
    masked_key, source = info
    print_kv([("API Key", masked_key), ("Source", source)])


def logout() -> None:
    """Remove saved credentials."""
    if delete_credentials():
        print_success("Credentials removed.")
    else:
        console.print("No credentials file found.")
