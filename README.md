# GoallineIQ

<p align="center">
  <img src="data_files/logo.png" width="220" alt="GoallineIQ Logo" />
</p>

<p align="center">
  <strong>World Cup 2026 sports-betting analytics powered by Elo ratings, Poisson modelling, and Monte Carlo simulation.</strong>
</p>

---

## Overview

GoallineIQ is a multi-page Streamlit application that aggregates historical World Cup data (2010–2026), trains a live Elo + Poisson prediction model, and surfaces actionable insights for sports-betting research.  It covers the full tournament lifecycle — from pre-match deep dives and value-bet detection to full tournament simulations and multi-bookmaker odds comparison.

---

## Features

| Page | Description |
|------|-------------|
| **Predictions** (main) | Live countdown, upcoming match probability cards, value-bet alerts, Elo rankings chart, group standings |
| **Match Hub** | Season selector, full schedule table, group standings, and a visual knockout-bracket diagram |
| **Pre-Match Analysis** | Win/Draw/Loss gauge charts, head-to-head record, form guide, expected-goals scoreline distribution |
| **Odds Comparison** | Multi-bookmaker odds (live via API-Football), implied probability charts, bookmaker overround analysis, value-bet threshold slider |
| **Tournament Simulator** | Monte Carlo simulation (up to 25 000 runs) of the full 48-team / 12-group 2026 format; confederation filter; results as bar chart, table, or heatmap |
| **Statistics** | Scoring leaders, team stats, xG analysis, historical WC trends (goals/match, result distributions, all-time wins) |
| **Team Deep Dive** | Nation profile with Elo gauge, WC match history, playing-style radar, current squad, and head-to-head record vs. any opponent |

---

## Data Sources

| Source | Tournaments | Notes |
|--------|-------------|-------|
| [Openfootball (GitHub JSON)](https://github.com/openfootball/worldcup.json) | 2010, 2014 | Free, no key required |
| [BALLDONTLIE FIFA API](https://fifa.balldontlie.io) | 2018, 2022, 2026 | Requires API key; cursor-paginated |
| [API-Football v3](https://www.api-football.com) | 2026 live | Fixtures, standings, odds, H2H; 100 calls/day free tier |

Data is cached aggressively (24 h for historical, 5 min for live fixtures) to stay within free-tier limits.

---

## Nightly Data Refresh

This repo includes a GitHub Actions workflow that pulls fresh 2026 World Cup data snapshots on a nightly basis.

- Workflow: [.github/workflows/nightly-world-cup-data-refresh.yml](.github/workflows/nightly-world-cup-data-refresh.yml)
- Snapshot script: [scripts/pull_world_cup_data.py](scripts/pull_world_cup_data.py)
- Output directory: [data_files/nightly_snapshots](data_files/nightly_snapshots)
- Consumption note: [docs/worldcup-snapshot-consumption.md](docs/worldcup-snapshot-consumption.md)

### Schedule Window

The workflow is scheduled for `03:00 UTC` every day, but only performs the snapshot job during the tournament support window:

- Start: `2026-06-04 UTC` (one week before kickoff)
- End: `2026-07-26 UTC` (one week after the final)

This keeps pre-tournament and post-tournament data pulls available without running year-round.

### Required GitHub Secrets

Add these repository secrets in GitHub before enabling the workflow:

- `BALLDONTLIE_API_KEY`
- `API_FOOTBALL_KEY`
- `THE_SPORTS_DB_KEY`

### Snapshot Contents

Each nightly run writes a dated folder under `data_files/nightly_snapshots/YYYY-MM-DD/` containing:

- `matches_all.csv`
- `upcoming_matches.csv`
- `standings.csv`
- `top_scorers.csv`
- `manifest.json`

You can also trigger the workflow manually with `workflow_dispatch` from the GitHub Actions UI.

---

## Prediction Model

GoallineIQ uses a two-component approach described in the project docs:

### Layer 1 — Elo + Poisson (implemented)

1. **EloRatingSystem** — trains on all World Cup results from 2010–2026, applying a K-factor of 32 and a home advantage of +40 Elo points.
2. **PoissonModel** — converts the Elo differential between two teams into expected goals (λ_home, λ_away) using a logistic scaling function.
3. **Win / Draw / Loss probabilities** — computed by summing the full bivariate Poisson scoreline distribution (score cap: 9 goals per side).
4. **Value-bet detection** — compares model-implied probabilities against bookmaker odds to flag edges above a configurable threshold.

### Layer 2+ (future)
The docs recommend adding XGBoost, an ensemble model, and live in-match features in later iterations.  These layers are scaffolded but not yet trained.

---

## Assumptions & Design Decisions

1. **Odds API / OddsPapi not used** — no keys for these services were found in `.env`.  Multi-bookmaker odds are sourced from API-Football; when the API is unavailable, illustrative demo odds are generated for UI demonstration.

2. **XGBoost (Layer 2) not trained** — the project docs recommend starting with the Elo + Poisson baseline and adding model layers incrementally.  XGBoost is referenced in the architecture but not yet fit to data.

3. **2026 group draw is approximate** — the 12 groups (A–L) and their team assignments are hard-coded as a fallback in `utils/models.py` (`WC2026_GROUPS`).  Live draw data from BALLDONTLIE will override this when available.

4. **BALLDONTLIE endpoint structure** — the FIFA-specific base URL (`https://fifa.balldontlie.io/api/v1`) and `Authorization: <key>` header format are assumed from the provider's standard REST patterns, as full endpoint docs were not public at build time.

5. **TheSportsDB** — free public key `123` is configured.  Team logos from TheSportsDB are not currently rendered; the integration point exists in `api_client.py` for a future enhancement.

6. **Playing-style radar** — trait scores (Attacking, Defensive, Elo Strength, Tournament Experience, Consistency) are derived from historical WC match data and current Elo ratings.  Live club metrics (e.g., from Understat) are not yet integrated.

7. **Pre-tournament state** — at build time (May 2026) the tournament had not yet started (kick-off June 11, 2026).  All pages handle this gracefully with countdown timers and placeholder messages.

---

## Tech Stack

| Package | Version | Purpose |
|---------|---------|---------|
| streamlit | ≥ 1.35 | App framework |
| pandas | ≥ 2.0 | Data wrangling |
| numpy | ≥ 1.24 | Numerics |
| scipy | ≥ 1.11 | Poisson distributions |
| xgboost | ≥ 2.0 | ML scaffold (Layer 2) |
| scikit-learn | ≥ 1.3 | Preprocessing utilities |
| plotly | ≥ 5.18 | Interactive charts |
| requests | ≥ 2.31 | API calls |
| python-dotenv | ≥ 1.0 | `.env` key loading |
| Pillow | ≥ 10.0 | Logo rendering |

---

## Responsible Gambling

> **This application is for entertainment and research purposes only.**
> Predictions and value-bet alerts do not constitute financial advice.
> Please gamble responsibly.  If you need support, contact the **National Problem Gambling Helpline: 1-800-522-4700**.
> Must be 21+ in applicable jurisdictions.