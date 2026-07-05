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


def _latest_odds_snapshot() -> list | None:
    """Load today's odds.json from the nightly snapshot directory."""
    snap_dir = DATA / "nightly_snapshots"
    if not snap_dir.exists():
        return None
    # Walk dated subdirs newest-first
    for dated_dir in sorted(snap_dir.iterdir(), reverse=True):
        path = dated_dir / "odds.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return data
            except Exception:
                continue
    return None


def _name_key(name: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _find_event(raw_odds: list, home: str, away: str) -> dict | None:
    """Fuzzy-match a (home, away) pair against the raw Odds API event list."""
    hk, ak = _name_key(home), _name_key(away)
    for ev in raw_odds:
        ek_h = _name_key(ev.get("home_team", ""))
        ek_a = _name_key(ev.get("away_team", ""))
        if (hk in ek_h or ek_h in hk) and (ak in ek_a or ek_a in ak):
            return ev
        if (ak in ek_h or ek_h in ak) and (hk in ek_a or ek_a in hk):
            return ev
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

    # ── Load real odds from The Odds API snapshot ─────────────────────────
    raw_odds = _latest_odds_snapshot() or []

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
        ou = pred.get("ou", {})
        ou25 = ou.get(2.5, {})

        # Find matching event in Odds API snapshot
        event = _find_event(raw_odds, home, away)
        flipped = False
        if event and _name_key(event.get("home_team","")) != _name_key(home):
            flipped = True

        # Extract best odds from all bookmakers
        best_h = best_d = best_a = 0.0
        best_ou_over = best_ou_under = 0.0
        if event:
            for bm in event.get("bookmakers", []):
                for mkt in bm.get("markets", []):
                    mkt_key = mkt.get("key", "")
                    if mkt_key == "h2h":
                        for o in mkt.get("outcomes", []):
                            o_key = _name_key(o.get("name", ""))
                            price = float(o.get("price", 0))
                            if "draw" in o_key:
                                best_d = max(best_d, price)
                            elif o_key in _name_key(event.get("home_team", "")):
                                if flipped:
                                    best_a = max(best_a, price)
                                else:
                                    best_h = max(best_h, price)
                            else:
                                if flipped:
                                    best_h = max(best_h, price)
                                else:
                                    best_a = max(best_a, price)
                    elif mkt_key == "totals":
                        for o in mkt.get("outcomes", []):
                            if abs(float(o.get("point", 0)) - 2.5) < 0.01:
                                nm = o.get("name", "").lower()
                                if "over" in nm:
                                    best_ou_over = max(best_ou_over, float(o.get("price", 0)))
                                elif "under" in nm:
                                    best_ou_under = max(best_ou_under, float(o.get("price", 0)))

        # Build candidate bets: 1X2 + O/U
        candidates: list[tuple] = []
        if best_h:
            candidates.append(("moneyline", home, hw, best_h))
        if best_d:
            candidates.append(("draw", "Draw", dr, best_d))
        if best_a:
            candidates.append(("moneyline", away, aw, best_a))
        if best_ou_over and ou25.get("over"):
            candidates.append(("over_2.5", f"Over 2.5 ({home} vs {away})",
                               ou25["over"], best_ou_over))
        if best_ou_under and ou25.get("under"):
            candidates.append(("under_2.5", f"Under 2.5 ({home} vs {away})",
                               ou25["under"], best_ou_under))

        for bet_type, pick, model_prob, market_dec in candidates:
            if not market_dec or market_dec <= 0:
                continue
            market_implied = 1.0 / _safe_float(market_dec, 1.0)
            edge = model_prob - market_implied
            dk_odds = _decimal_to_american(_safe_float(market_dec))

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
