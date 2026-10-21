# API v1

## Request

`evaluate(payload: dict) -> dict` is the sole public decision function. Invalid input raises `ValidationError` (a `ValueError` subclass). Use JSON-compatible built-in types. It does not mutate the request. Unknown keys are errors, not silently ignored.

Required top-level keys: `operation`, `bookings`. Optional: `unavailable` (default empty array).

For `operation: "check"`, add `candidate`, a booking record. Its ID must not already exist. For `operation: "extend"`, add `booking_id` and `new_end`. This ID must identify a booking, not an unavailable window. New end must be strictly later than the existing end. The extension operation reconstructs that booking with the later end and preserves all other fields. There is no unrestricted `exclude_id` parameter. Unknown exclusion/replacement keys are errors.

### Booking record

Required: `id`, `resource_id`, `start`, `end`.
Optional: `buffer_before_minutes`, `buffer_after_minutes` (each defaults to zero).

An unavailable-window record has only the four required fields, no buffers. Booking and window IDs share one unique namespace; duplicate IDs are rejected even across resources. Candidate ID must not collide with a window ID either.

Identifiers are exact, case-sensitive strings of 1–128 Unicode characters; blank-only strings, control characters U+0000–001F/U+007F and surrogate code points are rejected. No whitespace trimming or Unicode normalization is performed. Use stable opaque IDs, not customer names or secrets.

Datetime syntax: `YYYY-MM-DDTHH:MM:SS[.ffffff](Z|+HH:MM|-HH:MM)`. ASCII digits, uppercase T/Z, 1–6 fractional digits if present. Valid calendar dates only, years 0001–9999. Offset hour range 00–23, minute range 00–59. `-00:00` denotes an unknown offset and is rejected; use `Z` or `+00:00` for known UTC. Calendar arithmetic and offset/buffer normalization must remain in datetime's valid range. No leap seconds, ISO week dates, named zones or DST inference. If wall times cross DST, callers supply the correct offset separately for each endpoint.

End must be strictly after start in UTC. Buffers are integer minutes, inclusive range 0–10080 (seven days). Booleans, fractions, numeric strings, null and negatives are not integers for this API. These limits are operational guards, not a recommendation for reservation length.

Each of the bookings and unavailable arrays may hold at most 10,000 records (20,000 combined). CLI input is at most 2 MiB, decoded strictly as UTF-8 without BOM. Library calls have no serialized-byte cap. CLI rejects duplicate JSON object keys, NaN/Infinity and excessive nesting.

## Response

- `schema_version`: 1
- `operation`: check or extend
- `allowed`: true exactly when conflicts is empty
- `candidate_id`, `resource_id`: exact IDs
- `start`, `end`: normalized candidate time
- `effective_start`, `effective_end`: time including buffers
- `conflicts`: zero or more records containing `reason`, `record_id`, `record_type`, `overlap_start`, `overlap_end`

All output timestamps are UTC with `Z`. Fractional seconds, if nonzero, have six digits. No fractional component is emitted for whole seconds. Overlap endpoints represent the intersection of effective occupied intervals, not merely unbuffered business time.

Reasons:

- `BOOKING_OVERLAP`: candidate's actual interval overlaps another booking's actual interval.
- `BUFFER_OVERLAP`: effective intervals overlap but actual intervals do not.
- `UNAVAILABLE`: candidate's effective interval overlaps an unavailable window.

Record type is `booking` or `unavailable`. For an unavailable window, its effective interval is its actual interval. Reasons are mutually exclusive per opposing record. The same resource may yield multiple conflicts, each retained.

Conflict ordering is ascending overlap start instant, then record type, record ID (Unicode code-point ordering), reason. UTC comparisons ensure ordering is not affected by input timezone offsets. CLI object keys are sorted and separators compact, so reordering equivalent input records does not change output bytes.

## CLI

`python -m booking_rules`, JSON stdin, JSON stdout. No file paths or network calls. Close stdin to finish the single request. Like other stdin filters, an open stream can wait for more bytes; no wall-clock timeout is provided. Application integrations should impose their own request timeout.

Exit 0: allowed. Exit 1: conflicts (also used if the output pipe closes early). Exit 2: invalid input or arguments. `--help` prints text and exits 0. Error JSON is `{"error":{"code":"INVALID_INPUT","message":"..."}}`. Error messages name the invalid field rather than echoing input values. Malformed JSON/UTF-8 receives a generic error; detailed error strings are not a compatibility-stable API. Library callers get exceptions, not CLI envelopes.

UTF-8 is configured only when running the CLI as a module. Importing this package does not change process stream encoding. External build/install tooling is not part of the runtime CLI.

## Non-goals and caller responsibilities

Read-only snapshot decision only, capacity one per resource. No authentication, authorization, booking persistence, atomic commits, race prevention, whole-schedule conflict audit, recurrence, fees, customer records, calendar-service integration or timezone database. An extension can expose pre-existing conflicts because it rechecks the entire resulting interval. Host applications must validate caller authorization for the target booking and prevent stale-snapshot writes using their datastore's concurrency controls.
