"""Authentication commands: login, whoami, logout."""

from __future__ import annotations

import sys
from typing import Optional

import typer

from simplex.cli.config import (
    delete_credentials,
    get_api_key_source,
    resolve_base_url,
    save_api_key,
)
from simplex.cli.output import console, print_error, print_success, print_kv

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


def login(
    api_key: Optional[str] = typer.Option(None, "--api-key", help="API key (skip browser login)"),
) -> None:
    """Log in to Simplex."""
    if api_key:
        _login_with_key(api_key)
        return
    _login_with_browser()


def _login_with_browser() -> None:
    """Browser-based login flow."""
    import webbrowser
    import time

    import requests
    from rich.live import Live
    from rich.spinner import Spinner

    base_url = resolve_base_url() or "https://api.simplex.sh"

    # Step 1: Request a ticket
    try:
        resp = requests.post(f"{base_url}/cli-auth/request", timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print_error(f"Could not connect to Simplex: {e}")
        console.print("[dim]Falling back to manual API key entry.[/dim]")
        _login_manual()
        return

    ticket_id = data["ticket_id"]
    poll_token = data["poll_token"]
    auth_url = data["auth_url"]

    # Step 2: Open browser
    console.print()
    console.print("[bold]Opening browser to log in...[/bold]")
    console.print(f"[dim]If the browser doesn't open, visit:[/dim]")
    console.print(f"[bold cyan underline]{auth_url}[/bold cyan underline]")
    console.print()
    webbrowser.open(auth_url)

    # Step 3: Poll with spinner
    spinner = Spinner("dots", text="Waiting for browser authorization...")
    timeout = 300  # 5 minutes
    start = time.time()

    try:
        with Live(spinner, console=console, refresh_per_second=4):
            while time.time() - start < timeout:
                try:
                    poll_resp = requests.get(
                        f"{base_url}/cli-auth/poll",
                        params={"ticket_id": ticket_id, "poll_token": poll_token},
                        timeout=10,
                    )
                    if poll_resp.status_code == 200:
                        poll_data = poll_resp.json()
                        if poll_data["status"] == "authorized":
                            save_api_key(poll_data["api_key"])
                            break
                except Exception:
                    pass  # Network blip, retry
                time.sleep(2)
            else:
                print_error("Login timed out. Please try again.")
                raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[dim]Login cancelled.[/dim]")
        raise typer.Exit(0)

    print_success("Logged in successfully! Credentials saved to ~/.simplex/credentials")


def _login_manual() -> None:
    """Fallback: manual API key entry (old flow)."""
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

    _validate_and_save_key(api_key.strip())


def _login_with_key(api_key: str) -> None:
    """Direct API key login (--api-key flag)."""
    _validate_and_save_key(api_key.strip())


def _validate_and_save_key(api_key: str) -> None:
    """Validate an API key and save it."""
    try:
        from simplex import SimplexClient

        client = SimplexClient(api_key=api_key)
        client.search_workflows(workflow_name="__simplex_cli_auth_check__")
    except Exception as e:
        from simplex.errors import AuthenticationError

        if isinstance(e, AuthenticationError):
            print_error("Invalid API key.")
            raise typer.Exit(1)
        # Other errors (network, etc.) are fine — key format is valid

    save_api_key(api_key)
    print_success("Logged in successfully! Credentials saved to ~/.simplex/credentials")


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
