"""Pure, deterministic booking decisions. No persistence or external services."""
from datetime import datetime, timedelta, timezone
import re

MAX_RECORDS = 10000
MAX_BUFFER_MINUTES = 10080
_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})\Z", re.ASCII)


class ValidationError(ValueError):
    """Invalid input. Messages identify fields, not their potentially private values."""


def _object(value, allowed, required, path):
    if not isinstance(value, dict):
        raise ValidationError(f"{path}: expected object")
    if set(value) - allowed:
        raise ValidationError(f"{path}: unknown field")
    if required - set(value):
        raise ValidationError(f"{path}: missing required field")


def _id(value, path):
    if not isinstance(value, str) or not value.strip() or len(value) > 128 or any(ord(c) < 32 or ord(c) == 127 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
        raise ValidationError(f"{path}: expected nonblank identifier, at most 128 characters, without control characters")
    return value


def _time(value, path):
    if not isinstance(value, str) or not _TIMESTAMP.fullmatch(value):
        raise ValidationError(f"{path}: expected ISO 8601 timestamp with seconds and explicit offset")
    # datetime permits oversized offset minute components and normalizes them.
    if value[-1:] != 'Z' and (int(value[-5:-3]) > 23 or int(value[-2:]) > 59 or value.endswith('-00:00')):
        raise ValidationError(f"{path}: invalid or unknown UTC offset")
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise ValidationError(f"{path}: invalid or out-of-range timestamp") from None


def _record(value, path, window=False):
    fields = {'id', 'resource_id', 'start', 'end'}
    _object(value, fields if window else fields | {'buffer_before_minutes', 'buffer_after_minutes'}, fields, path)
    result = {'id': _id(value['id'], path + '.id'), 'resource_id': _id(value['resource_id'], path + '.resource_id')}
    result['start'] = _time(value['start'], path + '.start')
    result['end'] = _time(value['end'], path + '.end')
    if result['end'] <= result['start']:
        raise ValidationError(f"{path}: end must be after start")
    for name in ('buffer_before_minutes', 'buffer_after_minutes'):
        n = value.get(name, 0)
        if type(n) is not int or not 0 <= n <= MAX_BUFFER_MINUTES:
            raise ValidationError(f"{path}.{name}: expected integer from 0 to {MAX_BUFFER_MINUTES}")
        result[name] = n
    try:
        result['effective_start'] = result['start'] - timedelta(minutes=result['buffer_before_minutes'])
        result['effective_end'] = result['end'] + timedelta(minutes=result['buffer_after_minutes'])
    except OverflowError:
        raise ValidationError(f"{path}: buffered interval exceeds datetime range") from None
    return result


def _stamp(dt):
    return dt.isoformat().replace('+00:00', 'Z')


def evaluate(payload):
    """Validate all input and return a JSON-compatible decision without mutation.

    operation=check requires candidate. operation=extend requires booking_id and
    new_end; only that existing booking is excluded from comparison. See docs/API.md.
    """
    common = {'operation', 'bookings', 'unavailable'}
    if not isinstance(payload, dict):
        raise ValidationError('request: expected object')
    op = payload.get('operation')
    if op not in ('check', 'extend'):
        raise ValidationError('operation: expected check or extend')
    extra = {'candidate'} if op == 'check' else {'booking_id', 'new_end'}
    _object(payload, common | extra, {'operation', 'bookings'} | extra, 'request')
    bookings, windows = [], []
    seen = set()
    for key, output in (('bookings', bookings), ('unavailable', windows)):
        values = payload.get(key, [])
        if not isinstance(values, list) or len(values) > MAX_RECORDS:
            raise ValidationError(f'{key}: expected array of at most {MAX_RECORDS} records')
        for i, value in enumerate(values):
            record = _record(value, f'{key}[{i}]', key == 'unavailable')
            if record['id'] in seen:
                raise ValidationError('records: duplicate id')
            seen.add(record['id'])
            output.append(record)
    if op == 'check':
        candidate = _record(payload['candidate'], 'candidate')
        if candidate['id'] in seen:
            raise ValidationError('candidate.id: already exists; use extend for extension')
        compared = bookings
    else:
        booking_id = _id(payload['booking_id'], 'booking_id')
        matched = [b for b in bookings if b['id'] == booking_id]
        if not matched:
            raise ValidationError('booking_id: booking not found')
        original = matched[0]
        end = _time(payload['new_end'], 'new_end')
        if end <= original['end']:
            raise ValidationError('new_end: must be later than existing end')
        raw = {k: original[k] for k in ('id', 'resource_id', 'buffer_before_minutes', 'buffer_after_minutes')}
        raw.update(start=_stamp(original['start']), end=_stamp(end))
        candidate = _record(raw, 'extension')
        compared = [b for b in bookings if b['id'] != booking_id]
    conflicts = []
    for kind, records in (('booking', compared), ('unavailable', windows)):
        for other in records:
            if other['resource_id'] != candidate['resource_id']:
                continue
            start = max(candidate['effective_start'], other['effective_start'])
            end = min(candidate['effective_end'], other['effective_end'])
            if start >= end:
                continue
            actual_overlap = max(candidate['start'], other['start']) < min(candidate['end'], other['end'])
            reason = 'UNAVAILABLE' if kind == 'unavailable' else ('BOOKING_OVERLAP' if actual_overlap else 'BUFFER_OVERLAP')
            conflicts.append({'reason': reason, 'record_id': other['id'], 'record_type': kind,
                              'overlap_start': _stamp(start), 'overlap_end': _stamp(end)})
    conflicts.sort(key=lambda c: (_time(c['overlap_start'], 'internal'), c['record_type'], c['record_id'], c['reason']))
    return {'schema_version': 1, 'operation': op, 'allowed': not conflicts,
            'candidate_id': candidate['id'], 'resource_id': candidate['resource_id'],
            'start': _stamp(candidate['start']), 'end': _stamp(candidate['end']),
            'effective_start': _stamp(candidate['effective_start']), 'effective_end': _stamp(candidate['effective_end']),
            'conflicts': conflicts}
