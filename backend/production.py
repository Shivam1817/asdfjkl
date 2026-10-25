"""Serve the API and built React dashboard from the same origin."""

from pathlib import Path

from backend.app import app

build_directory = Path(__file__).resolve().parents[1] / "frontend" / "dist"
app.frontend("/", directory=build_directory, fallback=None, check_dir=True)
