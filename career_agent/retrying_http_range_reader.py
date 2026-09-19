"""Retry-safe bounded HTTP range reader for unstable public file hosts."""

from __future__ import annotations

import io
import time
from typing import Any

from .http_range_reader import HTTPRangeReader


class RetryingHTTPRangeReader(HTTPRangeReader):
    """A range reader that retries only the failed bounded request.

    The source is never downloaded in full: each retry repeats the same byte
    range and verifies both the 206 response and the exact payload length.
    """

    def __init__(
        self,
        url: str,
        *,
        timeout_seconds: int = 75,
        max_attempts: int = 5,
        retry_delay_seconds: float = 1.5,
        user_agent: str = "CareerAgent/0.6",
    ) -> None:
        self.max_attempts = max_attempts
        self.retry_delay_seconds = retry_delay_seconds
        super().__init__(url, timeout_seconds=timeout_seconds, user_agent=user_agent)

    def _request(self, *, method: str = "GET", headers: dict[str, str] | None = None):
        last_error: BaseException | None = None
        for attempt in range(self.max_attempts):
            try:
                return super()._request(method=method, headers=headers)
            except (OSError, TimeoutError) as error:
                last_error = error
                if attempt + 1 < self.max_attempts:
                    time.sleep(self.retry_delay_seconds * (attempt + 1))
        raise OSError(
            f"HTTP {method} failed after {self.max_attempts} bounded attempts for {self.url}"
        ) from last_error

    def read(self, size: int = -1) -> bytes:
        if self._closed:
            raise ValueError("I/O operation on closed range reader")
        if size is None or size < 0:
            raise OSError("A finite read size is required to prevent a full remote download")
        if size == 0 or self._position >= self.info.size:
            return b""

        start = self._position
        end = min(start + size, self.info.size) - 1
        expected = end - start + 1
        last_error: BaseException | None = None
        for attempt in range(self.max_attempts):
            try:
                with self._request(headers={"Range": f"bytes={start}-{end}"}) as response:
                    if getattr(response, "status", response.getcode()) != 206:
                        raise OSError("Remote source ignored the range request; refusing a full-file response")
                    payload = response.read(expected)
                if len(payload) != expected:
                    raise OSError(f"Range read returned {len(payload)} bytes; expected {expected}")
                self._position = start + len(payload)
                return payload
            except (OSError, TimeoutError) as error:
                last_error = error
                if attempt + 1 < self.max_attempts:
                    time.sleep(self.retry_delay_seconds * (attempt + 1))
        raise OSError(
            f"Range read {start}-{end} failed after {self.max_attempts} bounded attempts"
        ) from last_error

