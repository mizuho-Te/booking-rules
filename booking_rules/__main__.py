"""JSON stdin/stdout CLI: python -m booking_rules < request.json."""
import json
import sys
from .core import ValidationError, evaluate

MAX_INPUT_BYTES = 2 * 1024 * 1024


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValidationError('JSON: duplicate object key')
        result[key] = value
    return result


def _constant(value):
    raise ValidationError('JSON: non-finite numbers are not permitted')


def main():
    """Read one UTF-8 JSON object. Exit 0 allowed, 1 conflict, 2 invalid input."""
    if len(sys.argv) > 1:
        if sys.argv[1:] in (['--help'], ['-h']):
            print('Usage: python -m booking_rules < request.json\nUTF-8 JSON stdin/stdout. Exit: 0 allowed; 1 conflict; 2 invalid input.')
            return 0
        print(json.dumps({'error': {'code': 'INVALID_INPUT', 'message': 'CLI accepts stdin only; use --help'}}))
        return 2
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise ValidationError('input: exceeds 2 MiB limit')
        payload = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs, parse_constant=_constant)
        result = evaluate(payload)
        code = 0 if result['allowed'] else 1
    except (ValidationError, UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError, OSError) as exc:
        message = str(exc) if isinstance(exc, ValidationError) else 'input: malformed UTF-8 JSON or excessive nesting'
        result = {'error': {'code': 'INVALID_INPUT', 'message': message}}
        code = 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(',', ':')))
    return code


if __name__ == '__main__':
    # Only CLI process streams are reconfigured. Importing never changes streams.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='strict')
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        # Avoid interpreter shutdown retrying the failed buffered output.
        import os
        os._exit(1)
