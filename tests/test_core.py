import copy
import unittest
from booking_rules import evaluate, ValidationError


def booking(id='existing', resource='room', start='2026-10-21T10:00:00+09:00', end='2026-10-21T11:00:00+09:00', **kw):
    return dict(id=id, resource_id=resource, start=start, end=end, **kw)


def request(candidate=None, bookings=None, **kw):
    return dict(operation='check', bookings=[] if bookings is None else bookings,
                candidate=booking('candidate') if candidate is None else candidate, **kw)


class RulesTests(unittest.TestCase):
    def test_empty_allowed_and_nonmutation(self):
        data = request(); before = copy.deepcopy(data)
        self.assertTrue(evaluate(data)['allowed'])
        self.assertEqual(before, data)

    def test_overlap(self):
        r = evaluate(request(bookings=[booking()]))
        self.assertFalse(r['allowed']); self.assertEqual(r['conflicts'][0]['reason'], 'BOOKING_OVERLAP')
        self.assertEqual(r['start'], '2026-10-21T01:00:00Z')

    def test_touching_edges_allowed(self):
        for b in [booking(start='2026-10-21T09:00:00+09:00', end='2026-10-21T10:00:00+09:00'),
                  booking(start='2026-10-21T11:00:00+09:00', end='2026-10-21T12:00:00+09:00')]:
            self.assertTrue(evaluate(request(bookings=[b]))['allowed'])

    def test_different_resource(self):
        self.assertTrue(evaluate(request(bookings=[booking(resource='other')]))['allowed'])

    def test_buffer_on_existing(self):
        b = booking(end='2026-10-21T10:00:00+09:00', start='2026-10-21T09:00:00+09:00', buffer_after_minutes=15)
        self.assertEqual(evaluate(request(bookings=[b]))['conflicts'][0]['reason'], 'BUFFER_OVERLAP')

    def test_buffer_on_candidate(self):
        b = booking(start='2026-10-21T11:00:00+09:00', end='2026-10-21T12:00:00+09:00')
        c = booking('candidate', buffer_after_minutes=1)
        self.assertEqual(evaluate(request(c, [b]))['conflicts'][0]['reason'], 'BUFFER_OVERLAP')

    def test_both_buffers_touch(self):
        c = booking('candidate', buffer_after_minutes=15)
        b = booking(start='2026-10-21T11:30:00+09:00', end='2026-10-21T12:00:00+09:00', buffer_before_minutes=15)
        self.assertTrue(evaluate(request(c, [b]))['allowed'])
        b['buffer_before_minutes'] = 16
        self.assertFalse(evaluate(request(c, [b]))['allowed'])

    def test_unavailable(self):
        w = booking('maintenance')
        r = evaluate(request(unavailable=[w]))
        self.assertEqual(r['conflicts'][0]['reason'], 'UNAVAILABLE')
        self.assertEqual(r['conflicts'][0]['record_type'], 'unavailable')

    def test_unavailable_blocks_buffer(self):
        c = booking('candidate', buffer_before_minutes=30)
        w = booking('window', start='2026-10-21T09:40:00+09:00', end='2026-10-21T09:50:00+09:00')
        self.assertFalse(evaluate(request(c, unavailable=[w]))['allowed'])

    def test_offsets_equivalent(self):
        b = booking(start='2026-10-21T01:00:00Z', end='2026-10-21T02:00:00Z')
        self.assertFalse(evaluate(request(bookings=[b]))['allowed'])

    def test_offset_date_boundary(self):
        b = booking(start='2026-10-20T20:00:00-05:00', end='2026-10-20T21:00:00-05:00')
        self.assertFalse(evaluate(request(bookings=[b]))['allowed'])

    def test_fractional_seconds(self):
        c = booking('candidate', start='2026-10-21T01:00:00.000001Z', end='2026-10-21T02:00:00.1Z')
        self.assertEqual(evaluate(request(c))['start'], '2026-10-21T01:00:00.000001Z')

    def test_stable_order(self):
        bs = [booking('z'), booking('a')]
        one = evaluate(request(bookings=bs)); two = evaluate(request(bookings=bs[::-1]))
        self.assertEqual(one, two)
        self.assertEqual([x['record_id'] for x in one['conflicts']], ['a', 'z'])

    def test_extension_excludes_only_self(self):
        data = dict(operation='extend', bookings=[booking()], booking_id='existing', new_end='2026-10-21T12:00:00+09:00')
        before = copy.deepcopy(data)
        self.assertTrue(evaluate(data)['allowed']); self.assertEqual(data, before)
        data['bookings'].append(booking('next', start='2026-10-21T11:30:00+09:00', end='2026-10-21T12:30:00+09:00'))
        self.assertEqual(evaluate(data)['conflicts'][0]['record_id'], 'next')

    def test_extension_preserves_buffer(self):
        data = dict(operation='extend', bookings=[booking(buffer_after_minutes=30)], booking_id='existing', new_end='2026-10-21T12:00:00+09:00', unavailable=[booking('w', start='2026-10-21T12:15:00+09:00', end='2026-10-21T12:30:00+09:00')])
        self.assertFalse(evaluate(data)['allowed'])

    def test_extension_failure_cases(self):
        base = dict(operation='extend', bookings=[booking()], booking_id='existing', new_end='2026-10-21T12:00:00+09:00')
        for change in [{'booking_id':'missing'}, {'new_end':'2026-10-21T11:00:00+09:00'}, {'new_end':'2026-10-21T10:30:00+09:00'}, {'candidate':booking()}]:
            with self.subTest(change=change), self.assertRaises(ValidationError):
                evaluate(base | change)

    def test_timestamp_rejections(self):
        for value in ['2026-10-21T10:00:00', '2026-10-21', '2026-10-21 10:00:00Z', '2026-10-21T10:00Z',
                      '2026-02-30T10:00:00Z', '2026-10-21T10:00:60Z', '2026-10-21T10:00:00+01:60',
                      '2026-10-21T10:00:00+24:00', '2026-10-21T10:00:00-00:00', '2026-10-21T10:00:00.1234567Z',
                      '0001-01-01T00:00:00+01:00', '9999-12-31T23:00:00-02:00', None, True, 123]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                evaluate(request(booking('candidate', start=value)))

    def test_bad_intervals(self):
        for end in ['2026-10-21T10:00:00+09:00', '2026-10-21T09:00:00+09:00']:
            with self.assertRaises(ValidationError): evaluate(request(booking('candidate', end=end)))

    def test_bad_buffers(self):
        for value in [-1, 1.5, True, '1', None, 10081]:
            for name in ['buffer_before_minutes', 'buffer_after_minutes']:
                with self.subTest(value=value), self.assertRaises(ValidationError):
                    evaluate(request(booking('candidate', **{name:value})))

    def test_buffer_overflow(self):
        for c in [booking('c',start='0001-01-01T00:00:00Z',end='0001-01-01T01:00:00Z',buffer_before_minutes=1),
                  booking('c',start='9999-12-31T22:00:00Z',end='9999-12-31T23:59:59Z',buffer_after_minutes=1)]:
            with self.assertRaises(ValidationError): evaluate(request(c))

    def test_duplicate_ids(self):
        for p in [request(bookings=[booking(), booking()]), request(booking('existing'),[booking()]), request(bookings=[booking()], unavailable=[booking()])]:
            with self.assertRaises(ValidationError): evaluate(p)

    def test_identifier_validation(self):
        for value in ['', ' ', '\n', 'a\x7f', '\ud800', 'x'*129, 1, None]:
            with self.subTest(value=repr(value)), self.assertRaises(ValidationError):
                evaluate(request(booking(value)))

    def test_japanese_identifiers(self):
        self.assertEqual(evaluate(request(booking('予約一',resource='会議室')))['candidate_id'], '予約一')

    def test_invalid_shapes(self):
        for p in [None, [], {}, {'operation':'unknown'}, request() | {'extra':1}, request() | {'bookings':{}}, request() | {'unavailable':None}, request() | {'candidate':[]}, request() | {'candidate':{}}, request() | {'bookings':[None]}, request() | {'bookings':[booking() | {'unknown': 1}]}]:
            with self.subTest(p=p), self.assertRaises(ValidationError): evaluate(p)

    def test_validate_other_resources_too(self):
        with self.assertRaises(ValidationError): evaluate(request(bookings=[booking(resource='other',end='bad')]))

    def test_record_limit(self):
        with self.assertRaises(ValidationError): evaluate(request(bookings=[None]*10001))

    def test_windows_cannot_have_buffer(self):
        with self.assertRaises(ValidationError): evaluate(request(unavailable=[booking(buffer_after_minutes=1)]))


if __name__ == '__main__': unittest.main()
