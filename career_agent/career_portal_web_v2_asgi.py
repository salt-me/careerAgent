"""Recommended local web entrypoint with readable result excerpts."""

from __future__ import annotations

from .platform.config import PlatformSettings
from .platform.full_runtime_v2 import build_full_components
from .platform.portal_web_v2 import create_career_portal_web_v2_app


components = build_full_components(PlatformSettings.from_env())
app = create_career_portal_web_v2_app(components)
