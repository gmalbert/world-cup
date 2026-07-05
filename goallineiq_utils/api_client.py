"""
API Client module for GoallineIQ.
Handles BALLDONTLIE FIFA API, API-Football, ESPN (unofficial), The Odds API,
and openfootball GitHub data.
Covers World Cup tournaments: 2010, 2014, 2018, 2022, 2026.
"""
import os
import json
import re
import requests
import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Any, Tuple
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ────────────────────────────────────────────────────────────────
BALLDONTLIE_KEY  = os.getenv("BALLDONTLIE_API_KEY", "")
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "")
SPORTS_DB_KEY    = os.getenv("THE_SPORTS_DB_KEY", "123")
ODDS_API_KEY     = os.getenv("ODDS_API_KEY", "")

# ── Base URLs ────────────────────────────────────────────────────────────────
BDL_BASE          = "https://fifa.balldontlie.io/api/v1"
APF_BASE          = "https://v3.football.api-sports.io"
OPENFOOTBALL_BASE = "https://raw.githubusercontent.com/openfootball/worldcup.json/master"
ESPN_BASE         = "https://site.api.espn.com/apis"
ODDS_API_BASE     = "https://api.the-odds-api.com/v4"

# ── Snapshot directory ───────────────────────────────────────────────────────
_REPO_ROOT     = Path(__file__).resolve().parent.parent
_SNAPSHOT_DIR  = _REPO_ROOT / "data_files" / "nightly_snapshots"

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

@st.cache_data(ttl=300, show_spinner=False)
def fetch_openfootball_wc(year: int) -> Optional[Dict]:
    """Fetch World Cup data from openfootball GitHub. No API key required."""
    url = f"{OPENFOOTBALL_BASE}/{year}/worldcup.json"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


_BRACKET_SLOT_RE = re.compile(r"^[WL](\d+)$", re.IGNORECASE)
_OPENFOOTBALL_TIME_RE = re.compile(
    r"^(\d{1,2}):(\d{2})\s+UTC([+-]\d{1,2})(?::?(\d{2}))?$",
    re.IGNORECASE,
)


def _openfootball_kickoff(match: Dict):
    """Return an offset-aware UTC kickoff when openfootball supplies a time."""
    date_value = match.get("date")
    time_value = str(match.get("time", "") or "").strip()
    parsed_time = _OPENFOOTBALL_TIME_RE.fullmatch(time_value)
    if not date_value or not parsed_time:
        return date_value
    try:
        hour, minute = int(parsed_time.group(1)), int(parsed_time.group(2))
        offset_hours = int(parsed_time.group(3))
        offset_minutes = int(parsed_time.group(4) or 0)
        if offset_hours < 0:
            offset_minutes *= -1
        venue_tz = timezone(timedelta(hours=offset_hours, minutes=offset_minutes))
        kickoff = datetime.strptime(str(date_value), "%Y-%m-%d").replace(
            hour=hour, minute=minute, tzinfo=venue_tz
        )
        return kickoff.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        return date_value


def _resolve_openfootball_bracket(matches: List[Dict]) -> List[Dict]:
    """Replace W76/L76-style slots once the referenced match has a winner.

    Openfootball numbers matches by their one-based position in the feed.  A
    knockout winner is taken from penalties first, then extra time, then full
    time.  Unplayed slots remain unresolved and are excluded from predictions.
    """
    outcomes: Dict[int, Tuple[str, str]] = {}
    resolved: List[Dict] = []

    for match_number, raw_match in enumerate(matches, start=1):
        match = dict(raw_match)
        for field in ("team1", "team2"):
            value = str(match.get(field, "") or "").strip()
            slot = _BRACKET_SLOT_RE.fullmatch(value)
            if slot:
                prior = outcomes.get(int(slot.group(1)))
                if prior:
                    match[field] = prior[0] if value.upper().startswith("W") else prior[1]

        team1 = str(match.get("team1", "") or "").strip()
        team2 = str(match.get("team2", "") or "").strip()
        score = match.get("score") or {}
        deciding_score = next(
            (score.get(key) for key in ("p", "et", "ft")
             if isinstance(score.get(key), list) and len(score[key]) >= 2
             and score[key][0] is not None and score[key][1] is not None
             and score[key][0] != score[key][1]),
            None,
        )
        if deciding_score and team1 and team2:
            if deciding_score[0] > deciding_score[1]:
                outcomes[match_number] = (team1, team2)
            else:
                outcomes[match_number] = (team2, team1)
        resolved.append(match)

    return resolved


def _resolved_fixture_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only fixtures whose participants are actual named teams."""
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df
    if not {"home_team", "away_team"}.issubset(df.columns):
        return pd.DataFrame()
    home = df["home_team"].fillna("").astype(str).str.strip()
    away = df["away_team"].fillna("").astype(str).str.strip()
    placeholders = home.str.fullmatch(_BRACKET_SLOT_RE) | away.str.fullmatch(_BRACKET_SLOT_RE)
    return df[home.ne("") & away.ne("") & ~placeholders].copy()


def _parse_openfootball(data: Dict, year: int) -> pd.DataFrame:
    """Parse openfootball JSON into a flat DataFrame.

    Actual schema (all years):
      data["matches"] — flat list; team1/team2 are strings;
      score.ft = [home, away]; ground is a string; round/group are strings.
    """
    if not data:
        return pd.DataFrame()

    rows = []
    for m in _resolve_openfootball_bracket(data.get("matches", [])):
        score = m.get("score") or {}
        ft    = score.get("ft", [None, None])
        ht    = score.get("ht", [None, None])
        ground = m.get("ground", "") or ""

        rows.append({
            "source":        "openfootball",
            "season":        year,
            "tournament":    WC_NAMES.get(year, str(year)),
            "date":          _openfootball_kickoff(m),
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
# ESPN UNOFFICIAL API  (no key required — replaces API-Football for live data)
# ══════════════════════════════════════════════════════════════════════════════

class ESPNClient:
    """Lightweight wrapper for the ESPN unofficial soccer API.

    No API key required; intended as a free replacement for API-Football
    standing and fixture data when that service is unavailable.
    """

    SPORT_PATH = "site/v2/sports/soccer/fifa.world"

    def _get(self, path: str, params: Optional[Dict] = None) -> Optional[Dict]:
        try:
            url = f"{ESPN_BASE}/{path}"
            r = requests.get(url, params=params or {}, timeout=12)
            r.raise_for_status()
            return r.json()
        except Exception:
            return None

    @st.cache_data(ttl=120, show_spinner=False)
    def get_scoreboard(_self) -> pd.DataFrame:
        """Live and recent scores from the ESPN scoreboard endpoint."""
        data = _self._get(f"{_self.SPORT_PATH}/scoreboard")
        if not data:
            return pd.DataFrame()
        rows = []
        for event in data.get("events", []):
            comp = (event.get("competitions") or [{}])[0]
            comps_teams = comp.get("competitors", [])
            home = next((t for t in comps_teams if t.get("homeAway") == "home"), {})
            away = next((t for t in comps_teams if t.get("homeAway") == "away"), {})
            status = event.get("status", {}).get("type", {})
            rows.append({
                "id": event.get("id"),
                "date": event.get("date"),
                "home_team": home.get("team", {}).get("displayName", ""),
                "away_team": away.get("team", {}).get("displayName", ""),
                "home_goals": home.get("score"),
                "away_goals": away.get("score"),
                "status": status.get("shortDetail", ""),
                "completed": status.get("completed", False),
                "venue": comp.get("venue", {}).get("fullName", ""),
                "city": comp.get("venue", {}).get("address", {}).get("city", ""),
            })
        return pd.DataFrame(rows)

    @st.cache_data(ttl=300, show_spinner=False)
    def get_schedule(_self, date_str: Optional[str] = None) -> pd.DataFrame:
        """Upcoming / recent schedule.  date_str format: 'YYYYMMDD'."""
        params = {}
        if date_str:
            params["dates"] = date_str
        data = _self._get(f"{_self.SPORT_PATH}/scoreboard", params)
        if not data:
            return pd.DataFrame()
        rows = []
        for event in data.get("events", []):
            comp = (event.get("competitions") or [{}])[0]
            comps_teams = comp.get("competitors", [])
            home = next((t for t in comps_teams if t.get("homeAway") == "home"), {})
            away = next((t for t in comps_teams if t.get("homeAway") == "away"), {})
            status = event.get("status", {}).get("type", {})
            season_type = event.get("season", {}).get("type", {})
            season_type_name = season_type.get("name", "") if isinstance(season_type, dict) else str(season_type)
            rows.append({
                "source": "espn",
                "season": 2026,
                "date": event.get("date"),
                "round": season_type_name,
                "group": "",
                "home_team": home.get("team", {}).get("displayName", ""),
                "away_team": away.get("team", {}).get("displayName", ""),
                "home_goals": home.get("score"),
                "away_goals": away.get("score"),
                "venue": comp.get("venue", {}).get("fullName", ""),
                "city": comp.get("venue", {}).get("address", {}).get("city", ""),
                "status": "completed" if status.get("completed") else "scheduled",
            })
        return pd.DataFrame(rows)

    @st.cache_data(ttl=300, show_spinner=False)
    def get_standings(_self) -> pd.DataFrame:
        """Group standings from ESPN."""
        data = _self._get("v2/sports/soccer/fifa.world/standings")
        if not data:
            return pd.DataFrame()
        rows = []
        for group_block in data.get("children", []):
            group_name = group_block.get("abbreviation", group_block.get("name", ""))
            for entry in group_block.get("standings", {}).get("entries", []):
                team = entry.get("team", {})
                stats = {s["name"]: s.get("value", 0) for s in entry.get("stats", [])}
                rows.append({
                    "group": group_name,
                    "rank": entry.get("stats", [{}])[0].get("rank", 0) if entry.get("stats") else 0,
                    "team": team.get("displayName", ""),
                    "played":       int(stats.get("gamesPlayed", 0)),
                    "won":          int(stats.get("wins", 0)),
                    "drawn":        int(stats.get("ties", 0)),
                    "lost":         int(stats.get("losses", 0)),
                    "goals_for":    int(stats.get("pointsFor", 0)),
                    "goals_against":int(stats.get("pointsAgainst", 0)),
                    "goal_diff":    int(stats.get("pointDifferential", 0)),
                    "points":       int(stats.get("points", 0)),
                })
        return pd.DataFrame(rows)


espn_client = ESPNClient()


# ══════════════════════════════════════════════════════════════════════════════
# THE ODDS API  (ODDS_API_KEY — max 500 req/month; aggressively cached)
# ══════════════════════════════════════════════════════════════════════════════

class OddsAPIClient:
    """Client for The Odds API (https://the-odds-api.com).

    Strategy to minimise request consumption:
    - Primary: read today's odds snapshot from disk (written by pull_world_cup_data.py)
    - Fallback: fetch live only if today's snapshot does not exist
    - All live fetches are cached for 24 hours in Streamlit session
    - The nightly pull script (run once/day) writes the snapshot so pages
      never need to hit the API directly during normal operation.
    """

    SPORT = "soccer_fifa_world_cup"

    def __init__(self):
        self._snapshot_path = _SNAPSHOT_DIR / date.today().isoformat() / "odds.json"

    def _get(self, path: str, params: Optional[Dict] = None) -> Optional[Any]:
        if not ODDS_API_KEY:
            return None
        try:
            url = f"{ODDS_API_BASE}/{path}"
            r = requests.get(url, params={**(params or {}), "apiKey": ODDS_API_KEY}, timeout=15)
            r.raise_for_status()
            return r.json()
        except Exception:
            return None

    def _load_snapshot(self) -> Optional[List[Dict]]:
        """Load today's pre-fetched odds snapshot from disk (no API call)."""
        path = _SNAPSHOT_DIR / date.today().isoformat() / "odds.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return None

    @st.cache_data(ttl=86400, show_spinner=False)
    def get_wc_odds(_self,
                    markets: str = "h2h,totals",
                    regions: str = "us",
                    bookmakers: str = "draftkings,fanduel,betmgm,williamhill_us,betrivers") -> List[Dict]:
        """Return upcoming WC match odds.  Reads snapshot if available; fetches only if needed."""
        snapshot = _self._load_snapshot()
        if snapshot is not None:
            return snapshot
        # Live fetch (consumes 1 request per event returned)
        data = _self._get(
            f"sports/{_self.SPORT}/odds",
            {"regions": regions, "markets": markets, "oddsFormat": "decimal",
             "bookmakers": bookmakers},
        )
        return data or []

    def fetch_and_save_snapshot(self) -> int:
        """Fetch live odds and persist to today's snapshot directory.
        Called by pull_world_cup_data.py (once per day).
        Returns number of events saved."""
        data = self._get(
            f"sports/{self.SPORT}/odds",
            {"regions": "us", "markets": "h2h,totals", "oddsFormat": "decimal",
             "bookmakers": "draftkings,fanduel,betmgm,williamhill_us,betrivers"},
        )
        if not data:
            return 0
        path = _SNAPSHOT_DIR / date.today().isoformat() / "odds.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return len(data)

    def parse_to_df(self, raw: List[Dict]) -> pd.DataFrame:
        """Flatten raw odds list into a tidy DataFrame."""
        rows = []
        for event in (raw or []):
            home  = event.get("home_team", "")
            away  = event.get("away_team", "")
            label = f"{home} vs {away}"
            game_time = event.get("commence_time", "")
            for bm in event.get("bookmakers", []):
                bm_name = bm.get("title", bm.get("key", ""))
                for mkt in bm.get("markets", []):
                    mkt_key = mkt.get("key", "")
                    outcomes = mkt.get("outcomes", [])
                    if mkt_key == "h2h":
                        for o in outcomes:
                            rows.append({
                                "game": label, "game_time": game_time,
                                "bookmaker": bm_name, "market": "1X2",
                                "outcome": o.get("name", ""), "odds": float(o.get("price", 0)),
                                "line": None,
                            })
                    elif mkt_key == "totals":
                        for o in outcomes:
                            rows.append({
                                "game": label, "game_time": game_time,
                                "bookmaker": bm_name, "market": "O/U",
                                "outcome": o.get("name", ""),
                                "odds": float(o.get("price", 0)),
                                "line": float(o.get("point", 2.5)),
                            })
        return pd.DataFrame(rows)


odds_client = OddsAPIClient()


# ── Snapshot helpers ──────────────────────────────────────────────────────────

def _latest_snapshot_df(filename: str) -> pd.DataFrame:
    """Read the most recent dated snapshot CSV for a given filename."""
    if not _SNAPSHOT_DIR.exists():
        return pd.DataFrame()
    for snap_dir in sorted(_SNAPSHOT_DIR.iterdir(), reverse=True):
        path = snap_dir / filename
        if path.exists():
            try:
                df = pd.read_csv(path, low_memory=False)
                if not df.empty:
                    return df
            except Exception:
                continue
    return pd.DataFrame()


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
    - Plus: international_results (1950-2024) for rich Elo training context
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
    
    # ── Enrich with international_results (1950-2024) for Elo training ───────
    try:
        from . import international_results
        result = international_results.enrich_training_dataset(result)
    except Exception as e:
        # Silently fall back to WC-only data if international_results unavailable
        pass
    
    return result


@st.cache_data(ttl=300, show_spinner=False)
def get_upcoming_matches(n: int = 20) -> pd.DataFrame:
    """Get the next N upcoming 2026 WC matches from any available source."""
    # 1. BALLDONTLIE (may be unavailable)
    df = bdl_client.get_matches(2026)
    if df is not None and not df.empty and "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
        now = pd.Timestamp.utcnow()
        upcoming = df[
            df["date"].gt(now)
            | (df["date"].isna() & df["status"].isin(["scheduled", "NS", "TBD", ""]))
        ]
        upcoming = _resolved_fixture_rows(upcoming)
        upcoming = upcoming.sort_values("date")
        if not upcoming.empty:
            return upcoming.head(n)

    # 2. API-Football (may be suspended)
    df = apf_client.get_fixtures(2026, next_n=n)
    if df is not None and not df.empty and "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
        upcoming = _resolved_fixture_rows(df[df["date"].gt(pd.Timestamp.utcnow())])
        if not upcoming.empty:
            return upcoming.sort_values("date").head(n)

    # 3. ESPN schedule (live and keyless)
    df = espn_client.get_schedule()
    if df is not None and not df.empty and "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
        now = pd.Timestamp.utcnow()
        upcoming = _resolved_fixture_rows(df[df["date"] >= now]).sort_values("date")
        if not upcoming.empty:
            return upcoming.head(n)

    # 4. Current openfootball feed. Prefer it to a dated local snapshot: the
    # feed fills knockout participants as results become known.
    raw = fetch_openfootball_wc(2026)
    if raw:
        df = _parse_openfootball(raw, 2026)
        if not df.empty and "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
            now = pd.Timestamp.utcnow()
            upcoming = _resolved_fixture_rows(df[df["date"] >= now]).sort_values("date")
            if not upcoming.empty:
                return upcoming.head(n)

    # 5. Nightly snapshot is an offline fallback only. Old snapshots commonly
    # contain W76/W78 bracket slots, so never expose those as team names.
    df = _latest_snapshot_df("upcoming_matches.csv")
    if not df.empty and "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
        now = pd.Timestamp.utcnow()
        upcoming = _resolved_fixture_rows(
            df[df["date"].isna() | df["date"].gt(now)]
        ).sort_values("date")
        if not upcoming.empty:
            return upcoming.head(n)

    return pd.DataFrame()


@st.cache_data(ttl=120, show_spinner=False)
def get_current_standings() -> pd.DataFrame:
    """Get 2026 WC group standings, trying multiple sources."""
    # 1. BALLDONTLIE
    df = bdl_client.get_standings(2026)
    if df is not None and not df.empty:
        return df
    # 2. API-Football
    df = apf_client.get_standings(2026)
    if df is not None and not df.empty:
        return df
    # 3. ESPN (free, no key)
    df = espn_client.get_standings()
    if df is not None and not df.empty:
        return df
    # 4. Nightly snapshot
    df = _latest_snapshot_df("standings.csv")
    if not df.empty and "group" in df.columns:
        return df
    return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def load_predictions_cache() -> Optional[Dict]:
    """Load the pre-computed predictions cache written by scripts/precompute_predictions.py.

    Returns the full dict (keys: match_predictions, upset_watch, group_draw,
    top_teams, best_bets, generated_at) or None if the file doesn't exist yet.
    Cache TTL is 1 hour so the app always picks up a fresh nightly build.
    """
    path = _REPO_ROOT / "data_files" / "predictions_cache.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


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


# ── Odds lookup helper ────────────────────────────────────────────────────────

def _name_key(name: str) -> str:
    """Normalise a team name to a comparable key (lowercase, strip punctuation)."""
    import re
    return re.sub(r"[^a-z0-9]", "", name.lower())


@st.cache_data(ttl=86400, show_spinner=False)
def get_match_odds_from_snapshot(home_team: str, away_team: str) -> Dict:
    """Look up real bookmaker odds for a match from today's odds snapshot.

    Returns a dict with keys:
      - ``bookmakers``: list of {name, h2h_home, h2h_draw, h2h_away,
                                  ou_line, ou_over, ou_under}
      - ``best_h2h``: {home, draw, away} — best available decimal odds
      - ``best_ou``: {line, over, under} — best available O/U odds

    Returns an empty dict if no matching event is found.
    """
    raw = odds_client.get_wc_odds()
    if not raw:
        return {}

    home_key = _name_key(home_team)
    away_key = _name_key(away_team)

    # Find the matching event (try both orderings)
    event = None
    for ev in raw:
        ek_h = _name_key(ev.get("home_team", ""))
        ek_a = _name_key(ev.get("away_team", ""))
        if (home_key in ek_h or ek_h in home_key) and \
           (away_key in ek_a or ek_a in away_key):
            event = ev
            break
        if (away_key in ek_h or ek_h in away_key) and \
           (home_key in ek_a or ek_a in home_key):
            # Odds API has teams flipped — still useful, just note it
            event = ev
            break

    if not event:
        return {}

    bookmakers_out = []
    best_h = best_d = best_a = 0.0
    best_ou_line = 2.5
    best_ou_over = best_ou_under = 0.0

    flipped = _name_key(event.get("home_team", "")) != home_key

    for bm in event.get("bookmakers", []):
        bm_name = bm.get("title", bm.get("key", "?"))
        row: Dict = {"name": bm_name,
                     "h2h_home": 0.0, "h2h_draw": 0.0, "h2h_away": 0.0,
                     "ou_line": None, "ou_over": 0.0, "ou_under": 0.0}
        for mkt in bm.get("markets", []):
            key = mkt.get("key", "")
            outcomes = mkt.get("outcomes", [])
            if key == "h2h":
                for o in outcomes:
                    o_key = _name_key(o.get("name", ""))
                    price  = float(o.get("price", 0))
                    if o_key in _name_key(event.get("home_team", "")):
                        row["h2h_home"] = price
                        if not flipped:
                            best_h = max(best_h, price)
                        else:
                            best_a = max(best_a, price)
                    elif o_key in _name_key(event.get("away_team", "")):
                        row["h2h_away"] = price
                        if not flipped:
                            best_a = max(best_a, price)
                        else:
                            best_h = max(best_h, price)
                    elif "draw" in o_key or o.get("name", "").lower() == "draw":
                        row["h2h_draw"] = price
                        best_d = max(best_d, price)
            elif key == "totals":
                for o in outcomes:
                    line = float(o.get("point", 2.5))
                    price = float(o.get("price", 0))
                    name  = o.get("name", "").lower()
                    if abs(line - 2.5) < 0.01:  # prefer 2.5 line
                        row["ou_line"] = line
                        if "over" in name:
                            row["ou_over"] = price
                            best_ou_over = max(best_ou_over, price)
                            best_ou_line = line
                        elif "under" in name:
                            row["ou_under"] = price
                            best_ou_under = max(best_ou_under, price)
        bookmakers_out.append(row)

    # Re-map best odds to correct home/away if flipped
    if flipped:
        best_h, best_a = best_a, best_h

    return {
        "bookmakers": bookmakers_out,
        "best_h2h":   {"home": best_h, "draw": best_d, "away": best_a},
        "best_ou":    {"line": best_ou_line, "over": best_ou_over, "under": best_ou_under},
        "event_home": event.get("home_team", ""),
        "event_away": event.get("away_team", ""),
    }
