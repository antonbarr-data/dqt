"""dqt list-detectors — print all registered detector slugs."""
from __future__ import annotations

import typer


def list_detectors_command(
    group: str = typer.Option("", "--group", "-g", help="Filter by group (e.g. drift, outliers_uni)."),
    plain: bool = typer.Option(False, "--plain", help="Print slugs only, one per line."),
) -> None:
    """List all registered detector slugs with their group and label."""
    import dqt  # noqa: F401 — triggers detector registration
    from dqt.algorithms._registry import registry
    from dqt.algorithms._scales import STAT_SCALES

    slugs = sorted(registry.slugs())
    if group:
        slugs = [s for s in slugs if registry.get(s).group == group]

    if plain:
        for s in slugs:
            typer.echo(s)
        return

    # grouped table
    rows: list[tuple[str, str, str]] = []
    for s in slugs:
        cls = registry.get(s)
        label = STAT_SCALES[s].plain_english_label if s in STAT_SCALES else ""
        rows.append((cls.group, s, label))

    current_group = ""
    for grp, slug, label in rows:
        if grp != current_group:
            current_group = grp
            typer.echo(f"\n{grp}")
            typer.echo("─" * len(grp))
        pad = 42
        typer.echo(f"  {slug:<{pad}}{label}")

    typer.echo(f"\n{len(slugs)} detector{'s' if len(slugs) != 1 else ''} registered.")
