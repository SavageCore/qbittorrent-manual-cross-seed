#!/usr/bin/env python3
"""
qBittorrent Manual Cross-Seed

A CLI tool to manually trigger cross-seed searches for qBittorrent torrents.
Supports direct info hash input or interactive torrent selection.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import qbittorrentapi
import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import Button, DataTable, Footer, Header, Input, Static

if TYPE_CHECKING:
    pass

# Load environment variables
load_dotenv()

# Initialize Rich console for non-TUI output
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
            RichHandler(console=console, rich_tracebacks=True, show_path=False),
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
    # curl -sS -X POST "http://127.0.0.1:2468/api/webhook?apikey=c680b3cc92ecf4d466469c7a03ba1e3e2cab0ce9f4d57837" -d "infoHash=696c022cb9371f2893689fe7ba18e9c1f8005fbc" -d "includeSingleEpisodes=true"
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


class TorrentSelectorApp(App):
    """A Textual app to select torrents for cross-seeding."""

    TITLE = "qBittorrent Cross-Seed"
    SHOW_CLOCK = False

    CSS = """
    Screen {
        background: #1a1a1a;
    }

    Header {
        background: #2d2d2d;
        color: #e0e0e0;
    }

    HeaderIcon {
        display: none;
    }

    Footer {
        background: #2d2d2d;
        color: #808080;
    }

    Footer > .footer--key {
        background: #404040;
        color: #4eb5ab;
    }

    Scrollbar {
        background: #2d2d2d;
    }

    ScrollbarSlider {
        color: #4eb5ab;
    }

    #search-container {
        height: auto;
        padding: 0 1;
        background: #2d2d2d;
        layout: horizontal;
    }

    #search-label {
        width: auto;
        height: 1;
        padding: 0 1;
        color: #4eb5ab;
        background: #2d2d2d;
    }

    #search-input {
        width: 1fr;
        height: 1;
        background: #2d2d2d;
        border: none;
        color: #e0e0e0;
        padding: 0;
    }

    #search-input:focus {
        background: #333333;
    }

    #search-input > .input--placeholder {
        color: #606060;
    }

    DataTable {
        height: 100%;
        background: #1a1a1a;
    }

    DataTable > .datatable--header {
        background: #2d2d2d;
        color: #808080;
        text-style: bold;
    }

    DataTable > .datatable--cursor {
        background: #4eb5ab;
        color: #1a1a1a;
    }

    DataTable > .datatable--hover {
        background: #333333;
    }

    DataTable > .datatable--even-row {
        background: #1a1a1a;
    }

    DataTable > .datatable--odd-row {
        background: #222222;
    }

    #status-bar {
        height: auto;
        padding: 1 2;
        background: #2d2d2d;
        color: #808080;
    }

    #button-container {
        height: auto;
        padding: 1 2;
        background: #1a1a1a;
        align: center middle;
    }

    Button {
        margin: 0 1;
        min-width: 20;
    }

    #confirm-btn {
        background: #4eb5ab;
        color: #1a1a1a;
        border: none;
    }

    #confirm-btn:hover {
        background: #5fcfc4;
    }

    #confirm-btn:focus {
        text-style: bold;
    }

    #cancel-btn {
        background: #404040;
        color: #e0e0e0;
        border: none;
    }

    #cancel-btn:hover {
        background: #505050;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("escape", "unfocus_search", "Back"),
        Binding("space", "toggle_select", "Toggle Select", show=True),
        Binding("enter", "confirm", "Confirm Selection", show=True),
        Binding("a", "select_all", "Select All"),
        Binding("n", "select_none", "Select None"),
        Binding("/", "focus_search", "Search"),
        Binding("1", "sort_by_name", "Sort Name"),
        Binding("2", "sort_by_size", "Sort Size"),
        Binding("3", "sort_by_tracker", "Sort Tracker"),
    ]

    def __init__(
        self,
        torrents: list,
        config: dict,
        app_logger: logging.Logger,
        include_single_episodes: bool,
    ):
        super().__init__()
        self._torrents = torrents
        self._filtered_torrents = torrents.copy()
        self._selected_hashes: set = set()
        self._config = config
        self._app_logger = app_logger
        self._include_single_episodes = include_single_episodes
        self._results: list = []
        self._sort_column: str | None = None
        self._sort_reverse: bool = False
        # Build a map of hash -> torrent for size lookups
        self._torrent_map: dict = {t.hash: t for t in torrents}

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("Filter: ", id="search-label"),
            Input(placeholder="type to filter...", id="search-input"),
            id="search-container",
        )
        yield DataTable(id="torrent-table", cursor_type="row")
        yield Static(id="status-bar")
        yield Container(
            Button("Confirm Selection", id="confirm-btn", variant="primary"),
            Button("Cancel", id="cancel-btn", variant="error"),
            id="button-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Set up the table when the app starts."""
        table = self.query_one("#torrent-table", DataTable)
        # Add sortable columns
        table.add_column("Sel", key="sel")
        table.add_column("Name", key="name")
        table.add_column("Size", key="size")
        table.add_column("Tracker", key="tracker")
        self._populate_table()
        self._update_status()
        table.focus()

    def _populate_table(self) -> None:
        """Populate the table with filtered torrents."""
        table = self.query_one("#torrent-table", DataTable)
        table.clear()

        for torrent in self._filtered_torrents:
            size_gb = torrent.size / (1024**3)
            selected = " * " if torrent.hash in self._selected_hashes else "   "
            # Extract tracker hostname
            tracker = torrent.tracker
            if tracker:
                # Parse hostname from tracker URL
                try:
                    parsed = urlparse(tracker)
                    tracker = parsed.hostname or tracker
                except Exception:
                    pass
            else:
                tracker = "-"
            table.add_row(
                selected,
                torrent.name,
                f"{size_gb:.2f} GB",
                tracker,
                key=torrent.hash,
            )

    def _update_status(self) -> None:
        """Update the status bar."""
        status = self.query_one("#status-bar", Static)
        total = len(self._torrents)
        filtered = len(self._filtered_torrents)
        selected = len(self._selected_hashes)

        if filtered < total:
            status.update(f"Showing {filtered}/{total} torrents | {selected} selected")
        else:
            status.update(f"{total} torrents | {selected} selected")

    @on(Input.Changed, "#search-input")
    def filter_torrents(self, event: Input.Changed) -> None:
        """Filter torrents based on search input."""
        query = event.value.lower().strip()

        if query:
            self._filtered_torrents = [
                t for t in self._torrents if query in t.name.lower()
            ]
        else:
            self._filtered_torrents = self._torrents.copy()

        self._populate_table()
        self._update_status()

    @on(DataTable.RowSelected, "#torrent-table")
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        """Toggle selection when a row is clicked/selected."""
        if event.row_key is not None:
            self._toggle_hash(str(event.row_key.value))

    def action_toggle_select(self) -> None:
        """Toggle selection of the current row."""
        table = self.query_one("#torrent-table", DataTable)
        if table.row_count == 0:
            return

        row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        if row_key is not None:
            self._toggle_hash(str(row_key.value))

    def _toggle_hash(self, hash_value: str) -> None:
        """Toggle a hash in the selected set."""
        if hash_value in self._selected_hashes:
            self._selected_hashes.discard(hash_value)
        else:
            self._selected_hashes.add(hash_value)

        # Update the checkbox in the table
        table = self.query_one("#torrent-table", DataTable)
        selected = " * " if hash_value in self._selected_hashes else "   "
        # Get the first column key from the ordered columns list
        first_col_key = list(table.columns.keys())[0]
        table.update_cell(hash_value, first_col_key, selected)
        self._update_status()

    def action_select_all(self) -> None:
        """Select all visible torrents."""
        for torrent in self._filtered_torrents:
            self._selected_hashes.add(torrent.hash)
        self._populate_table()
        self._update_status()

    def action_select_none(self) -> None:
        """Deselect all torrents."""
        self._selected_hashes.clear()
        self._populate_table()
        self._update_status()

    def action_focus_search(self) -> None:
        """Focus the search input."""
        self.query_one("#search-input", Input).focus()

    def action_unfocus_search(self) -> None:
        """Unfocus search and return to table, or quit if already on table."""
        search_input = self.query_one("#search-input", Input)
        if search_input.has_focus:
            # Clear search and return to table
            search_input.value = ""
            self._filtered_torrents = self._torrents.copy()
            self._populate_table()
            self._update_status()
            self.query_one("#torrent-table", DataTable).focus()
        else:
            self.exit([])

    def _sort_by_column(self, column_key: str) -> None:
        """Sort by the given column, toggling direction if same column."""
        # Toggle direction if same column, otherwise reset to ascending
        if self._sort_column == column_key:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_column = column_key
            self._sort_reverse = False

        # Sort the filtered torrents
        if column_key == "name":
            self._filtered_torrents.sort(
                key=lambda t: t.name.lower(), reverse=self._sort_reverse
            )
        elif column_key == "size":
            self._filtered_torrents.sort(
                key=lambda t: t.size, reverse=self._sort_reverse
            )
        elif column_key == "tracker":
            self._filtered_torrents.sort(
                key=lambda t: (t.tracker or "").lower(), reverse=self._sort_reverse
            )
        elif column_key == "sel":
            self._filtered_torrents.sort(
                key=lambda t: t.hash in self._selected_hashes,
                reverse=self._sort_reverse,
            )

        self._populate_table()

    def action_sort_by_name(self) -> None:
        """Sort by name column."""
        self._sort_by_column("name")

    def action_sort_by_size(self) -> None:
        """Sort by size column."""
        self._sort_by_column("size")

    def action_sort_by_tracker(self) -> None:
        """Sort by tracker column."""
        self._sort_by_column("tracker")

    @on(DataTable.HeaderSelected)
    def on_header_selected(self, event: DataTable.HeaderSelected) -> None:
        """Sort table when header is clicked."""
        self._sort_by_column(str(event.column_key))

    def action_confirm(self) -> None:
        """Confirm selection and process torrents."""
        if not self._selected_hashes:
            self.notify("No torrents selected!", severity="warning")
            return

        self._results = list(self._selected_hashes)
        self.exit(self._results)

    @on(Button.Pressed, "#confirm-btn")
    def on_confirm_pressed(self) -> None:
        """Handle confirm button press."""
        self.action_confirm()

    @on(Button.Pressed, "#cancel-btn")
    def on_cancel_pressed(self) -> None:
        """Handle cancel button press."""
        self.exit([])


def run_interactive_mode(
    config: dict, logger: logging.Logger, include_single_episodes: bool
) -> list:
    """Run the interactive TUI for torrent selection."""
    console.print("[bold blue]Connecting to qBittorrent...[/bold blue]")
    client = connect_qbittorrent(config)
    console.print(f"[green]Connected to qBittorrent {client.app.version}[/green]")

    torrents = get_torrents(client)
    if not torrents:
        console.print("[yellow]No torrents found in qBittorrent[/yellow]")
        return []

    console.print(f"[bold]Found {len(torrents)} torrents. Launching selector...[/bold]")

    app = TorrentSelectorApp(torrents, config, logger, include_single_episodes)
    result = app.run()
    return result if result else []


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
        # Interactive mode with Textual TUI
        info_hashes = run_interactive_mode(config, logger, include_single_episodes)

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
