"""dqt CLI entry point."""

import typer

from dqt_cli.commands.dashboard import dashboard_command
from dqt_cli.commands.demo import reset_command, seed_command
from dqt_cli.commands.list_detectors import list_detectors_command
from dqt_cli.commands.report import report_command
from dqt_cli.commands.run import run_command
from dqt_cli.commands.wiki import wiki_app

app = typer.Typer(name="dqt", help="dqt data quality CLI", no_args_is_help=True)
app.command("run")(run_command)
app.command("dashboard")(dashboard_command)
app.command("list-detectors")(list_detectors_command)
app.command("report")(report_command)
app.add_typer(wiki_app, name="wiki")

demo_app = typer.Typer(help="Demo data commands")
app.add_typer(demo_app, name="demo")
demo_app.command("seed")(seed_command)
demo_app.command("reset")(reset_command)


@app.command()
def version() -> None:
    """Print dqt library version."""
    import dqt

    typer.echo(dqt.__version__)


if __name__ == "__main__":
    app()
