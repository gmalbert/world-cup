# GoallineIQ — GitHub Copilot Instructions

## Project Overview

**App name:** GoallineIQ
**Purpose:** World Cup 2026 betting intelligence platform. Predicts match outcomes using Elo ratings and xG models, surfaces value bets vs. bookmaker odds.
**Entry point:** `streamlit run predictions.py`
**Part of:** Betting Oracle suite

---

## Tech Stack

| Layer | Technology |
|---|---|
| UI | Streamlit ≥ 1.36 (`st.navigation`, `st.Page`) |
| ML | Elo ratings + Dixon-Coles goal model (goallineiq_utils) |
| Data | pandas, ESPN API, football-data.org |
| Odds | The Odds API / nightly snapshots in `data_files/nightly_snapshots/` |
| Config | python-dotenv (`.env` file) |
| Python | 3.9+ |

---

## File Conventions

### Key files
- `predictions.py` — entry point; sets `st.set_page_config` ONCE; wires navigation.
- `goallineiq_utils/api_client.py` — `get_all_wc_matches()`, `get_upcoming_matches()`, `get_current_standings()`. All API calls here.
- `goallineiq_utils/models.py` — `build_predictor()`, `get_predictor()`, `WC2026_GROUPS`, `FALLBACK_ELO`. Predictor returns `{home_win, draw, away_win, home_elo, away_elo, home_xg, away_xg}`.
- `goallineiq_utils/simulator.py` — Monte Carlo tournament simulator.
- `footer.py` — `add_betting_oracle_footer()` called at page bottom.
- `scripts/export_best_bets.py` — exports `data_files/best_bets_today.json` for Sports Picks Grid.

### Pages
- `pages/1_Match_Hub.py` — live scores, standings, schedule, bracket
- `pages/2_Pre_Match_Analysis.py` — head-to-head, form, xG preview
- `pages/3_Odds_Comparison.py` — multi-book odds, model vs. market, value detector
- `pages/4_Tournament_Simulator.py` — Monte Carlo group/knockout simulation
- `pages/5_Statistics.py` — tournament-wide stats
- `pages/6_Team_Deep_Dive.py` — per-team drill-down

### Data files
- `data_files/nightly_snapshots/` — daily JSON odds snapshots (keyed by fixture label)
- `data_files/logo.png` — app logo
- `data_files/best_bets_today.json` — unified schema for Sports Picks Grid aggregator

---

## Domain Knowledge

### Predictor output
```python
pred = predictor.predict(home_team, away_team, neutral=True)
# pred keys: home_win, draw, away_win, home_elo, away_elo, home_xg, away_xg
```

### Groups
- `WC2026_GROUPS` in `goallineiq_utils/models.py` — dict of group → list of teams
- All 48 teams for 2026 format

### Odds snapshots
- Nightly JSON saved to `data_files/nightly_snapshots/YYYY-MM-DD.json`
- Keys are fixture labels (e.g. `"France vs Morocco"`), values have `home_dec`, `draw_dec`, `away_dec`

---

## Coding Conventions

### Streamlit patterns
- `st.set_page_config()` called ONCE in `predictions.py` — NEVER in sub-pages
- Use `width='stretch'` for dataframes/charts (not deprecated `use_container_width`)
- Cache API results with `@st.cache_data(ttl=300)` (5-min TTL for live scores)
- Wrap all `goallineiq_utils` imports in try/except (Streamlit caching warnings when running headless)

### Security
- API keys in `.env` via `python-dotenv`; never hardcode
- `.env` is gitignored

### Error handling
- `get_upcoming_matches()` can return `None` — always guard with `if upcoming is None or upcoming.empty`
- `predictor.predict()` can raise on unknown teams — wrap in try/except

---

## Export for Sports Picks Grid

`scripts/export_best_bets.py` loads the predictor, iterates upcoming matches, and compares model probabilities against the latest nightly odds snapshot. Writes `data_files/best_bets_today.json`.

Run: `python scripts/export_best_bets.py`
