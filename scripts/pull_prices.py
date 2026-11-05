"""Download (or refresh with --refresh) daily prices from Yahoo and FRED into data/raw/prices/."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from hormuz.prices import pull_all  # noqa: E402

for (source, name), st in pull_all(refresh="--refresh" in sys.argv).items():
    print(f"{source:5s} {name:6s} {st}")
