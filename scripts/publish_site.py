"""Rebuild the website and push it to GitHub Pages. Commits the docs/ folder only, and only if it changed.

Run:  .venv/bin/python scripts/publish_site.py   (the dashboard's Update button runs this too)
The live site picks up the push in about a minute; its Refresh button then shows the new data.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


subprocess.run([sys.executable, str(ROOT / "scripts/build_site.py")], cwd=ROOT, check=True)
git("add", "docs")
if git("diff", "--cached", "--quiet", "--", "docs").returncode == 0:
    print("Website already up to date: nothing to publish.", flush=True)
    sys.exit(0)

c = git("commit", "-m", "Update website data", "--", "docs")
if c.returncode != 0:
    sys.exit(f"Commit failed: {c.stderr.strip() or c.stdout.strip()}")
p = git("push")
if p.returncode != 0:
    sys.exit(f"Push to GitHub failed: {p.stderr.strip()[-300:]}")
print("Published to GitHub. The website updates in about a minute: "
      "https://yousuf6273.github.io/hormuz-ships-oil/", flush=True)
