# booking-rules

A small, deterministic Python library and UTF-8 JSON CLI for checking resource bookings before saving them.

[日本語](README.ja.md) · [API](docs/API.md) · [License status](LICENSE)

## Status

Version 0.1.0; released under the MIT license. All examples are synthetic. No production adoption, user count or operational success is claimed. Python 3.11+; no runtime dependencies. CI is configured for Linux, Windows and macOS on Python 3.11–3.13; configuration is not evidence those remote jobs have run.

## Why use it?

An application can ask: “Can room A be reserved from 10:00 until 11:00, allowing 15 minutes for preparation?” or “Would extending this equipment reservation conflict with another booking?”

The result names the conflicting records and distinguishes direct overlap, buffer-only overlap and unavailable periods. Different resources are independent. Inputs are never mutated. Results do not depend on record ordering.

## Try it without installation

From the repository directory:

```sh
python examples/run_demo.py
python -m unittest discover -s tests -v
```

The demo runs the real CLI with synthetic Japanese identifiers and prints a buffer conflict. It works without shell-specific input redirection on Windows, macOS and Linux. For shells supporting redirection:

```sh
python -m booking_rules < examples/buffer-conflict.json
```

CLI exit statuses: `0` allowed, `1` conflict, `2` invalid input. JSON is on stdout. A conflict exit is a successful evaluation, not a crash. Send exactly one UTF-8 JSON object via stdin and close the stream. CLI `--help` is also available.

## Python API

```python
from booking_rules import evaluate, ValidationError

result = evaluate({
    "operation": "check",
    "bookings": [],
    "candidate": {
        "id": "new-1", "resource_id": "room-a",
        "start": "2026-10-21T10:00:00+09:00",
        "end": "2026-10-21T11:00:00+09:00",
        "buffer_before_minutes": 15,
        "buffer_after_minutes": 10
    }
})
assert result["allowed"] is True
```

Call `evaluate(payload)` with JSON-compatible built-in Python dictionaries/lists; invalid data raises `ValidationError`. Install locally if useful with `python -m pip install .`; setuptools is needed for the build, but the runtime uses only the standard library.

## Rules and boundaries

- Use explicit UTC offsets or `Z`, with seconds. No naive local times, zone names, date-only values, leap seconds or unknown `-00:00` offsets. Fractional seconds: at most six digits.
- All intervals are half-open `[start, end)`. A booking ending exactly when the next effective interval begins is allowed.
- Preparation/cleanup buffers expand each booking's occupied interval on both sides. Two adjacent bookings' buffers both count. Unavailable windows have no buffers and block the entire effective candidate interval.
- `extend` can only extend the end of a uniquely identified existing booking. Resource, start, identity and buffers cannot be silently changed. It excludes only that booking and checks the entire resulting interval, not just the added portion.
- This checks a candidate, not the consistency of every pair already in the schedule. It does validate every record, including other resources, before returning a decision.
- No storage, network access, persistence, recurring schedules, timezone database, prices, fees or personal/customer records.

## Critical integration limitation

`allowed: true` describes only the supplied snapshot. It does not reserve anything and cannot prevent two concurrent users from both receiving approval. The host application must authorize the operation and enforce atomic validation/write transactions, locks or database constraints. Never use this result alone as a concurrency guarantee. Keep logs and identifiers free of personal information. Domain policy, authorization, capacity greater than one and cancellation rules belong to the host application.

See [API documentation](docs/API.md) for complete schemas, limits, ordering and errors. See [verification notes](docs/VERIFICATION.md) for exactly what was exercised locally.
