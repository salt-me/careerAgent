"""Recommended production entrypoint for the complete CareerAgent portal."""

from __future__ import annotations

from .platform.config import PlatformSettings
from .platform.full_runtime_v2 import build_full_components
from .platform.portal import create_career_portal_app


components = build_full_components(PlatformSettings.from_env())
app = create_career_portal_app(components)
