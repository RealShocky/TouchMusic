"""Writable data paths for both source checkouts and installed wheels."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_CHECKOUT = (ROOT / 'Setup.cmd').is_file() and (ROOT / 'touchmusic').is_dir()
default_data = ROOT / 'data' if SOURCE_CHECKOUT else Path(
    os.environ.get('LOCALAPPDATA', str(Path.home() / '.local/share'))) / 'TouchMusic'
DATA = Path(os.environ.get('TOUCHMUSIC_DATA_DIR', str(default_data))).expanduser().resolve()
VENDOR = ROOT / 'vendor/seed-vc' if SOURCE_CHECKOUT else DATA / 'vendor/seed-vc'
SEED_REVISION = '51383efd921027683c89e5348211d93ff12ac2a8'
VERSION = '0.5.0.dev2'
