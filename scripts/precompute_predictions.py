"""
Pre-compute all expensive prediction fields and save to data_files/predictions_cache.json.

Runs nightly via GitHub Actions after the data refresh and before the app serves users.
The Streamlit pages load from this cache on startup, avoiding live Elo training and
prediction loops that add 2-8 seconds to every cold-start.

Fields saved:
  - match_predictions: list of prediction dicts for all upcoming fixtures
  - upset_watch: ranked list of underdog win probabilities
  - group_draw: Elo ratings, avg Elo, and sim advancement % per group
  - best_bets: value bets vs real market odds (same as best_bets_today.json but richer)
  - top_teams: top 20 teams by Elo rating
  - generated_at: ISO timestamp
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv()

DATA = ROOT / "data_files"
OUTPUT = DATA / "predictions_cache.json"

ODDS_LINE_1X2_MARGIN = 1.05   # proxy overround for 1X2 benchmark
ODDS_OU_LINE         = 1.91   # standard O/U decimal line
VALUE_THRESHOLD      = 0.04   # min edge to flag


def _safe_float(val, default=0.0):
    try:
        return float(val)
    except Exception:
        return default


def _tier(edge: float) -> str:
    if edge >= 0.08: return "Elite"
    if edge >= 0.05: return "Strong"
    if edge >= 0.04: return "Good"
    return "Standard"


def run():
    print("[precompute] Loading match data and building predictor …")
    from goallineiq_utils.api_client import (
        get_all_wc_matches, get_upcoming_matches, get_match_odds_from_snapshot,
    )
    from goallineiq_utils.models import build_predictor, WC2026_GROUPS, FALLBACK_ELO

    all_matches  = get_all_wc_matches()
    predictor    = build_predictor(all_matches)
    upcoming     = get_upcoming_matches(n=30)

    # ── Group Draw ────────────────────────────────────────────────────────────
    print("[precompute] Computing group draw strength …")
    sim_adv: dict[str, float] = {}
    sim_r32: dict[str, float] = {}
    sim_win: dict[str, float] = {}
    sim_path = DATA / "tournament_simulation.json"
    if sim_path.exists():
        try:
            sim_data = json.loads(sim_path.read_text(encoding="utf-8"))
            for r in sim_data.get("results", []):
                t = r["team"]
                sim_adv[t] = r.get("Group Stage", 100.0)
                sim_r32[t] = r.get("Round of 32", 0.0)
                sim_win[t] = r.get("Winner", r.get("Winner %", 0.0))
        except Exception:
            pass

    group_draw = {}
    for gname, gteams in sorted(WC2026_GROUPS.items()):
        entries = []
        for team in gteams:
            try:
                p = predictor.predict(team, team, neutral=True)
                elo = int(p["home_elo"])
            except Exception:
                elo = FALLBACK_ELO.get(team, 1500)
            entries.append({
                "team": team,
                "elo": elo,
                "adv_pct": round(sim_adv.get(team, 100.0), 1),
                "r32_pct":  round(sim_r32.get(team, 0.0), 1),
                "win_pct":  round(sim_win.get(team, 0.0), 2),
            })
        entries.sort(key=lambda x: x["elo"], reverse=True)
        avg_elo = sum(e["elo"] for e in entries) / len(entries)
        group_draw[gname] = {
            "teams": entries,
            "avg_elo": round(avg_elo, 1),
        }

    # ── Top teams by Elo ──────────────────────────────────────────────────────
    print("[precompute] Computing top teams by Elo …")
    ratings_df = predictor.get_ratings_df().head(20)
    top_teams = ratings_df[["team", "elo", "rank"]].to_dict(orient="records")

    # ── Match predictions + upset watch + best bets ───────────────────────────
    print("[precompute] Computing match predictions …")
    match_predictions = []
    upset_watch = []
    best_bets = []

    if upcoming is not None and not upcoming.empty:
        for _, row in upcoming.iterrows():
            home = str(row.get("home_team", "")).strip()
            away = str(row.get("away_team", "")).strip()
            if not home or not away:
                continue

            try:
                pred = predictor.predict(home, away, neutral=True)
            except Exception:
                continue

            hw_p, dr_p, aw_p = pred["home_win"], pred["draw"], pred["away_win"]
            ou = pred.get("ou", {})
            ou25 = ou.get(2.5, {"over": 0.5, "under": 0.5})
            xg_total = round(pred["home_xg"] + pred["away_xg"], 3)

            game_date_raw = row.get("date") or str(date.today())
            game_date = str(game_date_raw)[:10]

            # Real snapshot odds
            snap = get_match_odds_from_snapshot(home, away)
            real_odds = snap.get("best_h2h", {}) if snap else {}
            real_ou   = snap.get("best_ou", {}) if snap else {}
            odds_source = "real" if real_odds.get("home") else "proxy"

            # Benchmark: use real odds when available, else proxy
            bm_h = (1.0 / real_odds["home"]) if real_odds.get("home") else (hw_p / ODDS_LINE_1X2_MARGIN)
            bm_d = (1.0 / real_odds["draw"]) if real_odds.get("draw") else (dr_p / ODDS_LINE_1X2_MARGIN)
            bm_a = (1.0 / real_odds["away"]) if real_odds.get("away") else (aw_p / ODDS_LINE_1X2_MARGIN)
            bm_ou_over  = (1.0 / real_ou["over"])  if real_ou.get("over")  else (1.0 / ODDS_OU_LINE)
            bm_ou_under = (1.0 / real_ou["under"]) if real_ou.get("under") else (1.0 / ODDS_OU_LINE)

            match_entry = {
                "home_team":  home,
                "away_team":  away,
                "date":       game_date,
                "round":      str(row.get("round", "")),
                "venue":      str(row.get("venue", "")),
                "city":       str(row.get("city", "")),
                "home_win":   round(hw_p, 4),
                "draw":       round(dr_p, 4),
                "away_win":   round(aw_p, 4),
                "home_xg":    pred["home_xg"],
                "away_xg":    pred["away_xg"],
                "xg_total":   xg_total,
                "home_elo":   int(pred["home_elo"]),
                "away_elo":   int(pred["away_elo"]),
                "ou_over_2_5":    round(ou25["over"], 4),
                "ou_under_2_5":   round(ou25["under"], 4),
                "ou_over_1_5":    round(ou.get(1.5, {}).get("over", 0), 4),
                "ou_over_3_5":    round(ou.get(3.5, {}).get("over", 0), 4),
                "top_scorelines": pred.get("top_scorelines", [])[:5],
                "fair_h": round(1/hw_p, 2) if hw_p else 0,
                "fair_d": round(1/dr_p, 2) if dr_p else 0,
                "fair_a": round(1/aw_p, 2) if aw_p else 0,
                "mkt_h_odds": round(1/bm_h, 2) if bm_h else 0,
                "mkt_d_odds": round(1/bm_d, 2) if bm_d else 0,
                "mkt_a_odds": round(1/bm_a, 2) if bm_a else 0,
                "h_edge":  round(hw_p - bm_h, 4),
                "d_edge":  round(dr_p - bm_d, 4),
                "a_edge":  round(aw_p - bm_a, 4),
                "ou_over_edge":  round(ou25["over"]  - bm_ou_over,  4),
                "ou_under_edge": round(ou25["under"] - bm_ou_under, 4),
                "odds_source":   odds_source,
            }
            match_predictions.append(match_entry)

            # Upset watch
            elo_h, elo_a = pred["home_elo"], pred["away_elo"]
            if elo_h < elo_a:
                underdog, fav = home, away
                upset_p  = hw_p
                elo_gap  = elo_a - elo_h
                u_xg     = pred["home_xg"]
            else:
                underdog, fav = away, home
                upset_p  = aw_p
                elo_gap  = elo_h - elo_a
                u_xg     = pred["away_xg"]
            upset_watch.append({
                "date":     game_date,
                "match":    f"{home} vs {away}",
                "favourite": fav,
                "underdog":  underdog,
                "elo_gap":  int(elo_gap),
                "upset_pct": round(upset_p * 100, 1),
                "underdog_xg": round(u_xg, 3),
            })

            # Best bets
            for label, prob, mkt_imp, bet_type in [
                (f"{home} Win", hw_p, bm_h, "1X2"),
                ("Draw",        dr_p, bm_d, "1X2"),
                (f"{away} Win", aw_p, bm_a, "1X2"),
                ("Over 2.5",   ou25["over"],  bm_ou_over,  "O/U"),
                ("Under 2.5",  ou25["under"], bm_ou_under, "O/U"),
            ]:
                edge = prob - mkt_imp
                if edge >= VALUE_THRESHOLD:
                    best_bets.append({
                        "game_date":  game_date,
                        "game":       f"{home} vs {away}",
                        "bet_type":   bet_type,
                        "pick":       label,
                        "confidence": round(prob, 4),
                        "edge":       round(edge, 4),
                        "tier":       _tier(edge),
                        "xg_total":   xg_total if bet_type == "O/U" else None,
                        "home_elo":   int(pred["home_elo"]),
                        "away_elo":   int(pred["away_elo"]),
                        "odds_source": odds_source,
                        "notes":      f"xG {pred['home_xg']:.2f}–{pred['away_xg']:.2f}  |  Elo {int(pred['home_elo'])} vs {int(pred['away_elo'])}",
                    })

    upset_watch.sort(key=lambda x: x["upset_pct"], reverse=True)
    best_bets.sort(key=lambda x: x["edge"], reverse=True)

    # ── Write cache ───────────────────────────────────────────────────────────
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "match_predictions": match_predictions,
        "upset_watch": upset_watch,
        "group_draw": group_draw,
        "top_teams": top_teams,
        "best_bets": best_bets[:30],
    }
    DATA.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"[precompute] Wrote predictions_cache.json — "
          f"{len(match_predictions)} matches, {len(upset_watch)} upset candidates, "
          f"{len(best_bets)} value bets")


if __name__ == "__main__":
    run()
