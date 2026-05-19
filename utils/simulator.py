"""
Monte Carlo tournament simulator for the 2026 FIFA World Cup.
48 teams → 12 groups of 4 → top 2 + 8 best third-placed → Round of 32
→ R16 → QF → SF → Final.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from utils.models import MatchPredictor, WC2026_GROUPS


class TournamentSimulator:
    """
    Simulates the 2026 FIFA World Cup using per-match Poisson probabilities.
    """

    def __init__(self, predictor: MatchPredictor):
        self.predictor = predictor

    # ── Single-match simulation ───────────────────────────────────────────────

    def _sim_match(self, team_a: str, team_b: str,
                   allow_draw: bool = True) -> Tuple[str, int, int]:
        """
        Simulate one match. Returns (result, goals_a, goals_b).
        result is team_a, team_b, or "draw" (only when allow_draw=True).
        """
        pred = self.predictor.predict(team_a, team_b, neutral=True)
        goals_a = int(np.random.poisson(pred["home_xg"]))
        goals_b = int(np.random.poisson(pred["away_xg"]))

        if goals_a > goals_b:
            return team_a, goals_a, goals_b
        if goals_b > goals_a:
            return team_b, goals_b, goals_a

        if allow_draw:
            return "draw", goals_a, goals_b

        # Knockout tie → penalty shootout (slight Elo-weighted 50/50)
        elo_diff = pred["home_elo"] - pred["away_elo"]
        pen_prob = 0.5 + 0.05 * np.tanh(elo_diff / 500.0)
        winner = team_a if np.random.random() < pen_prob else team_b
        return winner, goals_a, goals_b

    # ── Group stage ──────────────────────────────────────────────────────────

    def _sim_group(self, teams: List[str]) -> pd.DataFrame:
        """Simulate round-robin group and return standings DataFrame."""
        rec: Dict[str, Dict] = {
            t: {"played": 0, "won": 0, "drawn": 0, "lost": 0,
                "gf": 0, "ga": 0, "points": 0}
            for t in teams
        }

        for i in range(len(teams)):
            for j in range(i + 1, len(teams)):
                ta, tb = teams[i], teams[j]
                res, ga, gb = self._sim_match(ta, tb, allow_draw=True)
                rec[ta]["played"] += 1
                rec[tb]["played"] += 1
                rec[ta]["gf"] += ga
                rec[ta]["ga"] += gb
                rec[tb]["gf"] += gb
                rec[tb]["ga"] += ga

                if res == ta:
                    rec[ta]["won"] += 1
                    rec[ta]["points"] += 3
                    rec[tb]["lost"] += 1
                elif res == tb:
                    rec[tb]["won"] += 1
                    rec[tb]["points"] += 3
                    rec[ta]["lost"] += 1
                else:
                    rec[ta]["drawn"] += 1
                    rec[ta]["points"] += 1
                    rec[tb]["drawn"] += 1
                    rec[tb]["points"] += 1

        rows = [{"team": t, **v, "gd": v["gf"] - v["ga"]} for t, v in rec.items()]
        df = pd.DataFrame(rows).sort_values(
            ["points", "gd", "gf"], ascending=False
        ).reset_index(drop=True)
        df["position"] = df.index + 1
        return df

    # ── Knockout round ────────────────────────────────────────────────────────

    def _sim_round(self, teams: List[str]) -> List[str]:
        """Simulate one knockout round; return list of winners."""
        winners = []
        paired = list(teams)
        # Ensure even pairing
        if len(paired) % 2 != 0:
            winners.append(paired.pop())  # bye
        for i in range(0, len(paired), 2):
            res, _, _ = self._sim_match(paired[i], paired[i + 1], allow_draw=False)
            winners.append(res)
        return winners

    # ── Full tournament ───────────────────────────────────────────────────────

    def run(
        self,
        groups: Optional[Dict[str, List[str]]] = None,
        n: int = 10_000,
    ) -> pd.DataFrame:
        """
        Run the full 2026 WC Monte Carlo simulation.

        Args:
            groups: dict mapping group letter → list of team names.
                    Defaults to WC2026_GROUPS if None.
            n:      number of simulations.

        Returns:
            DataFrame with columns:
            team, Group Stage %, Round of 32 %, Round of 16 %,
            Quarterfinal %, Semifinal %, Final %, Winner %
        """
        if groups is None:
            groups = WC2026_GROUPS

        all_teams = [t for tl in groups.values() for t in tl]

        stages = [
            "Group Stage", "Round of 32", "Round of 16",
            "Quarterfinal", "Semifinal", "Final", "Winner",
        ]
        counts: Dict[str, Dict[str, int]] = {
            t: {s: 0 for s in stages} for t in all_teams
        }

        rng_seed = np.random.default_rng()

        for _ in range(n):
            all_standings: List[pd.DataFrame] = []

            # ── Group stage
            for g_name, g_teams in groups.items():
                g_df = self._sim_group(list(g_teams))
                g_df["group"] = g_name
                all_standings.append(g_df)

            combined = pd.concat(all_standings, ignore_index=True)

            # Every team played the group stage
            for t in all_teams:
                counts[t]["Group Stage"] += 1

            # Determine R32 qualifiers: top 2 per group (24) + 8 best 3rd-placed (8)
            top2 = combined[combined["position"] <= 2]["team"].tolist()
            thirds = combined[combined["position"] == 3].copy()
            thirds = thirds.sort_values(
                ["points", "gd", "gf"], ascending=False
            ).head(8)["team"].tolist()

            qualifiers = top2 + thirds
            for t in qualifiers:
                counts[t]["Round of 32"] += 1

            # Shuffle bracket for random seeding
            np.random.shuffle(qualifiers)

            # ── Knockout rounds
            round_stages = ["Round of 16", "Quarterfinal", "Semifinal", "Final"]
            current = qualifiers
            for stage in round_stages:
                current = self._sim_round(current)
                for t in current:
                    counts[t][stage] += 1

            # Winner is whoever remains after the Final round
            if current:
                counts[current[0]]["Winner"] += 1

        # Convert to percentages
        rows = []
        for team, stage_counts in counts.items():
            row = {"team": team}
            for stage in stages:
                row[stage] = round(stage_counts[stage] / n * 100, 1)
            rows.append(row)

        df = pd.DataFrame(rows).sort_values("Winner", ascending=False).reset_index(drop=True)
        df.insert(0, "rank", df.index + 1)
        return df

    def simulate_match_once(self, team_a: str, team_b: str,
                            n: int = 5000) -> Dict:
        """
        Run N simulations of a single match and return probability estimates.
        Useful for pre-match analysis pages.
        """
        counts = {"home_win": 0, "draw": 0, "away_win": 0}
        goals_a_list, goals_b_list = [], []

        for _ in range(n):
            res, ga, gb = self._sim_match(team_a, team_b, allow_draw=True)
            goals_a_list.append(ga)
            goals_b_list.append(gb)
            if res == team_a:
                counts["home_win"] += 1
            elif res == team_b:
                counts["away_win"] += 1
            else:
                counts["draw"] += 1

        return {
            "home_win": round(counts["home_win"] / n, 4),
            "draw": round(counts["draw"] / n, 4),
            "away_win": round(counts["away_win"] / n, 4),
            "avg_goals_home": round(float(np.mean(goals_a_list)), 2),
            "avg_goals_away": round(float(np.mean(goals_b_list)), 2),
        }
