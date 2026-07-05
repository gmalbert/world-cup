"""
Prediction models for GoallineIQ.
Implements:
  1. EloRatingSystem  — computed from historical WC match data
  2. PoissonModel     — converts Elo differentials to expected goals & match probabilities
  3. MatchPredictor   — orchestrates training + inference
"""
import numpy as np
import pandas as pd
from scipy.stats import poisson
from typing import Dict, List, Tuple, Optional
import streamlit as st

# ── Approximate Elo ratings for 2026 WC participants (seed values) ────────────
# Source: World Football Elo Ratings (eloratings.net) — approximate May 2026
FALLBACK_ELO: Dict[str, float] = {
    "France": 2052, "Spain": 2041, "Brazil": 2030, "England": 2022,
    "Argentina": 2010, "Germany": 1989, "Netherlands": 1965, "Portugal": 1971,
    "Belgium": 1955, "Uruguay": 1945, "Morocco": 1920, "United States": 1910,
    "USA": 1910, "Mexico": 1905, "Colombia": 1900, "Japan": 1895,
    "Australia": 1870, "Canada": 1862, "Switzerland": 1880, "Croatia": 1875,
    "Denmark": 1870, "Senegal": 1865, "Ecuador": 1850, "Serbia": 1840,
    "South Korea": 1840, "Cameroon": 1835, "Nigeria": 1845, "Ghana": 1820,
    "Côte d'Ivoire": 1825, "Ivory Coast": 1825, "Iran": 1815, "Saudi Arabia": 1800,
    "Chile": 1830, "Peru": 1800, "Paraguay": 1810, "Venezuela": 1790,
    "Algeria": 1820, "Egypt": 1835, "Mali": 1800, "Tunisia": 1810,
    "Qatar": 1760, "Costa Rica": 1780, "Panama": 1765, "Jamaica": 1750,
    "Bolivia": 1740, "Honduras": 1745, "Zambia": 1755, "New Zealand": 1735,
    "Philippines": 1700, "Indonesia": 1695, "Slovakia": 1820, "Austria": 1825,
    "Turkey": 1830, "Ukraine": 1810, "Wales": 1820, "Scotland": 1815,
    "Poland": 1830, "Greece": 1790, "Romania": 1800, "Czech Republic": 1810,
    "Hungary": 1790, "Iraq": 1800, "Jordan": 1785, "Palestine": 1750,
    "Bahrain": 1750, "Cuba": 1720, "Guatemala": 1730, "El Salvador": 1720,
    "Suriname": 1740, "Kenya": 1760, "Tanzania": 1740, "Libya": 1750,
    "Mozambique": 1735, "Sudan": 1720, "Rwanda": 1730,
    # Real 2026 WC participants (added from actual draw)
    "Norway": 1895, "Sweden": 1855, "Bosnia & Herzegovina": 1810,
    "Cape Verde": 1790, "Curaçao": 1730, "DR Congo": 1800,
    "Haiti": 1740, "South Africa": 1785, "Uzbekistan": 1770,
    "Paraguay": 1810, "Algeria": 1820, "Australia": 1870,
    "Ivory Coast": 1825, "Ghana": 1820,
}

# ── K-factors by match type ────────────────────────────────────────────────────
K_FACTORS = {
    "world cup": 60,
    "continental": 50,
    "qualifier": 40,
    "friendly": 20,
    "default": 30,
}


class EloRatingSystem:
    """
    Maintains and updates Elo ratings for international football teams.
    Uses the World Football Elo Ratings methodology with a margin-of-victory multiplier.
    """

    def __init__(self, initial_ratings: Optional[Dict[str, float]] = None):
        self.ratings: Dict[str, float] = dict(FALLBACK_ELO)
        if initial_ratings:
            self.ratings.update(initial_ratings)

    # ── Core maths ────────────────────────────────────────────────────────────

    @staticmethod
    def expected_score(elo_a: float, elo_b: float) -> float:
        """Expected score (win probability) for team A vs team B."""
        return 1.0 / (1.0 + 10.0 ** ((elo_b - elo_a) / 400.0))

    @staticmethod
    def k_for(match_type: str) -> float:
        ml = match_type.lower()
        for key, k in K_FACTORS.items():
            if key in ml:
                return k
        return K_FACTORS["default"]

    # ── Training ──────────────────────────────────────────────────────────────

    def update(self, team_a: str, team_b: str, goals_a: int, goals_b: int,
               match_type: str = "World Cup") -> None:
        """Update ratings after one match result."""
        ea = self.ratings.get(team_a, 1500.0)
        eb = self.ratings.get(team_b, 1500.0)

        if goals_a > goals_b:
            sa, sb = 1.0, 0.0
        elif goals_b > goals_a:
            sa, sb = 0.0, 1.0
        else:
            sa, sb = 0.5, 0.5

        # Margin-of-victory multiplier (log-based)
        gdiff = abs(goals_a - goals_b)
        mov = np.log1p(gdiff) + 1.0 if gdiff > 0 else 1.0

        k = self.k_for(match_type)
        exp_a = self.expected_score(ea, eb)

        self.ratings[team_a] = round(ea + k * mov * (sa - exp_a), 1)
        self.ratings[team_b] = round(eb + k * mov * (sb - (1.0 - exp_a)), 1)

    def train_on_history(self, df: pd.DataFrame) -> None:
        """
        Train on a historical matches DataFrame.
        Required columns: date, home_team, away_team, home_goals, away_goals
        Optional: season (used to infer match_type)
        """
        if df.empty:
            return
        work = df.copy()
        work["date"] = pd.to_datetime(work["date"], errors="coerce", utc=True)
        work = work.dropna(subset=["date", "home_goals", "away_goals"])
        work = work.sort_values("date")

        for _, row in work.iterrows():
            try:
                self.update(
                    str(row["home_team"]),
                    str(row["away_team"]),
                    int(row["home_goals"]),
                    int(row["away_goals"]),
                    match_type="World Cup",
                )
            except Exception:
                continue

    # ── Helpers ───────────────────────────────────────────────────────────────

    def get(self, team: str) -> float:
        """Return Elo rating for a team (case-insensitive, 1500 default)."""
        if team in self.ratings:
            return self.ratings[team]
        for k, v in self.ratings.items():
            if k.lower() == team.lower():
                return v
        return 1500.0

    def as_dataframe(self) -> pd.DataFrame:
        df = pd.DataFrame(
            [{"team": t, "elo": r} for t, r in self.ratings.items()]
        ).sort_values("elo", ascending=False).reset_index(drop=True)
        df["rank"] = df.index + 1
        return df


class PoissonModel:
    """
    Predicts match outcomes using Elo-calibrated Poisson regression.
    The Elo differential determines expected goals; goals are independently
    Poisson-distributed, giving a full score probability matrix.
    """

    BASE_RATE = 1.32   # Mean goals per team in WC matches
    ELO_SCALE = 400.0  # Standard Elo scale factor

    def __init__(self, elo: EloRatingSystem):
        self.elo = elo

    def expected_goals(self, elo_home: float, elo_away: float,
                       neutral: bool = True) -> Tuple[float, float]:
        """Return (lambda_home, lambda_away) expected goals."""
        advantage = 0.0 if neutral else 80.0
        diff = (elo_home + advantage) - elo_away
        p_home = 1.0 / (1.0 + 10.0 ** (-diff / self.ELO_SCALE))
        # Scale total goal rate by average Elo: elite matchups are higher-scoring.
        # Reference: avg WC Elo ~1850 → no adjustment; ±200 Elo → ±~13% total goals.
        avg_elo = (elo_home + elo_away) / 2.0
        elo_factor = np.clip(1.0 + (avg_elo - 1850.0) / 1500.0, 0.75, 1.40)
        base = self.BASE_RATE * elo_factor
        lh = np.clip(base * (p_home / 0.5), 0.25, 4.5)
        la = np.clip(base * ((1.0 - p_home) / 0.5), 0.25, 4.5)
        return round(float(lh), 3), round(float(la), 3)

    def predict(self, home: str, away: str, neutral: bool = True,
                max_goals: int = 10) -> Dict:
        """
        Return full prediction dict for home vs away.
        Keys: home_win, draw, away_win, home_xg, away_xg,
              home_elo, away_elo, top_scorelines, ou
        """
        elo_h = self.elo.get(home)
        elo_a = self.elo.get(away)
        return self.predict_with_elo(home, away, elo_h, elo_a, neutral, max_goals)

    def predict_with_elo(self, home: str, away: str,
                         elo_h: float, elo_a: float,
                         neutral: bool = True,
                         max_goals: int = 10) -> Dict:
        """Internal: predict using caller-supplied (possibly adjusted) Elo values."""
        lh, la = self.expected_goals(elo_h, elo_a, neutral)

        prob_matrix = np.outer(
            poisson.pmf(np.arange(max_goals + 1), lh),
            poisson.pmf(np.arange(max_goals + 1), la),
        )
        home_win = float(np.sum(np.tril(prob_matrix, -1)))
        draw = float(np.sum(np.diag(prob_matrix)))
        away_win = float(np.sum(np.triu(prob_matrix, 1)))

        total = home_win + draw + away_win
        home_win /= total
        draw /= total
        away_win /= total

        # Top 8 most likely scorelines
        score_probs = {
            f"{h}-{a}": float(poisson.pmf(h, lh) * poisson.pmf(a, la))
            for h in range(6) for a in range(6)
        }
        top_scorelines = sorted(score_probs.items(), key=lambda x: -x[1])[:8]

        # Over/Under probabilities for standard goal lines
        ou: Dict[float, Dict[str, float]] = {}
        for line in (1.5, 2.5, 3.5):
            over_p = float(sum(
                prob_matrix[h, a]
                for h in range(max_goals + 1)
                for a in range(max_goals + 1)
                if h + a > line
            ))
            ou[line] = {"over": round(over_p, 4), "under": round(1.0 - over_p, 4)}

        return {
            "home_win": round(home_win, 4),
            "draw": round(draw, 4),
            "away_win": round(away_win, 4),
            "home_xg": lh,
            "away_xg": la,
            "home_elo": elo_h,
            "away_elo": elo_a,
            "top_scorelines": top_scorelines,
            "ou": ou,
        }

    def value_edges(self, pred: Dict, odds_h: float, odds_d: float,
                    odds_a: float) -> Dict:
        """
        Compute model edge vs. bookmaker odds.
        Positive edge = model gives higher probability than fair market.
        """
        implied = [1 / o if o > 0 else 0 for o in (odds_h, odds_d, odds_a)]
        overround = sum(implied)
        if overround <= 0:
            return {"home_edge": 0.0, "draw_edge": 0.0, "away_edge": 0.0, "overround": 0.0}
        fair_h, fair_d, fair_a = [i / overround for i in implied]
        return {
            "home_edge": round(pred["home_win"] - fair_h, 4),
            "draw_edge": round(pred["draw"] - fair_d, 4),
            "away_edge": round(pred["away_win"] - fair_a, 4),
            "overround": round(overround - 1.0, 4),
        }


class MatchPredictor:
    """
    High-level interface: trains on historical WC data and generates predictions.
    """

    def __init__(self):
        self.elo = EloRatingSystem()
        self.model = PoissonModel(self.elo)
        self._trained = False

    def train(self, historical: pd.DataFrame) -> None:
        if historical is None or historical.empty:
            return
        missing = [c for c in ("home_goals", "away_goals") if c not in historical.columns]
        if missing:
            return
        completed = historical.dropna(subset=["home_goals", "away_goals"])
        self.elo.train_on_history(completed)
        self._trained = True

    def predict(self, home: str, away: str, neutral: bool = True,
                stage: str = "group") -> Dict:
        """
        Generate a match prediction.

        Parameters
        ----------
        stage : str
            Tournament stage.  One of ``"group"``, ``"r32"``, ``"r16"``,
            ``"quarterfinal"``, ``"semifinal"``, ``"final"``.
            Knockout stages apply a 10 % Elo regression-to-mean so that
            surviving teams converge slightly toward parity — matching the
            empirical observation that upsets are more common in do-or-die
            single-leg matches (no draws) than in group play.
        """
        if stage != "group":
            # Regress both teams 10 % toward the average WC Elo (~1850)
            MEAN_ELO = 1850.0
            REGRESS  = 0.10
            elo_h_raw = self.elo.get(home)
            elo_a_raw = self.elo.get(away)
            adj_h = elo_h_raw + REGRESS * (MEAN_ELO - elo_h_raw)
            adj_a = elo_a_raw + REGRESS * (MEAN_ELO - elo_a_raw)
            return self.model.predict_with_elo(home, away, adj_h, adj_a, neutral)
        return self.model.predict(home, away, neutral)

    def predict_batch(self, matches: pd.DataFrame) -> pd.DataFrame:
        """
        Add prediction columns to a matches DataFrame.
        Expects columns: home_team, away_team.
        """
        if matches.empty:
            return matches
        results = matches.apply(
            lambda r: pd.Series(self.predict(r["home_team"], r["away_team"])),
            axis=1,
        )
        return pd.concat([matches.reset_index(drop=True), results], axis=1)

    def get_ratings_df(self) -> pd.DataFrame:
        return self.elo.as_dataframe()


# ── Cached singleton (trained once per session) ───────────────────────────────

@st.cache_resource(show_spinner="Training prediction model…")
def get_predictor(history_hash: str = "") -> MatchPredictor:
    """
    Returns a cached MatchPredictor.  Pass history_hash to bust cache when
    new historical data arrives (e.g. str(len(df)) + str(df['date'].max())).
    """
    return MatchPredictor()


def build_predictor(historical_df: Optional[pd.DataFrame] = None) -> MatchPredictor:
    """Build and train a predictor (used in pages)."""
    if historical_df is not None and not historical_df.empty:
        key = f"{len(historical_df)}_{str(historical_df['date'].max())[:10]}"
    else:
        key = "default"
    predictor = get_predictor(key)
    if not predictor._trained and historical_df is not None and not historical_df.empty:
        predictor.train(historical_df)
    return predictor


# ── 2026 WC Groups (actual draw — 48 teams, 12 groups of 4) ──────────────────
WC2026_GROUPS: Dict[str, List[str]] = {
    "A": ["Mexico", "South Korea", "Czech Republic", "South Africa"],
    "B": ["Canada", "Switzerland", "Qatar", "Bosnia & Herzegovina"],
    "C": ["Brazil", "Morocco", "Scotland", "Haiti"],
    "D": ["USA", "Paraguay", "Australia", "Turkey"],
    "E": ["Germany", "Ecuador", "Ivory Coast", "Curaçao"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "H": ["Spain", "Uruguay", "Saudi Arabia", "Cape Verde"],
    "I": ["France", "Senegal", "Norway", "Iraq"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "Colombia", "DR Congo", "Uzbekistan"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}
