"""Simplex CLI entry point."""

from __future__ import annotations

import typer

from simplex.cli import auth, connect, editor, run
from simplex.cli.sessions import app as sessions_app
from simplex.cli.workflows import app as workflows_app

app = typer.Typer(
    name="simplex",
    help="Simplex CLI — manage workflows and sessions from the terminal.",
    no_args_is_help=True,
)

app.add_typer(workflows_app, name="workflows")
app.add_typer(sessions_app, name="sessions")


def _version_callback(value: bool) -> None:
    if value:
        from simplex import __version__

        typer.echo(f"simplex {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True, help="Show version and exit."
    ),
) -> None:
    pass


app.command("login")(auth.login)
app.command("whoami")(auth.whoami)
app.command("logout")(auth.logout)
app.command("run")(run.run)
app.command("pause")(run.pause)
app.command("resume")(run.resume)
app.command("connect")(connect.connect)
app.command("editor")(editor.editor)

if __name__ == "__main__":
    app()
