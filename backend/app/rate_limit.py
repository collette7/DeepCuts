import hashlib
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

import anyio
from fastapi import HTTPException, Request


@dataclass(frozen=True, slots=True)
class RateLimitPolicy:
    requests: int
    window_seconds: int


class SlidingWindowRateLimiter:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = anyio.Lock()

    async def check(self, bucket_key: str, policy: RateLimitPolicy) -> None:
        now = self._clock()
        cutoff = now - policy.window_seconds
        async with self._lock:
            if len(self._requests) >= 10_000:
                self._requests = defaultdict(
                    deque,
                    {
                        key: timestamps
                        for key, timestamps in self._requests.items()
                        if timestamps and timestamps[-1] > cutoff
                    },
                )
            timestamps = self._requests[bucket_key]
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()
            if len(timestamps) >= policy.requests:
                retry_after = max(1, int(timestamps[0] + policy.window_seconds - now))
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests. Please try again later.",
                    headers={"Retry-After": str(retry_after)},
                )
            timestamps.append(now)


SEARCH_POLICY: Final = RateLimitPolicy(requests=10, window_seconds=60)
ENRICHMENT_POLICY: Final = RateLimitPolicy(requests=60, window_seconds=60)
ANALYTICS_POLICY: Final = RateLimitPolicy(requests=120, window_seconds=60)
MUTATION_POLICY: Final = RateLimitPolicy(requests=30, window_seconds=60)

rate_limiter = SlidingWindowRateLimiter()


def _client_key(request: Request, bucket: str) -> str:
    authorization = request.headers.get("authorization")
    if authorization:
        identity = hashlib.sha256(authorization.encode()).hexdigest()[:16]
        return f"{bucket}:account:{identity}"

    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return f"{bucket}:ip:{forwarded_for.split(',')[-1].strip()}"

    host = request.client.host if request.client else "unknown"
    return f"{bucket}:ip:{host}"


async def enforce_search_rate_limit(request: Request) -> None:
    await rate_limiter.check(_client_key(request, "search"), SEARCH_POLICY)


async def enforce_enrichment_rate_limit(request: Request) -> None:
    await rate_limiter.check(_client_key(request, "enrichment"), ENRICHMENT_POLICY)


async def enforce_analytics_rate_limit(request: Request) -> None:
    await rate_limiter.check(_client_key(request, "analytics"), ANALYTICS_POLICY)


async def enforce_mutation_rate_limit(request: Request) -> None:
    await rate_limiter.check(_client_key(request, "mutation"), MUTATION_POLICY)
