"""Seeded standard-library property checks with an independent minute oracle."""
from datetime import datetime, timedelta, timezone
import random
import unittest
from booking_rules import evaluate
from test_core import booking, request


class PropertyTests(unittest.TestCase):
    def test_interval_oracle_300_cases(self):
        randomizer = random.Random(82341)
        epoch = datetime(2026, 1, 1, tzinfo=timezone.utc)
        def stamp(minutes):
            return (epoch + timedelta(minutes=minutes)).isoformat()
        for _ in range(300):
            a, b = randomizer.randint(0, 100), randomizer.randint(0, 100)
            ae, be = a + randomizer.randint(1, 50), b + randomizer.randint(1, 50)
            before_a, after_a, before_b, after_b = [randomizer.randint(0, 15) for _ in range(4)]
            c = booking('candidate',start=stamp(a),end=stamp(ae),buffer_before_minutes=before_a,buffer_after_minutes=after_a)
            other = booking(start=stamp(b),end=stamp(be),buffer_before_minutes=before_b,buffer_after_minutes=after_b)
            expected_conflict = a-before_a < be+after_b and b-before_b < ae+after_a
            self.assertEqual(evaluate(request(c,[other]))['allowed'],not expected_conflict)

    def test_maximum_record_count(self):
        records = [booking(str(i),resource='unrelated') for i in range(10000)]
        self.assertTrue(evaluate(request(bookings=records))['allowed'])

    def test_time_translation_preserves_decision(self):
        epoch = datetime(2026, 1, 1, tzinfo=timezone.utc)
        def make(shift):
            def stamp(n): return (epoch+timedelta(minutes=n+shift)).isoformat()
            return request(booking('candidate',start=stamp(60),end=stamp(120),buffer_before_minutes=15),
                           [booking(start=stamp(0),end=stamp(50))])
        a=evaluate(make(0)); b=evaluate(make(100000))
        self.assertEqual(a['allowed'],b['allowed'])
        self.assertEqual(a['conflicts'][0]['reason'],b['conflicts'][0]['reason'])
