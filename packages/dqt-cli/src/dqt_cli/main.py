"""dqt CLI entry point."""

import typer

from dqt_cli.commands.dashboard import dashboard_command
from dqt_cli.commands.demo import reset_command, seed_command
from dqt_cli.commands.run import run_command

app = typer.Typer(name="dqt", help="dqt data quality CLI", no_args_is_help=True)
app.command("run")(run_command)
app.command("dashboard")(dashboard_command)

demo_app = typer.Typer(help="Demo data commands")
app.add_typer(demo_app, name="demo")
demo_app.command("seed")(seed_command)
demo_app.command("reset")(reset_command)


@app.command()
def version() -> None:
    """Print dqt library version."""
    import dqt

    typer.echo(dqt.__version__)
