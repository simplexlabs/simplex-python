"""Authentication commands: login, whoami, logout."""

from __future__ import annotations

import typer

from simplex.cli.config import (
    delete_credentials,
    get_api_key_source,
    save_api_key,
)
from simplex.cli.output import console, print_error, print_kv, print_success


def login() -> None:
    """Authenticate with your Simplex API key."""
    api_key = typer.prompt("Enter your Simplex API key", hide_input=True)
    if not api_key.strip():
        print_error("API key cannot be empty.")
        raise typer.Exit(1)

    # Validate the key by making a test request
    try:
        from simplex import SimplexClient

        client = SimplexClient(api_key=api_key.strip())
        client.search_workflows(workflow_name="__simplex_cli_auth_check__")
    except Exception as e:
        from simplex.errors import AuthenticationError

        if isinstance(e, AuthenticationError):
            print_error("Invalid API key.")
            raise typer.Exit(1)
        # Other errors (network, etc.) are fine — key format is valid

    save_api_key(api_key.strip())
    print_success("Authenticated successfully. Credentials saved to ~/.simplex/credentials")


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
