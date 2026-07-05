> **AI Onboarding Guide** — See also the project docs folder for architecture details.

# GoallineIQ (World Cup 2026) — Site Summary

## What This App Does

Streamlit app that aggregates FIFA World Cup 2026 tournament data (2010–2026 historical + live 2026 fixtures), trains an Elo + Poisson prediction model, and surfaces actionable betting insights including value-bet detection, Monte Carlo tournament simulations (up to 25k runs), and multi-bookmaker odds comparison.

## Quick Start

```bash
# 1. Activate virtual environment
.\.venv\Scripts\Activate.ps1        # Windows
source .venv/bin/activate           # macOS/Linux

# 2. (Optional) Pull latest data
python scripts/pull_world_cup_data.py   # Runs nightly in GitHub Actions

# 3. Run the app
streamlit run predictions.py
```

## Tech Stack

| Layer | Technology |
|---|---|
| UI | Streamlit ≥1.51 (multi-page) |
| ML Layer 1 | Elo rating system (K=32, home advantage +40) + Poisson distribution |
| Simulation | Monte Carlo tournament simulator (up to 25k iterations) |
| Data | pandas, NumPy, scipy |
| Visualization | Plotly 5.18+ |
| Config | python-dotenv (`.env` file) |

## Key Files

| File | Purpose |
|---|---|
| `predictions.py` | Entry point — page nav + theme CSS injection |
| `utils/models.py` | `EloRatingSystem`, `PoissonModel` — core prediction layer |
| `utils/simulator.py` | Monte Carlo tournament simulation logic |
| `utils/api_client.py` | API wrappers for Openfootball, FIFA API, API-Football |
| `goallineiq_utils/` | Cached data loaders (24h historical cache, 5-min live cache) |
| `pages/1_Match_Hub.py` | Full schedule, group standings, bracket diagram |
| `pages/4_Tournament_Simulator.py` | Monte Carlo simulation (confederation filter, run-count slider) |
| `scripts/pull_world_cup_data.py` | Nightly GitHub Actions data refresh |

## Data Flow

1. **Historical data**: Openfootball JSON (2010, 2014 free) + BALLDONTLIE FIFA API (2018, 2022, 2026)
2. **Live fixtures**: API-Football v3 (status=SCHEDULED, 100 calls/day free tier)
3. **Elo training**: All historical matches → `EloRatingSystem` → current team ratings
4. **Poisson conversion**: Elo difference → expected goals (λ_home, λ_away) → score matrix (capped at 9 goals/side)
5. **Win probabilities**: Poisson score matrix → P(Home win), P(Draw), P(Away win)
6. **Value bets**: Model probabilities vs bookmaker implied odds → edge percentage
7. **Monte Carlo**: Simulate remaining fixtures (up to 25k iterations) → tournament advancement probabilities

## Environment Variables

| Variable | Purpose | Required |
|---|---|---|
| `FIFA_API_KEY` | BALLDONTLIE FIFA API — 2018/2022/2026 data | Required for history |
| `API_FOOTBALL_KEY` | API-Football v3 — live 2026 fixtures, standings, odds | Required for live |
| `ODDS_API_KEY` | The Odds API — bookmaker odds for value bets | Optional |

## External APIs & Rate Limits

| API | Free Tier | Notes |
|---|---|---|
| Openfootball (GitHub JSON) | Unlimited | 2010, 2014 tournaments; no key needed |
| BALLDONTLIE FIFA API | Limited | 2018, 2022, 2026; cursor-paginated |
| API-Football v3 | 100 calls/day | Live fixtures, standings, odds, H2H |

## Architecture Notes

The app is designed as a **3-layer model** but only Layer 1 is currently implemented:
- **Layer 1 (Built)**: Elo + Poisson — statistical baseline
- **Layer 2 (Planned)**: XGBoost — adds pre-match features (FIFA ranking delta, form last 5, travel)
- **Layer 3 (Planned)**: Ensemble blend of Layer 1 + Layer 2

## Critical Conventions

- Aggressive caching: `goallineiq_utils/` provides 24h historical cache and 5-min live cache — always go through these loaders
- All API calls must be wrapped in try/except; return empty DataFrame on failure
- Monte Carlo simulation is CPU-intensive — cap at 25k iterations in the UI to avoid timeouts
- Bivariate Poisson score matrix is capped at 9 goals per side

## Common Gotchas

- API-Football v3 has a **100 calls/day** hard limit on the free tier — prioritize caching to avoid exhaustion
- Openfootball is the only free source with no rate limits; use it for 2010/2014 data only
- The Poisson model currently under-predicts high-scoring games (no overdispersion correction)
- Team names differ between Openfootball, FIFA API, and API-Football — normalize before merging
