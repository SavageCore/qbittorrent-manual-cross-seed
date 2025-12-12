#!/usr/bin/env python3
"""
qBittorrent Manual Cross-Seed

A CLI tool to manually trigger cross-seed searches for qBittorrent torrents.
Supports direct info hash input or interactive torrent selection.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

import questionary
import qbittorrentapi
import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

# Load environment variables
load_dotenv()

# Initialize Rich console
console = Console()


def setup_logging() -> logging.Logger:
    """Configure logging to file and console."""
    # Determine log directory based on OS
    if sys.platform == "win32":
        log_dir = (
            Path(os.environ.get("LOCALAPPDATA", "."))
            / "qbittorrent-manual-cross-seed"
            / "logs"
        )
    else:
        log_dir = Path("/var/logs/qbittorrent-manual-cross-seed")

    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "cross-seed.log"

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            RichHandler(console=console, rich_tracebacks=True),
        ],
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Logging to: {log_file}")
    return logger


def get_config() -> dict:
    """Load configuration from environment variables."""
    config = {
        "cross_seed_host": os.environ.get("CROSS_SEED_HOST", "127.0.0.1"),
        "cross_seed_port": os.environ.get("CROSS_SEED_PORT", "2468"),
        "cross_seed_api_key": os.environ.get("CROSS_SEED_API_KEY", ""),
        "qbit_host": os.environ.get("QBIT_HOST", "127.0.0.1"),
        "qbit_port": os.environ.get("QBIT_PORT", "8080"),
        "qbit_username": os.environ.get("QBIT_USERNAME", "admin"),
        "qbit_password": os.environ.get("QBIT_PASSWORD", "adminadmin"),
    }

    if not config["cross_seed_api_key"]:
        console.print("[red]Error: CROSS_SEED_API_KEY is required[/red]")
        sys.exit(1)

    return config


def connect_qbittorrent(config: dict) -> qbittorrentapi.Client:
    """Connect to qBittorrent WebUI."""
    try:
        client = qbittorrentapi.Client(
            host=config["qbit_host"],
            port=config["qbit_port"],
            username=config["qbit_username"],
            password=config["qbit_password"],
        )
        client.auth_log_in()
        return client
    except qbittorrentapi.LoginFailed as e:
        console.print(f"[red]Failed to login to qBittorrent: {e}[/red]")
        sys.exit(1)
    except qbittorrentapi.APIConnectionError as e:
        console.print(f"[red]Failed to connect to qBittorrent: {e}[/red]")
        sys.exit(1)


def trigger_cross_seed(
    config: dict,
    info_hash: str,
    logger: logging.Logger,
    include_single_episodes: bool = True,
) -> bool:
    """Trigger cross-seed search for a given info hash."""
    url = f"http://{config['cross_seed_host']}:{config['cross_seed_port']}/api/webhook"
    params = {"apikey": config["cross_seed_api_key"]}
    data = {
        "infoHash": info_hash,
        "includeSingleEpisodes": str(include_single_episodes).lower(),
    }

    try:
        response = requests.post(url, params=params, data=data, timeout=30)
        response.raise_for_status()
        logger.info(f"Successfully triggered cross-seed for: {info_hash}")
        return True
    except requests.RequestException as e:
        logger.error(f"Failed to trigger cross-seed for {info_hash}: {e}")
        return False


def get_torrents(client: qbittorrentapi.Client) -> list:
    """Get all torrents from qBittorrent, sorted by name."""
    torrents = client.torrents_info()
    return sorted(torrents, key=lambda t: t.name.lower())


def display_torrents(torrents: list) -> None:
    """Display torrents in a table format."""
    table = Table(title="qBittorrent Torrents")
    table.add_column("Name", style="cyan", no_wrap=False)
    table.add_column("Size", style="green")
    table.add_column("State", style="yellow")
    table.add_column("Hash", style="dim")

    for torrent in torrents[:20]:  # Show first 20 for preview
        size_gb = torrent.size / (1024**3)
        table.add_row(
            torrent.name[:60] + "..." if len(torrent.name) > 60 else torrent.name,
            f"{size_gb:.2f} GB",
            torrent.state,
            torrent.hash[:16] + "...",
        )

    console.print(table)


def select_torrents(torrents: list) -> list:
    """Interactive torrent selection with search."""
    choices = [
        questionary.Choice(
            title=(
                f"{t.name[:80]}... ({t.size / (1024**3):.2f} GB)"
                if len(t.name) > 80
                else f"{t.name} ({t.size / (1024**3):.2f} GB)"
            ),
            value=t.hash,
        )
        for t in torrents
    ]

    selected = questionary.checkbox(
        "Select torrents to cross-seed (use space to select, enter to confirm):",
        choices=choices,
    ).ask()

    return selected if selected else []


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Manually trigger cross-seed searches for qBittorrent torrents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -i INFOHASH                  # Search single torrent by hash
  %(prog)s -i HASH1 HASH2 HASH3         # Search multiple torrents
  %(prog)s                              # Interactive mode: select from qBittorrent
  %(prog)s --no-single-episodes         # Exclude single episodes from search
        """,
    )
    parser.add_argument(
        "-i",
        "--info-hash",
        nargs="+",
        help="Info hash(es) to search. Multiple hashes can be provided.",
    )
    parser.add_argument(
        "--no-single-episodes",
        action="store_true",
        help="Exclude single episodes from cross-seed search",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load config
    config = get_config()

    include_single_episodes = not args.no_single_episodes
    info_hashes = []

    if args.info_hash:
        # Direct info hash mode
        info_hashes = args.info_hash
        logger.info(f"Processing {len(info_hashes)} info hash(es) from command line")
    else:
        # Interactive mode - connect to qBittorrent and select torrents
        console.print("[bold blue]Connecting to qBittorrent...[/bold blue]")
        client = connect_qbittorrent(config)
        console.print(f"[green]Connected to qBittorrent {client.app.version}[/green]")

        torrents = get_torrents(client)
        if not torrents:
            console.print("[yellow]No torrents found in qBittorrent[/yellow]")
            sys.exit(0)

        console.print(f"\n[bold]Found {len(torrents)} torrents[/bold]\n")

        # Interactive selection
        info_hashes = select_torrents(torrents)

        if not info_hashes:
            console.print("[yellow]No torrents selected[/yellow]")
            sys.exit(0)

    # Process selected torrents
    console.print(f"\n[bold]Processing {len(info_hashes)} torrent(s)...[/bold]\n")

    success_count = 0
    fail_count = 0

    for info_hash in info_hashes:
        console.print(f"  Triggering cross-seed for: [cyan]{info_hash}[/cyan]")
        if trigger_cross_seed(config, info_hash, logger, include_single_episodes):
            success_count += 1
            console.print("    [green]✓ Success[/green]")
        else:
            fail_count += 1
            console.print("    [red]✗ Failed[/red]")

    # Summary
    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  [green]Successful: {success_count}[/green]")
    if fail_count > 0:
        console.print(f"  [red]Failed: {fail_count}[/red]")

    logger.info(f"Completed: {success_count} successful, {fail_count} failed")


if __name__ == "__main__":
    main()
