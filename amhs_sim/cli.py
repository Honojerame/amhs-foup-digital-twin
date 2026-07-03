from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .simulation import demo_fab


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AMHS FOUP transport digital twin")
    parser.add_argument("--duration", type=float, default=120.0, help="Maximum simulation seconds")
    parser.add_argument("--telemetry", type=Path, help="Optional telemetry CSV output")
    args = parser.parse_args()

    fab = demo_fab()
    summary = fab.run(args.duration)
    print(json.dumps(summary, indent=2))

    if args.telemetry:
        args.telemetry.parent.mkdir(parents=True, exist_ok=True)
        rows = fab.telemetry_dicts()
        with args.telemetry.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    main()

