"""Rate limits are normal operation on the free tier, so the runner waits them out instead of
failing the stage that hit one."""

from typing import Any

import pytest
from app.agents.base.sdk_runner import is_rate_limited, retrying


class FakeQuotaError(Exception):
    pass


def quota_error() -> FakeQuotaError:
    return FakeQuotaError(
        "429 RESOURCE_EXHAUSTED. Quota exceeded for metric: generate_content_free_tier_requests"
    )


def wrapped_quota_error() -> Exception:
    outer = RuntimeError("model call failed")
    outer.__cause__ = quota_error()
    return outer


def test_a_429_is_recognised_even_when_adk_wraps_it() -> None:
    assert is_rate_limited(quota_error()) is True
    assert is_rate_limited(wrapped_quota_error()) is True
    assert is_rate_limited(ValueError("bad schema")) is False


def test_a_cyclic_exception_chain_does_not_hang_the_check() -> None:
    a, b = RuntimeError("a"), RuntimeError("b")
    a.__cause__, b.__cause__ = b, a
    assert is_rate_limited(a) is False


async def test_a_rate_limited_attempt_is_retried_until_it_succeeds() -> None:
    calls: list[int] = []
    naps: list[float] = []

    async def attempt() -> str:
        calls.append(1)
        if len(calls) < 3:
            raise quota_error()
        return "answer"

    async def nap(seconds: float) -> None:
        naps.append(seconds)

    result = await retrying(attempt, delays=(10.0, 30.0, 65.0), sleep=nap)
    assert result == "answer" and len(calls) == 3
    assert naps == [10.0, 30.0]


async def test_anything_that_is_not_a_rate_limit_fails_immediately() -> None:
    calls: list[int] = []

    async def attempt() -> str:
        calls.append(1)
        raise ValueError("the schema was wrong")

    async def nap(seconds: float) -> None:  # pragma: no cover
        raise AssertionError("should not sleep")

    with pytest.raises(ValueError):
        await retrying(attempt, sleep=nap)
    assert len(calls) == 1


async def test_a_rate_limit_that_never_lifts_gives_up_to_the_queues_backoff() -> None:
    calls: list[Any] = []
    naps: list[float] = []

    async def attempt() -> str:
        calls.append(1)
        raise quota_error()

    async def nap(seconds: float) -> None:
        naps.append(seconds)

    with pytest.raises(FakeQuotaError):
        await retrying(attempt, delays=(10.0, 30.0), sleep=nap)
    assert len(calls) == 3  # two retried attempts, then the final one propagates
    assert naps == [10.0, 30.0]
