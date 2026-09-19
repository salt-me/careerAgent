"""Full candidate portal: official ATS boards plus enabled China page adapters."""

from __future__ import annotations

from .platform.config import PlatformSettings
from .platform.full_runtime import build_full_components
from .platform.portal import create_career_portal_app


components = build_full_components(PlatformSettings.from_env())
app = create_career_portal_app(components)
