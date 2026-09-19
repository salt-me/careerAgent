"""Small, privacy-first profile isolation for the local CareerAgent portal.

The local deployment deliberately avoids inventing an authentication provider.
Clients may supply a stable ``X-Career-Profile`` value; values are validated
and every workspace operation is scoped to that key.  A real SSO layer can
replace this resolver later without changing the workspace APIs.
"""

from __future__ import annotations

import re
from typing import Annotated

from fastapi import Header, HTTPException


_PROFILE_KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}")


def active_profile_key(
    x_career_profile: Annotated[str | None, Header()] = None,
) -> str:
    value = (x_career_profile or "local").strip()
    if not _PROFILE_KEY.fullmatch(value):
        raise HTTPException(
            status_code=422,
            detail="X-Career-Profile must be 1-80 characters: letters, numbers, dot, underscore or hyphen.",
        )
    return value
