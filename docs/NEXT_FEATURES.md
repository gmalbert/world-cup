# GoallineIQ (World Cup 2026) — Next 5 Features to Implement

> **Based on:** Codebase gap analysis as of July 2025

---

## Feature 1: XGBoost Layer (Model Layer 2)

**Why:** The architecture documents a 3-layer model stack (Layer 1: Elo+Poisson, Layer 2: XGBoost, Layer 3: Ensemble) but only Layer 1 is built. XGBoost would add features like recent form, squad quality, and head-to-head history that Elo alone misses — critical for a 48-team tournament with many unfamiliar matchups.

**How:**
1. Create `models/xgboost_model.py` that trains on the historical data in `data_files/`
2. Feature set: Elo rating diff, FIFA ranking diff, goal difference over last 10 games, H2H wins in last 5, days rest, confederation, qualified vs not-qualified flag
3. Use `scikit-learn` pipeline with `XGBClassifier` for H/D/A classification
4. Wrap both Elo and XGBoost outputs in `predict_match(home, away)` → dict with both model outputs
5. Layer 3 ensemble: simple average of Elo probability and XGBoost probability per outcome class

**Complexity:** High

---

## Feature 2: Player Availability / Injury Flags

**Why:** A missing key player (star striker, starting goalkeeper) can shift a national team's win probability significantly — especially for smaller nations where one world-class player dominates their squad. FIFA publishes official squad lists.

**How:**
1. Create `fetch_squad_availability.py` using FIFA/ESPN squad list endpoints
2. Maintain a `data_files/key_players.csv` mapping: `team`, `player_name`, `position`, `impact_score` (manually curated for ~80 top players)
3. Set `home_key_player_available` and `away_key_player_available` binary flags
4. Display on each prediction card as a contextual warning, not necessarily a model feature at first

**Complexity:** Medium

---

## Feature 3: Group Stage Qualification Tracker

**Why:** In the expanded 2026 format (48 teams, 3 per group → 16 groups, top 2 qualify), late group-stage games have high leverage. A live qualification tracker showing which teams are already through, on the bubble, or eliminated changes betting context dramatically.

**How:**
1. Parse live group stage results from the ESPN or FIFA API
2. Compute each team's current status: Qualified / Eliminated / On the Bubble
3. Add a `pages/group_stage.py` page with a collapsible group table and qualification probability chart (Monte Carlo over remaining group games)
4. Surface a "Qualification Impact" score on each prediction card when group position is on the line

**Complexity:** Medium

---

## Feature 4: Betting Line Movement Chart

**Why:** For a once-every-4-years event like the World Cup, lines open weeks before the tournament. Capturing opening vs current moneyline for each team (win the tournament, win their group, reach quarterfinals) would reveal sharp movement before matches are played.

**How:**
1. Adapt `fetch_odds.py` to call The Odds API for World Cup futures markets (outright winner, group winner)
2. Store snapshots at: tournament draw date, 2 weeks before opener, 1 week before, 48h before each match
3. Add a `pages/line_movement.py` page with a per-team timeline chart
4. Highlight teams where model probability diverges significantly from market line (potential value)

**Complexity:** Medium

---

## Feature 5: Interactive Tournament Bracket

**Why:** Users want to visualize bracket progression — especially with a 48-team field. The current UI shows match-level predictions but no bracket view. A Plotly-based bracket diagram with Monte Carlo win probabilities would be the flagship visual for the app.

**How:**
1. Use Plotly Sankey or a custom SVG/Plotly scatter layout to render the bracket
2. Drive each node with the Monte Carlo simulation output (already in `predictions.py`)
3. Color-code nodes by home confederation (UEFA blue, CONMEBOL green, etc.)
4. Allow users to click a team to see their predicted path to the final
5. Add "Sim" button that runs a new 10,000-trial simulation and updates the bracket in place

**Complexity:** Medium
