# Model and pipeline audit

This document traces the post-tournament results in [POST_TOURNAMENT_REVIEW_2026.md](POST_TOURNAMENT_REVIEW_2026.md) back to the checked-in implementation.

## Severity summary

| Priority | Finding | Consequence |
|---|---|---|
| P0 | No immutable per-match prediction ledger | Full no-hindsight evaluation is impossible |
| P0 | Simulator ignores actual results and current bracket | Nightly advancement probabilities remain nonzero for eliminated teams |
| P0 | Pre-tournament simulation used 20 nonparticipants and omitted 20 participants | Published tournament probabilities did not describe the actual field |
| P0 | Qualifiers are randomly shuffled | Advancement paths and championship odds do not match FIFA's bracket |
| P0 | Model cache key does not change when results fill existing fixture rows | “Live” Elo can remain stale within a persistent Streamlit process |
| P0 | Odds secret is absent from the nightly data workflow | Only one odds snapshot exists; CLV and betting evaluation are unavailable |
| P1 | Current-ish fallback ratings are followed by replaying 2010–2022 results | Ratings mix incompatible time origins and double-count history conceptually |
| P1 | Goal model is hard-coded rather than fitted | Probabilities and totals cannot be estimated or calibrated from evidence |
| P1 | Documentation calls the model Dixon–Coles and xG | Product language overstates the implementation |
| P1 | Team identity is string-based with a silent 1500 fallback | Aliases and new names can create extreme, hidden rating errors |
| P1 | Knockout-stage adjustment is effectively dead in the simulator | Intended regression-to-mean is not used |
| P1 | Randomness is not reproducible | Simulation changes cannot be separated from Monte Carlo noise |
| P2 | Data snapshots lack quality gates and reconciliation | Dates disappeared, scorers stayed empty, and the final remained scheduled |

## 1. Forecast logging and evaluation

### Current behavior

`scripts/precompute_predictions.py` can write a rich cache, but neither nightly workflow runs it or commits its output. Git history contains a June 13 cache and no daily prediction ledger. `predictions.py` prefers cached rows when present, then merges in uncovered live fixtures.

### Why it matters

A mutable cache is a serving optimization, not an evaluation dataset. A trustworthy record requires one append-only row per forecast vintage, written before kickoff. Without that, it is impossible to know exactly which probability a user saw, whether a later result entered training, or which odds were available at the decision time.

### Required change

Create an append-only prediction table with at least:

```text
fixture_id
forecast_created_at_utc
kickoff_at_utc
data_as_of_utc
model_name
model_version_or_git_sha
feature_schema_version
home_team_id / away_team_id
p_home / p_draw / p_away
lambda_home / lambda_away
market_snapshot_at_utc
market_probabilities_and_prices
source_snapshot_ids
```

Reject writes after kickoff for the official pre-match ledger. Corrections should append a new version rather than overwrite the old one.

## 2. Elo initialization and training

### Current behavior

`EloRatingSystem` starts from `FALLBACK_ELO`, described as approximate May 2026 ratings, then `train_on_history()` replays every completed World Cup match from 2010 onward with a World Cup K-factor. Unknown teams silently start at 1500.

### Problems

1. A May 2026 rating already summarizes past performance. Replaying 2010–2022 after that moves present-day ratings as if old matches happened after May 2026.
2. Only World Cup finals are used. Qualifiers, continental tournaments, Nations League matches, and friendlies—all important for current national-team strength—are absent.
3. Every historical row is hard-coded as `match_type="World Cup"`; the K-factor map creates the appearance of differentiated match importance without actually receiving differentiated data.
4. There is no offseason or generational regression, time decay, squad change, or manager change.
5. String aliases can split identities: `USA`/`United States`, `Ivory Coast`/`Côte d'Ivoire`, and future naming changes. A miss silently becomes 1500 rather than raising an error.

### Required change

Choose one coherent approach:

- Start from a trusted current rating snapshot and do **not** replay earlier results; update only with matches after the snapshot timestamp, or
- Estimate ratings chronologically from a neutral historical initialization, with time decay and periodic regression, using a broad international match dataset.

Use canonical team IDs and a tested alias table. Production inference should fail closed on an unknown tournament participant.

## 3. Goal and outcome model

### Current behavior

The code uses a base goal rate of 1.32 per team, converts Elo difference to a logistic share of those goals, adjusts the total using average Elo, clips each team's scoring rate to 0.25–4.5, and assumes independent Poisson goals.

### Problems

- No parameter is estimated from the project's match data.
- The average-Elo multiplier assumes elite matches are intrinsically higher-scoring; this is not validated.
- The 0.25 floor contributes to compressed underdog scoring estimates and extreme favorite probabilities.
- Independent Poisson misses the low-score correlation that Dixon–Coles is designed to address.
- The model is called “Poisson regression,” but no regression is fitted.
- Architecture documentation calls it Dixon–Coles, but there is no Dixon–Coles rho adjustment or likelihood fit.
- Pages call the generated lambdas “xG,” although no shot or chance-quality data is involved. “Model expected goals” or “goal-rate forecast” would be accurate.

The tournament evidence matches these issues: only 53.8% over/under accuracy, 0.921 team-goal MAE, and systematic goal-total drift between group and knockout phases.

### Required change

Fit and compare, with rolling time splits:

1. Independent Poisson with team attack/defense strengths.
2. Dixon–Coles with time decay.
3. Bivariate Poisson or negative binomial if dispersion diagnostics justify it.
4. A market-blended multinomial baseline.

Estimate parameters on training folds only. Calibrate the resulting 1X2 probabilities on validation folds and lock them before the test tournament.

## 4. Cache invalidation

### Current behavior

`build_predictor()` keys the cached resource with the number of rows plus the maximum fixture date. During the tournament the dataset remained 360 rows, and the schedule already extended through the final, so both values could remain unchanged when scores populated existing rows.

### Consequence

In a persistent Streamlit process, `get_predictor()` can return an already-trained object whose `_trained` flag prevents retraining. The site language promised updates with every result, but the cache key did not represent completed-result content.

### Required change

Hash a canonical serialization of all training-relevant fields, at minimum fixture ID, kickoff, status, teams, regulation score, extra-time score, penalties, and last-updated timestamp. Better still, train outside the request path and load an explicitly versioned model artifact.

## 5. Tournament simulation

### Current behavior

Every simulation:

1. Replays all 12 groups from zero.
2. Selects top two plus eight best third-place teams.
3. Randomly shuffles all 32 qualifiers.
4. Simulates successive paired rounds.
5. Resolves tied knockout scores with an arbitrary Elo-weighted penalty probability.

Nightly jobs rebuild this unconditional tournament from scratch with updated Elo, not from actual standings or a resolved bracket.

### Problems

- The June 11 artifact used a stale fallback field with 20 wrong teams.
- Random shuffling does not implement the official round-of-32 mapping.
- Completed games are resimulated rather than fixed.
- Eliminated teams retain championship probability.
- Group tie-breakers stop at points, goal difference, and goals for.
- `_sim_match()` always calls `predictor.predict()` with the default group stage, so the documented knockout regression branch is not invoked.
- `rng_seed = np.random.default_rng()` is unused; simulation draws use global `np.random`, and no seed is saved.
- Penalty modeling is an unsupported formula capped near 55/45 even for large Elo gaps.

### Required change

Represent tournament state explicitly:

```text
completed fixtures -> fixed scores and winners
current group table -> fixed accumulated points/GD/GF
remaining group fixtures -> simulated
official third-place mapping -> deterministic bracket construction
resolved knockout slots -> fixed participants
remaining knockout matches -> simulated once per path
```

Save the random seed, simulator version, input-state hash, and validation totals with each run. Assert that eliminated teams have exactly zero probability and confirmed participants have exactly 100% probability of stages already reached.

## 6. Market and betting layer

### Current behavior

The data-refresh workflow passes BALLDONTLIE and API-Football keys but not `ODDS_API_KEY`. Only June 11 has a committed `odds.json`. When real odds are unavailable, some UI paths build “market” probabilities from the model itself plus a margin.

### Problems

- A model-derived proxy cannot validate model edge; it is circular.
- There is no consistent open, bet-time, and closing-line archive.
- Edge thresholds are not calibrated to uncertainty, market liquidity, or multiple testing.
- The saved 23-bet sample lost 14.8% and the market beat the model's probability scores.

### Required change

Archive timestamped best and sharp-book prices, normalize overround consistently, and report closing-line value before realized ROI. Suppress “value bet” language when the odds source is a proxy. Large model–market divergence should open a review flag until input integrity checks pass.

## 7. Data quality and operations

Across the nightly archive:

- `top_scorers.csv` had zero data every day.
- Only one `odds.json` was committed.
- The July 20 snapshot still had the finished final as scheduled.
- Later final-snapshot tournament rows lost dates, requiring recovery from the June 4 schedule.
- Upcoming-match counts jumped from 4 on June 24 to 44 on June 25 as knockout slots resolved, a legitimate transition that still deserved an automated reconciliation check.

The workflow checks whether files changed, not whether the data are plausible.

Add hard gates for expected match counts, unique fixture IDs, non-null kickoff times, monotonic completed-match counts, valid scores, resolved bracket participants, odds freshness, and source-to-source discrepancies. Failed gates should alert and should not silently publish a new artifact.

## 8. Documentation drift

The repository variously describes K=32 versus K=60, home advantage +40 versus +80, Poisson versus Dixon–Coles, and XGBoost layers that are not trained. Documentation should be generated from a versioned model card and distinguish:

- implemented now;
- experimental but not served;
- planned;
- unavailable because data are missing.

Each published forecast should link to the matching model card.

## Testing gaps

The next implementation needs automated tests at four levels:

### Unit

- probability vectors sum to one;
- team aliases resolve to one ID;
- score and penalty outcomes are parsed correctly;
- cache hash changes when any completed result changes;
- seeded simulation is reproducible.

### Property

- increasing one team's strength cannot lower its win probability, holding other inputs fixed;
- confirmed elimination implies zero later-stage probability;
- stage probability is non-increasing for each team;
- advancement probability sums match the number of available slots.

### Replay

- freeze data before the 2018 and 2022 tournaments;
- generate every pre-match forecast in chronological order;
- compare artifacts byte-for-byte on repeat runs;
- verify no post-kickoff field enters a forecast.

### Integration

- nightly data -> validation -> model -> prediction ledger -> conditional simulator -> published artifact;
- injected missing odds, missing scorer data, stale final status, and team-name changes must produce visible failures or degraded-mode labels.
