"""Per-key principal budget and rate-limit enforcement."""

from __future__ import annotations

from collections import defaultdict, deque
from time import monotonic

from frostglass.errors import gateway_error
from frostglass.gateway.auth import Principal


class Limits:
    def __init__(self) -> None:
        self._spend: dict[str, int] = defaultdict(int)
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def check(self, principal: Principal) -> None:
        if self._spend[principal.team] >= principal.monthly_budget_cents:
            raise gateway_error(402, "Monthly budget exceeded", "budget_exceeded")
        now = monotonic()
        window = self._requests[principal.team]
        while window and window[0] <= now - 60:
            window.popleft()
        if len(window) >= principal.rate_limit_rpm:
            error = gateway_error(429, "Rate limit exceeded", "rate_limit_exceeded")
            error.headers = {"Retry-After": "60"}
            raise error
        window.append(now)

    def record_spend(self, principal: Principal, cents: int = 1) -> None:
        self._spend[principal.team] += cents
