# Model improvement roadmap

This roadmap prioritizes trustworthy measurement and tournament correctness before model complexity.

## Definition of success

The next system is successful only if it can answer all of these questions for any displayed probability:

1. What exact data were available when it was generated?
2. Which code and model artifact generated it?
3. Was it created before kickoff?
4. How did it compare with a naïve baseline and the market available then?
5. Can the forecast and its tournament state be reproduced exactly?

## Phase 0 — Preserve and validate evidence

**Goal:** make another postmortem exact rather than reconstructed.

- Add canonical fixture and team IDs.
- Create the append-only forecast ledger described in the audit.
- Store model version, feature schema, input snapshot hash, and odds timestamp.
- Archive open, decision-time, and closing odds separately.
- Add data contracts and stop publication when required fields fail.
- Reconcile the final result and late source updates instead of trusting a single 03:00 UTC pull.
- Preserve regulatory result, extra-time result, penalty result, and advancement as separate outcomes.

**Exit gate:** 100% of test fixtures receive one pre-kickoff forecast record; rerunning from its input hash reproduces probabilities within numerical tolerance; no unknown team falls back silently.

## Phase 1 — Rebuild the transparent baselines

**Goal:** establish models that are simple, fitted, and hard to fool.

### Rating baseline

- Use a chronological international-results dataset, not only World Cup finals.
- Estimate or tune K, home advantage, match-importance weights, time decay, and offseason regression using training tournaments.
- Treat penalty shootouts separately from match outcomes.
- Compare against published Elo and FIFA ratings as external baselines.

### Goal baseline

- Fit team attack and defense effects with an independent Poisson model.
- Add Dixon–Coles low-score correction and recency weighting.
- Estimate separate competition/stage and neutral-venue effects only if validation supports them.
- Remove arbitrary goal floors and elite-match scaling unless ablation tests show improvement.

### Evaluation protocol

- Use expanding-window backtests: train before 2014/test 2014, then before 2018/test 2018, before 2022/test 2022, and reserve 2026 as the final untouched test.
- Report log loss, multiclass Brier, RPS, calibration error, goal deviance, and team/total-goal MAE.
- Always show historical-frequency, rating-only, fitted-Poisson, and market baselines.

**Exit gate:** the fitted baseline beats the current hand-built model on aggregate out-of-sample log loss and Brier across multiple tournaments, not only 2026.

## Phase 2 — Calibrate and use the market correctly

**Goal:** produce honest probabilities and test whether independent information exists.

- Convert bookmaker prices to de-vigged probabilities with a documented method.
- Fit a blend such as `p_final = alpha * p_model + (1 - alpha) * p_market`, with alpha selected only on validation data.
- Try multinomial logistic stacking of Elo, goal-model, and market logits before boosted trees.
- Calibrate with temperature/vector scaling or isotonic calibration chosen by validation performance.
- Add disagreement diagnostics for alias failures, reversed fixtures, stale ratings, or unavailable players.
- Track closing-line value by forecast decile and edge band.

**Exit gate:** on locked test periods, the blended model improves market log loss or Brier with confidence intervals. Do not claim an exploitable edge from accuracy alone.

## Phase 3 — Build a stateful, official-bracket simulator

**Goal:** simulate only what remains uncertain.

- Ingest completed scores and current standings as fixed state.
- Implement every official group and third-place tie-break rule.
- Implement FIFA's exact round-of-32 mapping; never shuffle qualifiers.
- Resolve bracket slots from fixture IDs, not display names.
- Use separate match-result and advancement probabilities for knockouts.
- Fit or benchmark an advancement/penalty model.
- Seed every run and save the input-state hash.
- Recompute after each accepted result, not merely on a fixed nightly clock.

**Exit gate:** golden replay tests for a historical tournament reproduce the real bracket state after every match; eliminated teams always have zero future-stage probability; stage totals equal available slots.

## Phase 4 — Add richer football information

**Goal:** add features only where ablations show incremental value.

Candidate features, in approximate priority order:

1. Closing and earlier market probabilities.
2. Current broad-based international Elo/FIFA strength.
3. Squad availability, projected starters, injuries, and minutes load.
4. Recent opponent-adjusted form with time decay.
5. Rest days, travel distance, altitude, heat, and host advantage.
6. Team attack/defense and set-piece profiles.
7. Shot-based xG and keeper performance where coverage is consistent.
8. Manager tenure and tactical continuity.

Only after those features have stable coverage should XGBoost, LightGBM, or a larger ensemble be considered. Use grouped and temporal validation, monotonic constraints where appropriate, and SHAP only as a diagnostic—not as proof of causality.

**Exit gate:** each feature family must improve at least one primary probability metric without materially degrading calibration or coverage on other tournaments.

## Phase 5 — Production monitoring and communication

**Goal:** keep the system honest after deployment.

Publish a model-performance page driven from the ledger, with:

- coverage and freshness;
- accuracy, log loss, Brier, RPS, and calibration;
- model versus market by probability band;
- goal and totals residuals;
- CLV and realized ROI with sample size and uncertainty;
- results by tournament phase, favorite strength, confederation, and data-quality status;
- version-to-version changes.

Change product language:

- “Model expected goals,” not shot-based “xG,” unless actual xG is used.
- “Model–market disagreement,” not “value bet,” until the edge is validated.
- “Reconstructed estimate,” not “prediction,” for any record created after the fact.
- Always show forecast timestamp, model version, and data freshness.

**Exit gate:** monitoring alerts on stale models, missing odds, missing fixtures, unknown teams, calibration drift, extreme market disagreement, and nonzero probabilities for eliminated teams.

## Recommended next sprint

The highest-leverage first sprint is operational:

1. Define team/fixture schemas and aliases.
2. Implement the immutable prediction ledger.
3. Replace the model cache key with an input-content hash.
4. Add `ODDS_API_KEY` to the secured workflow environment and archive odds vintages.
5. Make the nightly workflow run and commit pre-match forecasts.
6. Add snapshot quality gates and a late-result reconciliation run.
7. Add a conditional simulator skeleton with official bracket fixtures.
8. Replay 2022 end to end as the first acceptance test.

That sprint will not create a flashier model. It will create the foundation needed to know whether the next model is actually better.

## Decision rules for future claims

- Do not promote a model because its accuracy increased on one tournament.
- Do not call a price an edge without a real timestamped market price.
- Do not report ROI without stake rules, availability checks, void handling, and uncertainty.
- Do not tune against 2026 and then report 2026 as an untouched test.
- Do not increase model complexity unless it beats the fitted baseline and market on proper out-of-sample probability scores.
- Do not publish a tournament simulation that fails participant, bracket, state, or stage-total assertions.

The detailed evidence behind these priorities is in [POST_TOURNAMENT_REVIEW_2026.md](POST_TOURNAMENT_REVIEW_2026.md) and [MODEL_PIPELINE_AUDIT_2026.md](MODEL_PIPELINE_AUDIT_2026.md).
