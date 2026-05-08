"""dqt CLI entry point."""

import typer

app = typer.Typer(name="dqt", help="dqt data quality CLI", no_args_is_help=True)

demo_app = typer.Typer(help="Demo data commands")
app.add_typer(demo_app, name="demo")


@app.command()
def version() -> None:
    """Print dqt library version."""
    import dqt

    typer.echo(dqt.__version__)


@demo_app.command("seed")
def demo_seed() -> None:
    """Seed demo data into the local database."""
    typer.echo("Demo seed not yet implemented.")


@demo_app.command("reset")
def demo_reset() -> None:
    """Reset demo data."""
    typer.echo("Demo reset not yet implemented.")
