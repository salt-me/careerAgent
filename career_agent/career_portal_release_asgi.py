"""Recommended final local/server entrypoint for CareerAgent."""

from __future__ import annotations

from .platform.career_portal_release_app import create_career_portal_release_app
from .platform.config import PlatformSettings
from .platform.release_runtime import build_release_components


components = build_release_components(PlatformSettings.from_env())
app = create_career_portal_release_app(components)
