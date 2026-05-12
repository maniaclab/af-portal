"""Configure sys.path so portal.downtime can be imported without the Flask app."""

import sys
from pathlib import Path

# Allow `import downtime` to resolve portal/downtime.py directly,
# bypassing portal/__init__.py (which eagerly loads Flask + portal.conf).
sys.path.insert(0, str(Path(__file__).parent.parent / "portal"))
