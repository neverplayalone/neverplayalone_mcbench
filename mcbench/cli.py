"""`mcbench` CLI entry point."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from . import server as server_mod
from .replay_tool import export_mcpr

console = Console()


@click.group()
def main() -> None:
    """Benchmark mineflayer-style Minecraft agents."""


@main.group()
def server() -> None:
    """Manage the ephemeral Paper server."""


@server.command("up")
def server_up() -> None:
    console.log("Bringing server up…")
    try:
        server_mod.up(wait=True)
    except RuntimeError as e:
        raise click.ClickException(str(e)) from e
    console.log("[green]Server is ready.[/]")


@server.command("down")
def server_down() -> None:
    console.log("Tearing server down…")
    try:
        server_mod.down()
    except RuntimeError as e:
        raise click.ClickException(str(e)) from e


@server.command("reset")
def server_reset() -> None:
    console.log("Resetting world (server will restart)…")
    try:
        server_mod.reset_world()
        server_mod.up(wait=True)
    except RuntimeError as e:
        raise click.ClickException(str(e)) from e
    console.log("[green]Fresh world ready.[/]")


@main.group()
def replay() -> None:
    """Manage visual replay artifacts."""


@replay.command("export-mcpr")
@click.argument("packet_log", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output .mcpr path (default: recording.mcpr next to the packet log)",
)
def replay_export_mcpr(packet_log: Path, output: Path | None) -> None:
    """Export a packet log to a ReplayMod .mcpr file."""
    try:
        mcpr = export_mcpr(packet_log, output=output)
    except RuntimeError as e:
        raise click.ClickException(str(e)) from e
    console.log(f"[green]ReplayMod file written:[/] {mcpr}")


@main.command("resource-gather")
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, path_type=Path),
    default=Path("resource_base.yaml"),
    help="Base resource-gathering config for server, kit, and duration.",
)
@click.option(
    "--catalog",
    "catalog_path",
    type=click.Path(exists=True, path_type=Path),
    default=Path("resource_catalog.yaml"),
    help="Resource catalog used to generate the shared challenge.",
)
@click.option(
    "--agent",
    "agent_assignments",
    multiple=True,
    required=True,
    help="Miner assignment as NAME=PATH or PATH. Repeat once per miner.",
)
@click.option("--seed", type=int, required=True, help="Deterministic challenge seed.")
@click.option("--challenge-id", default=None, help="Optional explicit challenge id.")
@click.option("--base-game-port", type=int, default=25665)
@click.option("--base-rcon-port", type=int, default=25675)
@click.option("--out", "out_dir", type=click.Path(path_type=Path), default=None)
@click.option("--record/--no-record", default=False, help="Record every miner slot.")
@click.option(
    "--keep-slots/--no-keep-slots",
    default=False,
    help="Keep per-slot world copies after the batch (for debugging). By default "
    "they are deleted; scores, traces, recordings, and world_template are kept.",
)
def resource_gather_cmd(
    config_path: Path,
    catalog_path: Path,
    agent_assignments: tuple[str, ...],
    seed: int,
    challenge_id: str | None,
    base_game_port: int,
    base_rcon_port: int,
    out_dir: Path | None,
    record: bool,
    keep_slots: bool,
) -> None:
    """Run one generated resource-gathering challenge across miner slots."""
    from .competition import load_resource_competition_config
    from .resource_batch import (
        create_evaluation_batch,
        load_resource_catalog,
        parse_agent_assignment,
        run_evaluation_batch,
    )

    try:
        agents = [parse_agent_assignment(raw) for raw in agent_assignments]
        cfg = load_resource_competition_config(config_path)
        catalog = load_resource_catalog(catalog_path)
        batch = create_evaluation_batch(
            catalog=catalog,
            base_cfg=cfg,
            agents=agents,
            seed=seed,
            challenge_id=challenge_id,
            output_dir=out_dir,
            base_game_port=base_game_port,
            base_rcon_port=base_rcon_port,
        )
        report = run_evaluation_batch(batch, record=record, keep_slots=keep_slots)
    except (ValueError, RuntimeError) as e:
        raise click.ClickException(str(e)) from e

    console.log(f"[bold green]Batch complete:[/] {batch.output_dir}")
    for result in report["results"]:
        if "error" in result:
            console.log(
                f"[red]{result['miner']}[/] slot {result['slot']} failed: {result['error']}"
            )
        else:
            console.log(
                f"{result['miner']} slot {result['slot']}: "
                f"{result['score']:.1f} / {result['max_score']:.1f}"
            )


if __name__ == "__main__":
    main()
