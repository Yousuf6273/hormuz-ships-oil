"""Refresh the newest data: last 2 months of GFW crossings, FRED prices (and Yahoo if reachable).

Add --publish to also rebuild the website and push it to GitHub Pages.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hormuz.pipeline import build_daily, refresh_recent_gfw  # noqa: E402
from hormuz.prices import YAHOO, pull_fred, pull_yahoo  # noqa: E402

refresh_recent_gfw()
for name in YAHOO:
    pull_fred(name)
    print(f"FRED {name}: ok", flush=True)
    try:
        pull_yahoo(name, tries=1)
        print(f"Yahoo {name}: ok", flush=True)
    except Exception as e:  # Yahoo is often blocked or rate-limited; FRED covers it
        print(f"Yahoo {name}: skipped ({str(e)[:60]})", flush=True)
d = build_daily()
print(f"daily crossings rebuilt: {d.index.min().date()} -> {d.index.max().date()}", flush=True)
subprocess.run([sys.executable, str(ROOT / "scripts/build_table.py")], check=True)
if "--publish" in sys.argv:
    subprocess.run([sys.executable, str(ROOT / "scripts/publish_site.py")], check=True)
