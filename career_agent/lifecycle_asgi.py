"""Production entry point with retry-enabled daily connector runtime."""

from __future__ import annotations

from .platform.config import PlatformSettings
from .platform.runtime import build_components
from .platform.service import create_platform_app


components = build_components(PlatformSettings.from_env())
app = create_platform_app(components)

