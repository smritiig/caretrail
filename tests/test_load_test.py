import base64
import json
from types import SimpleNamespace

import pytest

from scripts.load_test import (
    percentile,
    token_seconds_remaining,
    validate_arguments,
)


def create_test_token(expiration: int) -> str:
    payload = json.dumps(
        {
            "exp": expiration,
        }
    ).encode("utf-8")

    encoded_payload = (
        base64.urlsafe_b64encode(payload)
        .decode("ascii")
        .rstrip("=")
    )

    return f"header.{encoded_payload}.signature"


def test_percentile_interpolates_values():
    values = [10.0, 20.0, 30.0, 40.0]

    assert percentile(values, 50) == pytest.approx(25.0)
    assert percentile(values, 95) == pytest.approx(38.5)


def test_token_seconds_remaining(monkeypatch):
    monkeypatch.setattr(
        "scripts.load_test.time.time",
        lambda: 1_000,
    )

    token = create_test_token(expiration=1_120)

    assert token_seconds_remaining(token) == 120


def test_invalid_token_is_rejected():
    with pytest.raises(
        ValueError,
        match="CARETRAIL_TOKEN is not a valid JWT",
    ):
        token_seconds_remaining("not-a-jwt")


def test_load_test_arguments_are_bounded():
    valid_arguments = SimpleNamespace(
        requests=100,
        rate=10.0,
        workers=20,
        timeout=10.0,
    )

    validate_arguments(valid_arguments)

    too_many_requests = SimpleNamespace(
        requests=25_001,
        rate=10.0,
        workers=20,
        timeout=10.0,
    )

    with pytest.raises(ValueError):
        validate_arguments(too_many_requests)

    excessive_rate = SimpleNamespace(
        requests=100,
        rate=101.0,
        workers=20,
        timeout=10.0,
    )

    with pytest.raises(ValueError):
        validate_arguments(excessive_rate)