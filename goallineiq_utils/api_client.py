"""
API Client module for GoallineIQ.
Handles BALLDONTLIE FIFA API, API-Football, and openfootball GitHub data.
Covers World Cup tournaments: 2010, 2014, 2018, 2022, 2026.
"""
import os
import requests
import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timedelta
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ────────────────────────────────────────────────────────────────
BALLDONTLIE_KEY = os.getenv("BALLDONTLIE_API_KEY", "")
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "")
SPORTS_DB_KEY = os.getenv("THE_SPORTS_DB_KEY", "123")

# ── Base URLs ────────────────────────────────────────────────────────────────
BDL_BASE = "https://fifa.balldontlie.io/api/v1"
APF_BASE = "https://v3.football.api-sports.io"
OPENFOOTBALL_BASE = "https://raw.githubusercontent.com/openfootball/worldcup.json/master"

# ── WC seasons (data pull covers 2010–2026) ──────────────────────────────────
WC_SEASONS = [2010, 2014, 2018, 2022, 2026]
WC_NAMES = {
    2010: "South Africa 2010",
    2014: "Brazil 2014",
    2018: "Russia 2018",
    2022: "Qatar 2022",
    2026: "USA/Canada/Mexico 2026",
}


# ══════════════════════════════════════════════════════════════════════════════
# OPENFOOTBALL — free historical data (2010, 2014, 2018, 2022)
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_openfootball_wc(year: int) -> Optional[Dict]:
    """Fetch World Cup data from openfootball GitHub. No API key required."""
    url = f"{OPENFOOTBALL_BASE}/{year}/worldcup.json"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def _parse_openfootball(data: Dict, year: int) -> pd.DataFrame:
    """Parse openfootball JSON into a flat DataFrame.

    Actual schema (all years):
      data["matches"] — flat list; team1/team2 are strings;
      score.ft = [home, away]; ground is a string; round/group are strings.
    """
    if not data:
        return pd.DataFrame()

    rows = []
    for m in data.get("matches", []):
        score = m.get("score") or {}
        ft    = score.get("ft", [None, None])
        ht    = score.get("ht", [None, None])
        ground = m.get("ground", "") or ""

        rows.append({
            "source":        "openfootball",
            "season":        year,
            "tournament":    WC_NAMES.get(year, str(year)),
            "date":          m.get("date"),
            "round":         m.get("round", ""),
            "group":         m.get("group", m.get("round", "")),
            "home_team":     m.get("team1", ""),
            "away_team":     m.get("team2", ""),
            "home_code":     "",
            "away_code":     "",
            "home_goals":    ft[0] if ft and len(ft) > 0 and ft[0] is not None else None,
            "away_goals":    ft[1] if ft and len(ft) > 1 and ft[1] is not None else None,
            "home_goals_ht": ht[0] if ht and len(ht) > 0 and ht[0] is not None else None,
            "away_goals_ht": ht[1] if ht and len(ht) > 1 and ht[1] is not None else None,
            "venue":         ground,
            "city":          ground,  # Use venue as city fallback for openfootball
            "status":        "completed" if (ft and len(ft) > 0 and ft[0] is not None) else "scheduled",
            "home_xg":       None,
            "away_xg":       None,
        })
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════════
# BALLDONTLIE FIFA API
# ══════════════════════════════════════════════════════════════════════════════

class BallDontLieClient:
    """Client for the BALLDONTLIE FIFA World Cup API (2018, 2022, 2026)."""

    def __init__(self):
        self.base_url = BDL_BASE
        self.headers = {"Authorization": BALLDONTLIE_KEY} if BALLDONTLIE_KEY else {}

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        if not BALLDONTLIE_KEY:
            return None
        try:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            resp = requests.get(url, headers=self.headers, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response else 0
            if code == 401:
                st.warning("BALLDONTLIE: Invalid API key.")
            elif code == 429:
                st.warning("BALLDONTLIE: Rate limit reached — showing cached data.")
            return None
        except Exception:
            return None

    def _paginate(self, endpoint: str, params: Optional[Dict] = None) -> List[Dict]:
        """Fetch all pages from a cursor-paginated endpoint."""
        all_data: List[Dict] = []
        p = {**(params or {}), "per_page": 100}
        while True:
            result = self._get(endpoint, p)
            if not result:
                break
            all_data.extend(result.get("data", []))
            next_cursor = result.get("meta", {}).get("next_cursor")
            if not next_cursor:
                break
            p["cursor"] = next_cursor
        return all_data

    # ── Matches ──────────────────────────────────────────────────────────────

    @st.cache_data(ttl=300, show_spinner=False)
    def get_matches(_self, season: int) -> pd.DataFrame:
        data = _self._paginate("matches", {"season": season})
        return _self._parse_matches(data, season) if data else pd.DataFrame()

    def _parse_matches(self, data: List[Dict], season: int) -> pd.DataFrame:
        rows = []
        for m in data:
            home = m.get("home_team") or {}
            away = m.get("away_team") or {}
            score = m.get("scores") or m.get("score") or {}
            venue = m.get("venue") or {}
            round_d = m.get("round") or {}
            group_d = m.get("group") or {}

            rows.append({
                "source": "balldontlie",
                "id": m.get("id"),
                "season": season,
                "tournament": WC_NAMES.get(season, str(season)),
                "date": m.get("date") or m.get("datetime") or m.get("scheduled_at"),
                "round": round_d.get("name", "") if isinstance(round_d, dict) else str(round_d),
                "group": group_d.get("name", "") if isinstance(group_d, dict) else str(group_d),
                "home_team": home.get("name", ""),
                "away_team": away.get("name", ""),
                "home_code": home.get("code", ""),
                "away_code": away.get("code", ""),
                "home_goals": score.get("home_score") or score.get("home"),
                "away_goals": score.get("away_score") or score.get("away"),
                "venue": venue.get("name", "") if isinstance(venue, dict) else str(venue),
                "city": venue.get("city", "") if isinstance(venue, dict) else "",
                "status": m.get("status", "scheduled"),
                "home_xg": m.get("home_xg"),
                "away_xg": m.get("away_xg"),
            })
        return pd.DataFrame(rows)

    # ── Standings ─────────────────────────────────────────────────────────────

    @st.cache_data(ttl=120, show_spinner=False)
    def get_standings(_self, season: int) -> pd.DataFrame:
        result = _self._get("standings", {"season": season})
        if not result:
            return pd.DataFrame()
        return _self._parse_standings(result.get("data", result.get("response", [])))

    def _parse_standings(self, data: Any) -> pd.DataFrame:
        rows = []
        # Handle various response shapes
        groups = data if isinstance(data, list) else [data]
        for group in groups:
            gname = group.get("name", group.get("group", ""))
            entries = group.get("standings", group.get("teams", group.get("entries", [])))
            for s in entries:
                team = s.get("team") or {}
                rows.append({
                    "group": gname,
                    "team": team.get("name", s.get("team_name", "")),
                    "code": team.get("code", ""),
                    "logo": team.get("logo_url", team.get("image_url", "")),
                    "played": s.get("played", s.get("games_played", 0)),
                    "won": s.get("won", s.get("wins", 0)),
                    "drawn": s.get("drawn", s.get("draws", 0)),
                    "lost": s.get("lost", s.get("losses", 0)),
                    "goals_for": s.get("goals_for", s.get("gf", 0)),
                    "goals_against": s.get("goals_against", s.get("ga", 0)),
                    "goal_diff": s.get("goal_difference", s.get("gd", 0)),
                    "points": s.get("points", s.get("pts", 0)),
                    "form": s.get("form", ""),
                })
        return pd.DataFrame(rows)

    # ── Teams ─────────────────────────────────────────────────────────────────

    @st.cache_data(ttl=3600, show_spinner=False)
    def get_teams(_self, season: int) -> pd.DataFrame:
        data = _self._paginate("teams", {"season": season})
        if not data:
            return pd.DataFrame()
        rows = []
        for t in data:
            grp = t.get("group") or {}
            rows.append({
                "id": t.get("id"),
                "name": t.get("name", ""),
                "code": t.get("code", ""),
                "country": t.get("country", ""),
                "group": grp.get("name", "") if isinstance(grp, dict) else str(grp),
                "logo": t.get("logo_url", t.get("image_url", t.get("logo", ""))),
            })
        return pd.DataFrame(rows)

    # ── Players ───────────────────────────────────────────────────────────────

    @st.cache_data(ttl=3600, show_spinner=False)
    def get_players(_self, season: int) -> pd.DataFrame:
        data = _self._paginate("players", {"season": season})
        if not data:
            return pd.DataFrame()
        rows = []
        for p in data:
            team = p.get("team") or {}
            rows.append({
                "id": p.get("id"),
                "name": p.get("name", p.get("full_name", "")),
                "position": p.get("position", ""),
                "nationality": p.get("nationality", ""),
                "team": team.get("name", "") if isinstance(team, dict) else str(team),
                "jersey_number": p.get("jersey_number"),
            })
        return pd.DataFrame(rows)

    # ── Stats ─────────────────────────────────────────────────────────────────

    @st.cache_data(ttl=1800, show_spinner=False)
    def get_player_stats(_self, season: int) -> pd.DataFrame:
        data = _self._paginate("stats", {"season": season, "type": "player"})
        if not data:
            return pd.DataFrame()
        rows = []
        for s in data:
            player = s.get("player") or {}
            team = s.get("team") or {}
            rows.append({
                "player_id": player.get("id"),
                "player": player.get("name", ""),
                "team": team.get("name", "") if isinstance(team, dict) else str(team),
                "goals": s.get("goals", 0),
                "assists": s.get("assists", 0),
                "shots": s.get("shots", 0),
                "shots_on_target": s.get("shots_on_target", 0),
                "xg": s.get("xg"),
                "minutes": s.get("minutes_played", s.get("minutes", 0)),
                "appearances": s.get("appearances", s.get("games", 0)),
                "yellow_cards": s.get("yellow_cards", 0),
                "red_cards": s.get("red_cards", 0),
            })
        return pd.DataFrame(rows)

    @st.cache_data(ttl=1800, show_spinner=False)
    def get_team_stats(_self, season: int) -> pd.DataFrame:
        data = _self._paginate("stats", {"season": season, "type": "team"})
        if not data:
            return pd.DataFrame()
        rows = []
        for s in data:
            team = s.get("team") or {}
            rows.append({
                "team": team.get("name", "") if isinstance(team, dict) else str(team),
                "goals_for": s.get("goals_for", s.get("goals", 0)),
                "goals_against": s.get("goals_against", 0),
                "shots": s.get("shots", 0),
                "shots_on_target": s.get("shots_on_target", 0),
                "xg_for": s.get("xg_for", s.get("xg")),
                "xg_against": s.get("xg_against"),
                "possession": s.get("possession"),
                "pass_accuracy": s.get("pass_accuracy"),
                "appearances": s.get("games_played", s.get("matches", 0)),
            })
        return pd.DataFrame(rows)

    @st.cache_data(ttl=1800, show_spinner=False)
    def get_match_odds(_self, match_id: int) -> Dict:
        result = _self._get(f"matches/{match_id}/odds")
        return result or {}


# ══════════════════════════════════════════════════════════════════════════════
# API-FOOTBALL (v3.football.api-sports.io)
# ══════════════════════════════════════════════════════════════════════════════

class APIFootballClient:
    """Client for API-Football — live scores, lineups, odds, H2H."""

    def __init__(self):
        self.base_url = APF_BASE
        self.headers = {"x-apisports-key": API_FOOTBALL_KEY} if API_FOOTBALL_KEY else {}
        self.wc_league = 1  # FIFA World Cup league ID

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        if not API_FOOTBALL_KEY:
            return None
        try:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            resp = requests.get(url, headers=self.headers, params=params, timeout=15)
            resp.raise_for_status()
            result = resp.json()
            errors = result.get("errors", {})
            if errors and (isinstance(errors, list) and errors or isinstance(errors, dict) and errors):
                return None
            return result
        except Exception:
            return None

    @st.cache_data(ttl=120, show_spinner=False)
    def get_fixtures(_self, season: int, status: Optional[str] = None, last: Optional[int] = None, next_n: Optional[int] = None) -> pd.DataFrame:
        params = {"league": _self.wc_league, "season": season}
        if status:
            params["status"] = status
        if last:
            params["last"] = last
        if next_n:
            params["next"] = next_n
        data = _self._get("fixtures", params)
        if not data:
            return pd.DataFrame()
        rows = []
        for f in data.get("response", []):
            fixture = f.get("fixture", {})
            teams = f.get("teams", {})
            goals = f.get("goals", {})
            league = f.get("league", {})
            rows.append({
                "id": fixture.get("id"),
                "date": fixture.get("date", ""),
                "status_short": fixture.get("status", {}).get("short", ""),
                "status_long": fixture.get("status", {}).get("long", ""),
                "elapsed": fixture.get("status", {}).get("elapsed"),
                "venue": fixture.get("venue", {}).get("name", ""),
                "city": fixture.get("venue", {}).get("city", ""),
                "home_team": teams.get("home", {}).get("name", ""),
                "away_team": teams.get("away", {}).get("name", ""),
                "home_id": teams.get("home", {}).get("id"),
                "away_id": teams.get("away", {}).get("id"),
                "home_logo": teams.get("home", {}).get("logo", ""),
                "away_logo": teams.get("away", {}).get("logo", ""),
                "home_goals": goals.get("home"),
                "away_goals": goals.get("away"),
                "round": league.get("round", ""),
                "season": season,
            })
        return pd.DataFrame(rows)

    @st.cache_data(ttl=120, show_spinner=False)
    def get_standings(_self, season: int) -> pd.DataFrame:
        data = _self._get("standings", {"league": _self.wc_league, "season": season})
        if not data:
            return pd.DataFrame()
        rows = []
        for resp_item in data.get("response", []):
            for group_list in resp_item.get("league", {}).get("standings", []):
                for s in group_list:
                    rows.append({
                        "group": s.get("group", ""),
                        "rank": s.get("rank", 0),
                        "team": s.get("team", {}).get("name", ""),
                        "team_id": s.get("team", {}).get("id"),
                        "logo": s.get("team", {}).get("logo", ""),
                        "played": s.get("all", {}).get("played", 0),
                        "won": s.get("all", {}).get("win", 0),
                        "drawn": s.get("all", {}).get("draw", 0),
                        "lost": s.get("all", {}).get("lose", 0),
                        "goals_for": s.get("all", {}).get("goals", {}).get("for", 0),
                        "goals_against": s.get("all", {}).get("goals", {}).get("against", 0),
                        "goal_diff": s.get("goalsDiff", 0),
                        "points": s.get("points", 0),
                        "form": s.get("form", ""),
                    })
        return pd.DataFrame(rows)

    @st.cache_data(ttl=3600, show_spinner=False)
    def get_top_scorers(_self, season: int) -> pd.DataFrame:
        data = _self._get("players/topscorers", {"league": _self.wc_league, "season": season})
        if not data:
            return pd.DataFrame()
        rows = []
        for p in data.get("response", []):
            player = p.get("player", {})
            stats = (p.get("statistics") or [{}])[0]
            goals_d = stats.get("goals", {})
            shots_d = stats.get("shots", {})
            games_d = stats.get("games", {})
            rows.append({
                "name": player.get("name", ""),
                "nationality": player.get("nationality", ""),
                "photo": player.get("photo", ""),
                "team": stats.get("team", {}).get("name", ""),
                "goals": goals_d.get("total", 0) or 0,
                "assists": goals_d.get("assists", 0) or 0,
                "shots_total": shots_d.get("total", 0) or 0,
                "shots_on": shots_d.get("on", 0) or 0,
                "minutes": games_d.get("minutes", 0) or 0,
                "appearances": games_d.get("appearences", 0) or 0,
            })
        return pd.DataFrame(rows)

    @st.cache_data(ttl=1800, show_spinner=False)
    def get_fixture_odds(_self, fixture_id: int) -> pd.DataFrame:
        data = _self._get("odds", {"fixture": fixture_id})
        if not data:
            return pd.DataFrame()
        rows = []
        for item in data.get("response", []):
            for bm in item.get("bookmakers", []):
                bm_name = bm.get("name", "")
                for bet in bm.get("bets", []):
                    if bet.get("name") in ("Match Winner", "1X2"):
                        for odd in bet.get("values", []):
                            rows.append({
                                "bookmaker": bm_name,
                                "outcome": odd.get("value", ""),
                                "odd": float(odd.get("odd", 0) or 0),
                            })
        return pd.DataFrame(rows)

    @st.cache_data(ttl=86400, show_spinner=False)
    def get_h2h(_self, team1_id: int, team2_id: int, last: int = 15) -> pd.DataFrame:
        data = _self._get("fixtures/headtohead", {"h2h": f"{team1_id}-{team2_id}", "last": last})
        if not data:
            return pd.DataFrame()
        rows = []
        for f in data.get("response", []):
            fixture = f.get("fixture", {})
            teams = f.get("teams", {})
            goals = f.get("goals", {})
            league = f.get("league", {})
            rows.append({
                "date": fixture.get("date", ""),
                "home_team": teams.get("home", {}).get("name", ""),
                "away_team": teams.get("away", {}).get("name", ""),
                "home_goals": goals.get("home"),
                "away_goals": goals.get("away"),
                "venue": fixture.get("venue", {}).get("name", ""),
                "competition": league.get("name", ""),
            })
        return pd.DataFrame(rows)

    @st.cache_data(ttl=300, show_spinner=False)
    def get_fixture_stats(_self, fixture_id: int) -> pd.DataFrame:
        data = _self._get("fixtures/statistics", {"fixture": fixture_id})
        if not data:
            return pd.DataFrame()
        rows = []
        for team_stats in data.get("response", []):
            team_name = team_stats.get("team", {}).get("name", "")
            for stat in team_stats.get("statistics", []):
                rows.append({
                    "team": team_name,
                    "stat": stat.get("type", ""),
                    "value": stat.get("value"),
                })
        return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════════
# SINGLETON CLIENTS
# ══════════════════════════════════════════════════════════════════════════════
bdl_client = BallDontLieClient()
apf_client = APIFootballClient()


# ══════════════════════════════════════════════════════════════════════════════
# COMBINED DATA ACCESS
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600, show_spinner="Loading historical World Cup data…")
def get_all_wc_matches() -> pd.DataFrame:
    """
    Aggregate WC match data from all available sources.
    - 2010 & 2014: openfootball (free GitHub JSON)
    - 2018 & 2022: BALLDONTLIE with openfootball fallback
    - 2026: BALLDONTLIE with openfootball fallback
    """
    frames: List[pd.DataFrame] = []

    # Historical tournaments from openfootball
    for year in [2010, 2014]:
        raw = fetch_openfootball_wc(year)
        if raw:
            df = _parse_openfootball(raw, year)
            if not df.empty:
                frames.append(df)

    # BALLDONTLIE for 2018, 2022, 2026; fall back to openfootball
    for year in [2018, 2022, 2026]:
        df = bdl_client.get_matches(year)
        if df is not None and not df.empty:
            frames.append(df)
        else:
            raw = fetch_openfootball_wc(year)
            if raw:
                df = _parse_openfootball(raw, year)
                if not df.empty:
                    frames.append(df)

    _EMPTY_COLS = [
        "source", "season", "tournament", "date", "round", "group",
        "home_team", "away_team", "home_code", "away_code",
        "home_goals", "away_goals", "home_goals_ht", "away_goals_ht",
        "venue", "city", "status", "home_xg", "away_xg",
    ]
    if not frames:
        return pd.DataFrame(columns=_EMPTY_COLS)

    result = pd.concat(frames, ignore_index=True)
    if "date" in result.columns:
        result["date"] = pd.to_datetime(result["date"], errors="coerce", utc=True)
    for col in ("home_goals", "away_goals"):
        if col in result.columns:
            result[col] = pd.to_numeric(result[col], errors="coerce")
    return result


@st.cache_data(ttl=300, show_spinner=False)
def get_upcoming_matches(n: int = 20) -> pd.DataFrame:
    """Get the next N upcoming 2026 WC matches from any available source."""
    # BALLDONTLIE
    df = bdl_client.get_matches(2026)
    if df is not None and not df.empty and "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
        now = pd.Timestamp.utcnow()
        upcoming = df[df["status"].isin(["scheduled", "NS", "TBD", ""])
                      | df["date"].gt(now)]
        upcoming = upcoming.sort_values("date")
        if not upcoming.empty:
            return upcoming.head(n)

    # API-Football fallback
    df = apf_client.get_fixtures(2026, next_n=n)
    if df is not None and not df.empty and "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
        return df.sort_values("date").head(n)

    # openfootball fallback
    raw = fetch_openfootball_wc(2026)
    if raw:
        df = _parse_openfootball(raw, 2026)
        if not df.empty and "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
            now = pd.Timestamp.utcnow()
            return df[df["date"] >= now].sort_values("date").head(n)

    return pd.DataFrame()


@st.cache_data(ttl=120, show_spinner=False)
def get_current_standings() -> pd.DataFrame:
    """Get 2026 WC group standings, trying multiple sources."""
    df = bdl_client.get_standings(2026)
    if df is not None and not df.empty:
        return df
    df = apf_client.get_standings(2026)
    if df is not None and not df.empty:
        return df
    return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def get_historical_top_scorers() -> pd.DataFrame:
    """Aggregate top scorers across 2018, 2022, 2026 from BALLDONTLIE."""
    frames = []
    for year in [2018, 2022, 2026]:
        df = bdl_client.get_player_stats(year)
        if df is not None and not df.empty:
            df["season"] = year
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)
