"""Nightly World Cup data snapshot for GoallineIQ.

This script pulls the live 2026 tournament data and writes timestamped
CSV/JSON snapshots under data_files/nightly_snapshots/YYYY-MM-DD/.
It is safe to run outside the tournament window; by default it exits
without writing files unless the date is within the pre/post tournament
window.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from goallineiq_utils.api_client import (  # noqa: E402
    get_all_wc_matches,
    get_current_standings,
    get_historical_top_scorers,
    get_upcoming_matches,
)

WINDOW_START = date(2026, 6, 4)
WINDOW_END = date(2026, 7, 26)
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data_files" / "nightly_snapshots"


def in_tournament_window(today: date) -> bool:
    return WINDOW_START <= today <= WINDOW_END


def write_dataframe(df: pd.DataFrame, path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    if df is None or df.empty:
        df = pd.DataFrame()
    df.to_csv(path, index=False)
    return len(df)


def write_json(payload: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def build_snapshot(output_dir: Path) -> dict[str, Any]:
    snapshot_date = datetime.now(timezone.utc).date().isoformat()
    snapshot_dir = output_dir / snapshot_date
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    matches_all = get_all_wc_matches()
    upcoming = get_upcoming_matches(n=50)
    standings = get_current_standings()
    scorers = get_historical_top_scorers()

    counts = {
        "matches_all": write_dataframe(matches_all, snapshot_dir / "matches_all.csv"),
        "upcoming_matches": write_dataframe(upcoming, snapshot_dir / "upcoming_matches.csv"),
        "standings": write_dataframe(standings, snapshot_dir / "standings.csv"),
        "top_scorers": write_dataframe(scorers, snapshot_dir / "top_scorers.csv"),
    }

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "window_start": WINDOW_START.isoformat(),
        "window_end": WINDOW_END.isoformat(),
        "snapshot_date": snapshot_date,
        "counts": counts,
        "files": list(counts.keys()),
    }
    write_json(manifest, snapshot_dir / "manifest.json")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Pull nightly World Cup data snapshots.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where snapshot folders should be written.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run even if today's date is outside the tournament window.",
    )
    args = parser.parse_args()

    today = datetime.now(timezone.utc).date()
    if not args.force and not in_tournament_window(today):
        print(f"Skipping snapshot: {today.isoformat()} is outside {WINDOW_START.isoformat()}..{WINDOW_END.isoformat()}")
        return 0

    manifest = build_snapshot(args.output_dir)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
