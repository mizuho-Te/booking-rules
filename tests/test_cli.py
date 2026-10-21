import json
import os
import subprocess
import sys
import unittest
from booking_rules.__main__ import MAX_INPUT_BYTES
from test_core import request, booking


def run(raw, *args, cp1252=False):
    env = os.environ.copy()
    if cp1252: env['PYTHONIOENCODING'] = 'cp1252'; env['PYTHONUTF8'] = '0'
    return subprocess.run([sys.executable, '-m', 'booking_rules', *args], input=raw, capture_output=True, env=env, timeout=15)


class CliTests(unittest.TestCase):
    def test_allowed(self):
        r = run(json.dumps(request()).encode())
        self.assertEqual(r.returncode,0); self.assertTrue(json.loads(r.stdout)['allowed']); self.assertEqual(r.stderr,b'')

    def test_conflict(self):
        r = run(json.dumps(request(bookings=[booking()])).encode())
        self.assertEqual(r.returncode,1); self.assertFalse(json.loads(r.stdout)['allowed'])

    def test_utf8_on_legacy_windows_encoding(self):
        r = run(json.dumps(request(booking('予約')),ensure_ascii=False).encode('utf8'),cp1252=True)
        self.assertEqual(r.returncode,0); self.assertEqual(json.loads(r.stdout.decode('utf8'))['candidate_id'],'予約')

    def test_bad_inputs(self):
        for raw in [b'',b'{',b'\xff',b'{}{}',b'{"operation":"check","operation":"extend"}',b'{"operation":NaN}', b'['*2000+b']'*2000,b'{"n":'+b'9'*10000+b'}',b'{"operation":"check","bookings":[],"candidate":{"id":"\\ud800","resource_id":"x","start":"2026-01-01T00:00:00Z","end":"2026-01-01T01:00:00Z"}}']:
            with self.subTest(raw=raw[:30]):
                r=run(raw); self.assertEqual(r.returncode,2); self.assertEqual(json.loads(r.stdout)['error']['code'],'INVALID_INPUT'); self.assertEqual(r.stderr,b'')

    def test_input_limit(self):
        r = run(b' '*(MAX_INPUT_BYTES+1))
        self.assertEqual(r.returncode,2); self.assertIn('limit',json.loads(r.stdout)['error']['message'])

    def test_help_and_unknown_arg(self):
        self.assertEqual(run(b'','--help').returncode,0)
        self.assertEqual(run(b'','file.json').returncode,2)

    def test_output_determinism(self):
        p = request(bookings=[booking('z'),booking('a')]); a=run(json.dumps(p).encode())
        p['bookings'].reverse(); b=run(json.dumps(p).encode())
        self.assertEqual(a.stdout,b.stdout)

    def test_import_has_no_stream_side_effects(self):
        script = 'import sys; before=sys.stdout.encoding; import booking_rules; import booking_rules.__main__; assert before == sys.stdout.encoding'
        r=subprocess.run([sys.executable,'-c',script],capture_output=True,env=os.environ | {'PYTHONIOENCODING':'cp1252'},timeout=15)
        self.assertEqual(r.returncode,0)

if __name__ == '__main__': unittest.main()
