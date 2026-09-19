"""Seekable, bounded HTTP range reader for large public Parquet sources."""

from __future__ import annotations

import io
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class RangeSourceInfo:
    url: str
    size: int
    etag: str | None
    last_modified: str | None


class HTTPRangeReader(io.RawIOBase):
    """Expose a remote HTTP resource as a seekable file without full download.

    Every read uses a Range header and validates a 206 response.  A caller must
    supply a finite size; this intentionally prevents accidental multi-GB
    `read()` calls when operating on a public Parquet file.
    """

    def __init__(self, url: str, *, timeout_seconds: int = 60, user_agent: str = "CareerAgent/0.6") -> None:
        super().__init__()
        self.url = url
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent
        self._position = 0
        self._closed = False
        self.info = self._head()

    def _request(self, *, method: str = "GET", headers: dict[str, str] | None = None):
        request = urllib.request.Request(
            self.url,
            headers={"User-Agent": self.user_agent, **(headers or {})},
            method=method,
        )
        return urllib.request.urlopen(request, timeout=self.timeout_seconds)

    def _head(self) -> RangeSourceInfo:
        with self._request(method="HEAD") as response:
            size = int(response.headers["Content-Length"])
            accepts_ranges = response.headers.get("Accept-Ranges", "").lower()
            if "bytes" not in accepts_ranges:
                raise OSError(f"Remote source does not advertise byte-range support: {self.url}")
            return RangeSourceInfo(
                url=self.url,
                size=size,
                etag=response.headers.get("ETag"),
                last_modified=response.headers.get("Last-Modified"),
            )

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self._position

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        if whence == io.SEEK_SET:
            position = offset
        elif whence == io.SEEK_CUR:
            position = self._position + offset
        elif whence == io.SEEK_END:
            position = self.info.size + offset
        else:
            raise ValueError(f"Invalid whence: {whence}")
        if position < 0:
            raise ValueError("Cannot seek before the beginning of the source")
        self._position = min(position, self.info.size)
        return self._position

    def read(self, size: int = -1) -> bytes:
        if self._closed:
            raise ValueError("I/O operation on closed range reader")
        if size is None or size < 0:
            raise OSError("A finite read size is required to prevent a full remote download")
        if size == 0 or self._position >= self.info.size:
            return b""
        end = min(self._position + size, self.info.size) - 1
        expected = end - self._position + 1
        with self._request(headers={"Range": f"bytes={self._position}-{end}"}) as response:
            if getattr(response, "status", response.getcode()) != 206:
                raise OSError("Remote source ignored the range request; refusing a full-file response")
            payload = response.read(expected)
        if len(payload) != expected:
            raise OSError(f"Range read returned {len(payload)} bytes; expected {expected}")
        self._position += len(payload)
        return payload

    def close(self) -> None:
        self._closed = True
        super().close()
