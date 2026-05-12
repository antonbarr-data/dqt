"""dqt CLI entry point."""

import typer

from dqt_cli.commands.dashboard import dashboard_command
from dqt_cli.commands.demo import reset_command, seed_command
from dqt_cli.commands.healthcheck import healthcheck_command
from dqt_cli.commands.list_detectors import list_detectors_command
from dqt_cli.commands.prometheus import prometheus_command
from dqt_cli.commands.report import report_command
from dqt_cli.commands.run import run_command
from dqt_cli.commands.wiki import wiki_app

app = typer.Typer(name="dqt", help="dqt data quality CLI", no_args_is_help=True)
app.command("run")(run_command)
app.command("dashboard")(dashboard_command)
app.command("healthcheck")(healthcheck_command)
app.command("list-detectors")(list_detectors_command)
app.command("prometheus-exporter")(prometheus_command)
app.command("report")(report_command)
app.add_typer(wiki_app, name="wiki")

demo_app = typer.Typer(help="Demo data commands")
app.add_typer(demo_app, name="demo")
demo_app.command("seed")(seed_command)
demo_app.command("reset")(reset_command)


@app.command()
def version() -> None:
    """Print dqt version, Python version, and platform."""
    import platform
    import sys

    import dqt

    typer.echo(f"dqt {dqt.__version__}")
    typer.echo(f"Python {sys.version.split()[0]}")
    typer.echo(f"Platform {platform.platform()}")


if __name__ == "__main__":
    app()
