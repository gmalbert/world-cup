"""
Export daily best bets for the Sports Picks Grid aggregator.

Uses the GoallineIQ predictor (goallineiq_utils.models) to evaluate upcoming
World Cup 2026 fixtures, compares model probabilities against odds from
data_files/nightly_snapshots/ (latest snapshot), and writes
data_files/best_bets_today.json in the unified schema.

If no odds data is available the script writes an empty-bets file so the
Sports Picks Grid degrades gracefully.

Usage:
    python scripts/export_best_bets.py
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATA = ROOT / "data_files"
SPORT = "World Cup"
MODEL_VERSION = "1.0.0"
EV_THRESHOLD = 0.04

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tier_from_edge(edge: float) -> str:
    if edge >= 0.08:
        return "Elite"
    if edge >= 0.04:
        return "Strong"
    if edge >= 0.03:
        return "Good"
    return "Standard"


def _safe_float(val, default: float = 0.0) -> float:
    try:
        return float(val)
    except Exception:
        return default


def _decimal_to_american(dec: float) -> int | None:
    try:
        dec = float(dec)
        if dec <= 1.0:
            return None
        if dec >= 2.0:
            return int(round((dec - 1) * 100))
        return int(round(-100 / (dec - 1)))
    except Exception:
        return None


def _latest_snapshot() -> dict | None:
    """Return the most recent JSON odds snapshot, or None if none exist."""
    snap_dir = DATA / "nightly_snapshots"
    if not snap_dir.exists():
        return None
    files = sorted(snap_dir.glob("*.json"), reverse=True)
    for f in files:
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def export() -> None:
    bets: list[dict] = []

    # ── Try to load the predictor ─────────────────────────────────────────
    try:
        from goallineiq_utils.api_client import get_all_wc_matches, get_upcoming_matches
        from goallineiq_utils.models import build_predictor

        all_matches = get_all_wc_matches()
        predictor = build_predictor(all_matches)
        upcoming = get_upcoming_matches(n=20)
    except Exception as e:
        print(f"[world-cup export] Could not load predictor: {e} — writing empty bets")
        _write([], f"predictor unavailable: {e}")
        return

    if upcoming is None or (hasattr(upcoming, "empty") and upcoming.empty):
        print("[world-cup export] No upcoming fixtures found — writing empty bets")
        _write([], "no upcoming fixtures")
        return

    # ── Load latest odds snapshot (optional) ─────────────────────────────
    snap = _latest_snapshot()
    # snap is expected to be a dict keyed by match_id or fixture string
    odds_lookup: dict[str, dict] = snap if isinstance(snap, dict) else {}

    for _, row in upcoming.iterrows():
        home = str(row.get("home_team", "")).strip()
        away = str(row.get("away_team", "")).strip()
        if not home or not away:
            continue

        game_label = f"{home} vs {away}"
        game_date_raw = row.get("date") or row.get("kickoff") or str(date.today())
        try:
            game_date = str(game_date_raw)[:10]
        except Exception:
            game_date = str(date.today())

        try:
            pred = predictor.predict(home, away, neutral=True)
        except Exception:
            continue

        hw = _safe_float(pred.get("home_win", 0))
        dr = _safe_float(pred.get("draw", 0))
        aw = _safe_float(pred.get("away_win", 0))

        match_odds = odds_lookup.get(game_label, {})

        # Build candidate bets: home / draw / away
        candidates = [
            ("moneyline", home, hw, match_odds.get("home_dec")),
            ("draw", "Draw", dr, match_odds.get("draw_dec")),
            ("moneyline", away, aw, match_odds.get("away_dec")),
        ]

        for bet_type, pick, model_prob, market_dec in candidates:
            if market_dec:
                market_implied = 1.0 / _safe_float(market_dec, 1.0)
                edge = model_prob - market_implied
                dk_odds = _decimal_to_american(_safe_float(market_dec))
            else:
                # No odds available — skip value calculation
                continue

            if edge < EV_THRESHOLD:
                continue

            tier = _tier_from_edge(edge)
            bets.append(
                {
                    "game_date": game_date,
                    "game": game_label,
                    "game_time": None,
                    "bet_type": bet_type,
                    "pick": pick,
                    "confidence": round(min(max(model_prob, 0.0), 1.0), 4),
                    "edge": round(edge, 4),
                    "odds": dk_odds,
                    "tier": tier,
                    "notes": (
                        f"Elo: {int(pred.get('home_elo',0))} vs {int(pred.get('away_elo',0))}  |  "
                        f"xG: {pred.get('home_xg',0):.2f}–{pred.get('away_xg',0):.2f}"
                    ),
                }
            )

    bets.sort(key=lambda b: b["edge"], reverse=True)
    _write(bets)


def _write(bets: list[dict], notes: str = "") -> None:
    payload = {
        "meta": {
            "sport": SPORT,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "model_version": MODEL_VERSION,
            "season": str(date.today().year),
            "notes": notes,
        },
        "bets": bets,
    }
    out = DATA / "best_bets_today.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[world-cup export] Wrote {len(bets)} bets → {out}")


if __name__ == "__main__":
    export()
