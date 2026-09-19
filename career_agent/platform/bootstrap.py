"""Factories for configured live connectors and reviewed snapshot imports."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .config import PlatformSettings
from .connectors import GreenhouseConnector, JobConnector, JsonlSnapshotConnector


def configured_connectors(settings: PlatformSettings) -> list[JobConnector]:
    return [GreenhouseConnector(board) for board in settings.greenhouse_boards]


def snapshot_connector(paths: Iterable[Path]) -> JsonlSnapshotConnector:
    return JsonlSnapshotConnector("authorised_snapshot_import", paths)

