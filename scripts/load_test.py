import argparse
import base64
import binascii
import json
import math
import os
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


MAX_REQUESTS = 25_000
MAX_RATE = 100.0


@dataclass(frozen=True)
class RequestResult:
    status_code: int
    latency_ms: float
    error: str | None = None


def percentile(values: list[float], percent: float) -> float:
    if not values:
        return 0.0

    ordered = sorted(values)
    position = (len(ordered) - 1) * (percent / 100)
    lower = math.floor(position)
    upper = math.ceil(position)

    if lower == upper:
        return ordered[lower]

    fraction = position - lower

    return (
        ordered[lower]
        + (ordered[upper] - ordered[lower]) * fraction
    )


def token_seconds_remaining(token: str) -> float:
    try:
        encoded_payload = token.split(".")[1]
        encoded_payload += "=" * (-len(encoded_payload) % 4)

        payload = json.loads(
            base64.urlsafe_b64decode(encoded_payload)
        )

        return float(payload["exp"]) - time.time()

    except (
        binascii.Error,
        IndexError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        raise ValueError(
            "CARETRAIL_TOKEN is not a valid JWT"
        ) from exc


def create_event(index: int) -> dict:
    event_id = f"load-{uuid.uuid4()}"

    return {
        "event_id": event_id,
        "actor_id": f"load-test-user-{index % 10}",
        "patient_id": f"synthetic-patient-{index % 100}",
        "action": "PATIENT_RECORD_VIEWED",
        "outcome": "SUCCESS",
        "occurred_at": datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
    }


def send_event(
    api_url: str,
    token: str,
    index: int,
    timeout: float,
) -> RequestResult:
    payload = json.dumps(create_event(index)).encode("utf-8")

    request = Request(
        url=f"{api_url}/audit-events",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    started_at = time.perf_counter()

    try:
        with urlopen(request, timeout=timeout) as response:
            response.read()
            status_code = response.status
            error = None

    except HTTPError as exc:
        status_code = exc.code
        error = f"HTTP {exc.code}"

    except URLError as exc:
        status_code = 0
        error = str(exc.reason)

    except TimeoutError:
        status_code = 0
        error = "Request timed out"

    latency_ms = (time.perf_counter() - started_at) * 1_000

    return RequestResult(
        status_code=status_code,
        latency_ms=latency_ms,
        error=error,
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a controlled load test against CareTrail."
    )

    parser.add_argument(
        "--requests",
        type=int,
        default=20,
        help=f"Total requests to send (maximum {MAX_REQUESTS}).",
    )
    parser.add_argument(
        "--rate",
        type=float,
        default=1.0,
        help=f"Target requests per second (maximum {MAX_RATE}).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=20,
        help="Maximum concurrent request workers.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Timeout for each request in seconds.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmark-results.json"),
        help="JSON results file.",
    )

    return parser.parse_args()


def validate_arguments(arguments: argparse.Namespace) -> None:
    if arguments.requests < 1 or arguments.requests > MAX_REQUESTS:
        raise ValueError(
            f"--requests must be between 1 and {MAX_REQUESTS}"
        )

    if arguments.rate <= 0 or arguments.rate > MAX_RATE:
        raise ValueError(
            f"--rate must be greater than 0 and at most {MAX_RATE}"
        )

    if arguments.workers < 1 or arguments.workers > 100:
        raise ValueError("--workers must be between 1 and 100")

    if arguments.timeout <= 0:
        raise ValueError("--timeout must be greater than 0")


def main() -> None:
    arguments = parse_arguments()
    validate_arguments(arguments)

    api_url = os.getenv("CARETRAIL_API_URL", "").strip().rstrip("/")
    token = os.getenv("CARETRAIL_TOKEN", "").strip()

    if not api_url:
        raise RuntimeError(
            "CARETRAIL_API_URL environment variable is required"
        )

    if not token:
        raise RuntimeError(
            "CARETRAIL_TOKEN environment variable is required"
        )

    expected_duration = arguments.requests / arguments.rate
    remaining_token_time = token_seconds_remaining(token)
    required_token_time = expected_duration + 60

    if remaining_token_time < required_token_time:
        raise RuntimeError(
            "The Cognito token will expire before this test can finish. "
            "Refresh CARETRAIL_TOKEN and try again."
        )

    print("CareTrail controlled load test")
    print(f"Requests: {arguments.requests}")
    print(f"Target rate: {arguments.rate:.2f} requests/second")
    print(f"Workers: {arguments.workers}")
    print()

    started_at = time.perf_counter()
    futures = []

    with ThreadPoolExecutor(
        max_workers=arguments.workers
    ) as executor:
        for index in range(arguments.requests):
            scheduled_at = started_at + (index / arguments.rate)
            delay = scheduled_at - time.perf_counter()

            if delay > 0:
                time.sleep(delay)

            futures.append(
                executor.submit(
                    send_event,
                    api_url,
                    token,
                    index,
                    arguments.timeout,
                )
            )

        results = [
            future.result()
            for future in as_completed(futures)
        ]

    duration_seconds = time.perf_counter() - started_at

    latencies = [
        result.latency_ms
        for result in results
        if result.status_code == 202
    ]

    if not latencies:
        latencies = [0.0]

    status_counts = Counter(
        result.status_code for result in results
    )

    error_counts = Counter(
        result.error or f"HTTP {result.status_code}"
        for result in results
        if result.status_code not in (202, 429)
    )

    accepted = status_counts.get(202, 0)
    throttled = status_counts.get(429, 0)
    failed = len(results) - accepted - throttled
    success_rate = accepted / len(results) * 100

    summary = {
        "timestamp": datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "requests": len(results),
        "target_rate_per_second": arguments.rate,
        "actual_rate_per_second": (
            len(results) / duration_seconds
        ),
        "duration_seconds": duration_seconds,
        "accepted": accepted,
        "throttled": throttled,
        "failed": failed,
        "success_rate_percent": success_rate,
        "latency_ms": {
            "minimum": min(latencies),
            "average": sum(latencies) / len(latencies),
            "p50": percentile(latencies, 50),
            "p95": percentile(latencies, 95),
            "p99": percentile(latencies, 99),
            "maximum": max(latencies),
        },
        "status_counts": {
            str(status): count
            for status, count in sorted(status_counts.items())
        },
        "error_counts": {
            error: count
            for error, count in sorted(error_counts.items())
        },
    }

    arguments.output.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print("Results")
    print(f"Duration: {duration_seconds:.2f} seconds")
    print(
        "Actual rate: "
        f"{summary['actual_rate_per_second']:.2f} requests/second"
    )
    print(f"Accepted: {accepted}")
    print(f"Throttled: {throttled}")
    print(f"Failed: {failed}")
    print(f"Success rate: {success_rate:.2f}%")
    print(f"Status counts: {dict(sorted(status_counts.items()))}")

    if error_counts:
        print(f"Error counts: {dict(sorted(error_counts.items()))}")

    print()
    print("Accepted-request latency")
    print(f"Minimum: {summary['latency_ms']['minimum']:.2f} ms")
    print(f"Average: {summary['latency_ms']['average']:.2f} ms")
    print(f"P50: {summary['latency_ms']['p50']:.2f} ms")
    print(f"P95: {summary['latency_ms']['p95']:.2f} ms")
    print(f"P99: {summary['latency_ms']['p99']:.2f} ms")
    print(f"Maximum: {summary['latency_ms']['maximum']:.2f} ms")
    print()
    print(f"Results saved to {arguments.output}")


if __name__ == "__main__":
    main()