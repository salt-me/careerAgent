"""Compatibility command: run real official-source verification, never auto-archive."""

from __future__ import annotations

from .verify_snapshot_sources import main


if __name__ == "__main__":
    main()