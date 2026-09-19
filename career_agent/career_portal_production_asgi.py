"""Current recommended ASGI entrypoint for the complete CareerAgent portal."""

from __future__ import annotations

from .platform.career_portal_production_app import create_career_portal_production_app
from .platform.config import PlatformSettings
from .platform.full_runtime_v2 import build_full_components


components = build_full_components(PlatformSettings.from_env())
app = create_career_portal_production_app(components)
