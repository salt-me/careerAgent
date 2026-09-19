"""Runtime extension for reviewed official source contracts."""

from __future__ import annotations

from .config import PlatformSettings
from .full_runtime_v2 import build_full_components
from .official_source_contracts import configured_official_json_contracts
from .resilience import RetryPolicy, RetryingConnector


def build_release_components(settings: PlatformSettings):
    components = build_full_components(settings)
    for connector in configured_official_json_contracts():
        wrapped = RetryingConnector(connector, RetryPolicy(max_attempts=3))
        components.orchestrator.connectors[wrapped.name] = wrapped
    return components
