# GoallineIQ — Architecture

## Overview
World Cup 2026 betting intelligence platform. Predicts match outcomes using Elo ratings and a Dixon-Coles xG model. Value bets are surfaced by comparing model probabilities against nightly odds snapshots from The Odds API.

## Data Flow
```
ESPN API / football-data.org
        ↓
goallineiq_utils/api_client.py
    get_all_wc_matches()
    get_upcoming_matches()
    get_current_standings()
        ↓
goallineiq_utils/models.py
    build_predictor() → WC2026 Elo + Dixon-Coles model
        ↓
goallineiq_utils/simulator.py (Monte Carlo tournament simulation)
        ↓
The Odds API (nightly)
        ↓
data_files/nightly_snapshots/YYYY-MM-DD.json
        ↓
predictions.py (entry) → st.navigation → pages/
        ↓
scripts/export_best_bets.py → data_files/best_bets_today.json
```

## ML / Prediction Models

### Elo Predictor (`goallineiq_utils/models.py`)
- `build_predictor()` — constructs the Elo + Dixon-Coles model
- `get_predictor()` — cached singleton
- `FALLBACK_ELO` — default rating for unranked teams
- `WC2026_GROUPS` — dict of group letter → list of 4 teams (48-team format)
- Returns: `{home_win, draw, away_win, home_elo, away_elo, home_xg, away_xg}`

### Monte Carlo Simulator (`goallineiq_utils/simulator.py`)
- Simulates full tournament bracket from group stage through final
- Runs N trials; returns team advancement probabilities

## API Integrations
| Source | Purpose | Key |
|--------|---------|-----|
| `site.api.espn.com` | WC match schedule, standings | None (public) |
| football-data.org | Historical match data | `FOOTBALL_DATA_API_KEY` |
| The Odds API | WC betting lines (nightly) | `ODDS_API_KEY` |

## Key Components
- `predictions.py` — entry, `st.set_page_config`, navigation
- `goallineiq_utils/api_client.py` — all API calls
- `goallineiq_utils/models.py` — predictor factory + group mapping
- `goallineiq_utils/simulator.py` — Monte Carlo simulation
- `footer.py` — `add_betting_oracle_footer()`
- `scripts/export_best_bets.py` — exports `best_bets_today.json`

## Pages
| Page | Purpose |
|------|---------|
| `1_Match_Hub.py` | Live scores, standings, schedule, bracket |
| `2_Pre_Match_Analysis.py` | Head-to-head, form, xG preview |
| `3_Odds_Comparison.py` | Multi-book odds, model vs. market |
| `4_Tournament_Simulator.py` | Monte Carlo group/knockout simulation |
| `5_Statistics.py` | Tournament-wide stats |
| `6_Team_Deep_Dive.py` | Per-team drill-down |

## Edge Calculation
- `edge` = model probability - market implied probability
- EV_THRESHOLD = 0.04 (4% minimum edge to flag as value bet)

## Storage
- `data_files/nightly_snapshots/` — daily JSON odds (keyed by `"Team A vs Team B"`)
- `data_files/logo.png` — app logo
- `data_files/best_bets_today.json` — unified Sports Picks Grid schema
