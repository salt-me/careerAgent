"""Rate-limited, auditable verification of snapshot URLs against official ATS APIs."""

from __future__ import annotations

from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable, Iterable
from urllib.parse import urlsplit, urlunsplit

from .connectors import GreenhouseConnector, IncomingJob
from .models import JobRecord
from .official_ats_connectors import AshbyConnector, LeverConnector


SUPPORTED_PROVIDERS = {"greenhouse", "lever", "ashby"}
BoardFetcher = Callable[[str, str], list[IncomingJob]]


@dataclass(frozen=True)
class VerificationTarget:
    job_id: str
    source_url: str
    provider: str | None
    board: str | None


@dataclass(frozen=True)
class VerificationBatch:
    verified_open_ids: tuple[str, ...]
    verified_closed_ids: tuple[str, ...]
    pending_ids_by_reason: dict[str, tuple[str, ...]]
    board_attempts: dict[str, int]
    board_failures: dict[str, int]


def normalize_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    path = parsed.path.rstrip("/") or "/"
    # http/https and tracking parameters do not change an ATS posting identity.
    return urlunsplit(("", parsed.netloc.casefold(), path, "", ""))


def provider_job_key(provider: str, url: str) -> tuple[str, str, str] | None:
    target = target_from_url(url)
    parsed = urlsplit(url)
    segments = [segment for segment in parsed.path.split("/") if segment]
    if target.provider != provider or not target.board or not segments:
        return None
    return provider, target.board.casefold(), segments[-1].casefold()


def target_from_url(url: str) -> VerificationTarget:
    parsed = urlsplit(url)
    host = parsed.netloc.casefold()
    segments = [segment for segment in parsed.path.split("/") if segment]
    if "greenhouse" in host and segments:
        return VerificationTarget("", url, "greenhouse", segments[0])
    if host.endswith("jobs.lever.co") and segments:
        return VerificationTarget("", url, "lever", segments[0])
    if host.endswith("jobs.ashbyhq.com") and segments:
        return VerificationTarget("", url, "ashby", segments[0])
    return VerificationTarget("", url, None, None)


def target_from_record(record: JobRecord) -> VerificationTarget:
    target = target_from_url(record.source_url)
    return VerificationTarget(record.id, record.source_url, target.provider, target.board)


def _default_fetch(provider: str, board: str) -> list[IncomingJob]:
    if provider == "greenhouse":
        return GreenhouseConnector(board).fetch()
    if provider == "lever":
        return LeverConnector(board).fetch()
    if provider == "ashby":
        return AshbyConnector(board).fetch()
    raise ValueError(f"Unsupported provider: {provider}")


def verify_targets(
    targets: Iterable[VerificationTarget],
    *,
    fetch_board: BoardFetcher | None = None,
    max_workers: int = 6,
) -> VerificationBatch:
    """Verify only via successful public ATS board APIs.

    A failed API call never closes a job.  A job is closed only when its own
    board fetched successfully and no longer publishes that URL.
    """
    fetch_board = fetch_board or _default_fetch
    groups: dict[tuple[str, str], list[VerificationTarget]] = defaultdict(list)
    pending: dict[str, list[str]] = defaultdict(list)
    for target in targets:
        if target.provider not in SUPPORTED_PROVIDERS or not target.board:
            pending["unsupported_official_source"].append(target.job_id)
        else:
            groups[(target.provider, target.board)].append(target)

    verified_open: list[str] = []
    verified_closed: list[str] = []
    attempts: Counter[str] = Counter()
    failures: Counter[str] = Counter()
    with ThreadPoolExecutor(max_workers=max(1, min(max_workers, 12))) as pool:
        futures = {
            pool.submit(fetch_board, provider, board): (provider, board, board_targets)
            for (provider, board), board_targets in groups.items()
        }
        for future in as_completed(futures):
            provider, _board, board_targets = futures[future]
            attempts[provider] += 1
            try:
                live_jobs = [job for job in future.result() if job.source_url]
                live_urls = {normalize_url(job.source_url) for job in live_jobs}
                live_keys = {provider_job_key(provider, job.source_url) for job in live_jobs}
            except Exception:
                failures[provider] += 1
                pending[f"official_{provider}_verification_failed"].extend(target.job_id for target in board_targets)
                continue
            for target in board_targets:
                if normalize_url(target.source_url) in live_urls or provider_job_key(provider, target.source_url) in live_keys:
                    verified_open.append(target.job_id)
                else:
                    verified_closed.append(target.job_id)

    return VerificationBatch(
        verified_open_ids=tuple(verified_open),
        verified_closed_ids=tuple(verified_closed),
        pending_ids_by_reason={reason: tuple(ids) for reason, ids in pending.items()},
        board_attempts=dict(attempts),
        board_failures=dict(failures),
    )
