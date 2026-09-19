"""Single recommended entrypoint for the complete non-Docker release."""

from __future__ import annotations

from .platform.career_portal_complete_app import create_complete_career_portal_app
from .platform.config import PlatformSettings
from .platform.release_runtime import build_release_components


components = build_release_components(PlatformSettings.from_env())
app = create_complete_career_portal_app(components)
