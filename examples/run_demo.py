"""Cross-platform real CLI smoke demo using entirely synthetic data."""
from pathlib import Path
import json
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
raw = (root / 'examples' / 'buffer-conflict.json').read_bytes()
run = subprocess.run([sys.executable, '-m', 'booking_rules'], input=raw, capture_output=True, cwd=root, timeout=15)
assert run.returncode == 1, run.stderr
result = json.loads(run.stdout.decode('utf-8'))
assert result['conflicts'][0]['reason'] == 'BUFFER_OVERLAP'
# A demo should also display correctly in a legacy Windows console.
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
