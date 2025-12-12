# qBittorrent Manual Cross-Seed

A CLI tool to manually trigger [cross-seed](https://cross-seed.org/) searches for qBittorrent torrents.

## Features

- **Direct Hash Mode**: Pass info hash(es) directly as command-line arguments
- **Interactive Mode**: Connect to qBittorrent and select torrents from a searchable, multi-selectable list
- **Configurable**: All settings via environment variables or `.env` file
- **Logging**: Detailed logging to `/var/logs/qbittorrent-manual-cross-seed/` (Linux) or `%LOCALAPPDATA%\qbittorrent-manual-cross-seed\logs\` (Windows)

## Installation

### Using uv (recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/qbittorrent-manual-cross-seed.git
cd qbittorrent-manual-cross-seed

# Install dependencies and create virtual environment
uv sync

# Run the tool
uv run python main.py
```

### Using pip

```bash
# Clone the repository
git clone https://github.com/yourusername/qbittorrent-manual-cross-seed.git
cd qbittorrent-manual-cross-seed

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

## Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your settings:
   ```env
   # Cross-Seed Configuration
   CROSS_SEED_HOST=127.0.0.1
   CROSS_SEED_PORT=2468
   CROSS_SEED_API_KEY=your_api_key_here

   # qBittorrent Configuration
   QBIT_HOST=127.0.0.1
   QBIT_PORT=8080
   QBIT_USERNAME=admin
   QBIT_PASSWORD=adminadmin
   ```

## Usage

### Interactive Mode

Run without arguments to connect to qBittorrent and select torrents interactively:

```bash
python main.py
```

Use **Space** to select/deselect torrents and **Enter** to confirm.

### Direct Hash Mode

Pass one or more info hashes directly:

```bash
# Single hash
python main.py -i INFOHASH

# Multiple hashes
python main.py -i HASH1 HASH2 HASH3
```

### Options

```
usage: main.py [-h] [-i INFO_HASH [INFO_HASH ...]] [--no-single-episodes] [-v]

Manually trigger cross-seed searches for qBittorrent torrents

options:
  -h, --help            show this help message and exit
  -i INFO_HASH [INFO_HASH ...], --info-hash INFO_HASH [INFO_HASH ...]
                        Info hash(es) to search. Multiple hashes can be provided.
  --no-single-episodes  Exclude single episodes from cross-seed search
  -v, --verbose         Enable verbose output
```

## Examples

```bash
# Search a single torrent by hash
python main.py -i abc123def456

# Search multiple torrents
python main.py -i abc123 def456 ghi789

# Interactive mode (select from qBittorrent)
python main.py

# Exclude single episodes
python main.py --no-single-episodes

# Verbose output
python main.py -v
```

## Development

### Setup

```bash
# Install with dev dependencies
uv sync --dev
```

### Code Formatting

This project uses [Black](https://black.readthedocs.io/) for code formatting:

```bash
# Check formatting
uv run black --check .

# Format code
uv run black .

# Or use uvx to run without installing
uvx black --check .
```

### CI/CD

GitHub Actions automatically checks code formatting on push and pull requests.

## Log Location

- **Linux/macOS**: `/var/logs/qbittorrent-manual-cross-seed/cross-seed.log`
- **Windows**: `%LOCALAPPDATA%\qbittorrent-manual-cross-seed\logs\cross-seed.log`

## License

MIT License - see [LICENSE](LICENSE) for details.
