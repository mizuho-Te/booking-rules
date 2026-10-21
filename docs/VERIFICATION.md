# Verification record

Date: 2026-10-21 (UTC).

## Executed locally

Environment: Linux, Python 3.12.14.

- `python -m unittest discover -s tests -v`: 38 tests passed. Includes 300 seeded random interval/buffer oracle cases, translation invariance and a 10,000-record input.
- `python -m compileall -q booking_rules tests examples`: passed.
- `python examples/run_demo.py`: real CLI returned the expected buffer-conflict decision with Japanese identifiers.
- Extension example: independently checked; the preserved cleanup buffer overlaps the unavailable maintenance period as expected.
- `python -m pip wheel --no-deps --no-build-isolation --wheel-dir /tmp/booking-rules-wheel .`: wheel built successfully without downloading dependencies.
- CLI regression with `PYTHONIOENCODING=cp1252` and `PYTHONUTF8=0`: UTF-8 Japanese output decoded successfully. This simulates a legacy stream encoding on Linux; it is not a native Windows run.
- Independent read-only review reported 3,891 assertions passed, including 1,500 seeded interval cases, offset/DST-fold inputs, microsecond boundaries, ordering permutations, and unchanged inputs after failure. Additional malformed CLI requests and positional symlink/FIFO arguments were rejected. Those review assertions are separate from the committed 38-test suite.

## Not established

- The nine configured remote CI combinations have not been run as part of this local record.
- Native Windows and macOS execution, production installation, real-world adoption and concurrent datastore integration have not been validated here.
- Local test success does not prove correctness for every possible input or safety of a consuming application's persistence layer.
- No package-registry upload or production deployment has been performed.

The authoritative reproducible regression suite is in `tests/`; examples use synthetic records only.
