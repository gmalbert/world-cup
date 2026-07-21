# 2026 World Cup prediction postmortem

**Audit date:** July 20, 2026

**Tournament result:** Spain defeated Argentina 1–0 after extra time. Spain's title and the score are confirmed by [FIFA's final report](https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/spain-argentina-final-report-highlights) and the [Associated Press match report](https://apnews.com/article/fccc26aa12d9226e63d06b601b770617).

## Executive assessment

The match model was useful as a baseline, but it was not ready to support strong betting or tournament-forecast claims.

- The strongest honest result is **60.0% 1X2 accuracy on the 30 forecasts that were actually saved before the matches**. On exactly those matches, the de-vigged bookmaker probabilities were better: **63.3% accuracy, 0.883 log loss, and 0.532 Brier**, versus the model's **60.0%, 1.026, and 0.600**.
- Twenty-three saved 1X2 “value” selections returned **−3.40 units on 23 units staked (−14.8% ROI)**. That sample is far too small for a profitability conclusion, but it directly contradicts any claim that the displayed edges were validated.
- A reconstruction of the intended rolling model across all 104 matches produced **62.5% accuracy**, **0.910 log loss**, **0.539 multiclass Brier**, and **0.170 Ranked Probability Score**. It beat a historical outcome-frequency baseline, but these were reconstructed forecasts, not a complete immutable forecast log.
- Updating Elo during the tournament helped only modestly versus a frozen pre-tournament version: accuracy rose from **60.6% to 62.5%**, log loss improved from **0.935 to 0.910**, and Brier improved from **0.565 to 0.539**.
- The pre-tournament Monte Carlo artifact was not a valid simulation of the actual tournament. **Twenty simulated teams were not participants, twenty actual participants were missing, and qualifiers were randomly shuffled instead of placed into the official bracket.** Spain was ranked 11th with only a **2.3%** title probability; the Netherlands led at **27.7%**.
- The nightly simulator never conditioned on completed matches. On July 19 it still assigned the already-eliminated Netherlands a **21.6%** chance to win and France, which had already lost its semifinal, **10.9%**.
- The pipeline did not create a daily immutable prediction log. The only committed prediction cache was generated June 13, while the Monte Carlo file was updated nightly. That makes a complete, exact, no-hindsight evaluation impossible.

The best path forward is not “add a more complex model.” It is: make every forecast reproducible, repair the tournament state engine, establish clean baselines, then fit and calibrate better models against multiple historical tournaments and the market.

## What was evaluated

There are three evidence tiers, and they should not be blended.

| Evidence | Coverage | What it supports | Limitation |
|---|---:|---|---|
| Saved `predictions_cache.json`, generated 2026-06-13 01:31 UTC | 30 matches | Exact pre-match probabilities, scorelines, odds, and edges that were stored | Only one forecast vintage was preserved |
| Saved Monte Carlo artifact, generated 2026-06-11 08:45 UTC | 48 simulated teams | Exact published pre-tournament championship and advancement probabilities | Participant list and bracket were invalid |
| Reconstructed rolling forecasts | 104 matches | How the checked-in Elo–Poisson code would have forecast each match using only results from prior dates | Not proof of what every user actually saw; cache behavior could serve older values |

The upstream `main` history supplied nightly snapshots through July 20. The July 20 snapshot still marked the completed final as scheduled, so the final was filled from FIFA's 1–0 report. Fixture dates came from the clean June 4 schedule because later upstream rows lost dates. For same-day matches, only results from earlier dates were included in the rolling reconstruction.

Knockout matches were scored as the stored match result—home win, draw, or away win—rather than advancement. That matches the model's displayed three-way probabilities. A tied knockout match therefore counts as a draw even when one team advanced on penalties.

## Scorecard

### All-match reconstruction

Lower is better for log loss, Brier, RPS, and errors.

| Metric | Frozen pre-tournament model | Intended rolling model | Historical frequency baseline |
|---|---:|---:|---:|
| Matches | 104 | 104 | 104 |
| 1X2 accuracy | 60.6% (63/104) | **62.5% (65/104)** | 45.2% (47/104) |
| Log loss | 0.935 | **0.910** | 1.082 |
| Multiclass Brier | 0.565 | **0.539** | 0.655 |
| Ranked Probability Score | 0.181 | **0.170** | — |
| Mean top-pick confidence | 62.2% | 62.0% | 39.5% |
| Predicted / actual goals | 282.3 / 301 | 286.1 / 301 | — |
| Team-goal MAE | 0.943 | **0.921** | — |
| Total-goal MAE per match | **1.424** | 1.440 | — |
| Over/under 2.5 accuracy | 53.8% | 53.8% | — |
| Exact score, top choice | 9.6% | **10.6%** | — |
| Actual score among top five | 50.0% | **53.8%** | — |

The rolling update improved outcome probabilities but did not improve totals. This is consistent with the implementation: Elo moves team strength, while the total-goal process remains mostly a hard-coded function of average Elo.

The rolling accuracy's approximate 95% Wilson interval is **52.9–71.2%**. A 104-match tournament is enough to expose major defects, but not enough to establish a narrow estimate of future accuracy.

### Group and knockout performance

| Segment | Matches | Accuracy | Log loss | Brier | Predicted / actual goals |
|---|---:|---:|---:|---:|---:|
| Group stage | 72 | 62.5% | **0.888** | **0.521** | 192.4 / 215 |
| Knockouts plus third-place match | 32 | 62.5% | 0.960 | 0.580 | 93.7 / 86 |

Accuracy was identical, but probability quality deteriorated in the knockouts. The group model underpredicted scoring by 22.6 goals, while it overpredicted the knockout segment by 7.7. One fixed goal-rate formula did not transfer cleanly between phases.

### Calibration

| Top-pick probability band | Matches | Mean stated confidence | Observed accuracy |
|---|---:|---:|---:|
| 33–45% | 21 | 42.1% | 47.6% |
| 45–55% | 20 | 50.2% | 70.0% |
| 55–65% | 18 | 59.3% | 55.6% |
| 65–75% | 17 | 69.5% | 58.8% |
| 75–100% | 28 | 82.4% | 75.0% |

The model was overconfident at the top end and especially in the 65–75% band. The 45–55% band looks underconfident, but each bin is small; this is diagnostic evidence, not a stable calibration curve.

### The 30 forecasts that were actually saved

| Metric | Model | De-vigged market |
|---|---:|---:|
| Accuracy | 60.0% (18/30) | **63.3% (19/30)** |
| Log loss | 1.026 | **0.883** |
| Brier | 0.600 | **0.532** |

The saved model averaged **78.8% confidence** while being right **60.0%** of the time. It was substantially too certain. Only **1 of 30** most-likely exact scores landed, and the actual score appeared in the model's top five just **8 of 30** times.

The saved accuracy's approximate 95% Wilson interval is **42.3–75.4%**. The market comparison uses the saved best-price composite, de-vigged across outcomes; those prices came from one June 11 snapshot rather than a consistent sharp-book closing line. It is the best available contemporary benchmark, not a definitive market-efficiency test.

The 23 saved 1X2 selections with at least a five-point displayed edge won 12 times and lost 3.40 units at the saved best prices. The worst edge calls included:

- Ecuador over Ivory Coast: model 89.8%, price 2.45, lost.
- Uruguay over Saudi Arabia: model 81.5%, price 1.44, drew.
- Iran over New Zealand: model 82.5%, price 1.83, lost.
- Belgium over Egypt: model 77.7%, price 1.61, drew.
- Portugal over DR Congo: model 89.7%, price 1.29, drew.

Those pairings—extreme model confidence while the market offered relatively long prices—should have triggered a data-quality or model-disagreement alarm rather than an automatic “value” label.

## What went right

### 1. The baseline extracted real signal

The intended rolling model beat a simple historical outcome-frequency baseline by 17.3 percentage points of accuracy and improved log loss by 0.172. A strength-rating model is a sensible first layer for international football.

### 2. It handled many clear mismatches well

Among the strongest correct rolling calls were:

| Match | Model call | Probability | Result |
|---|---|---:|---:|
| Tunisia–Netherlands | Netherlands | 89.4% | 1–3 |
| Paraguay–France | France | 89.4% | 0–1 |
| France–Iraq | France | 88.6% | 3–0 |
| Jordan–Argentina | Argentina | 87.5% | 1–3 |
| Argentina–Egypt | Argentina | 86.3% | 3–2 |
| Panama–England | England | 85.7% | 0–2 |

The system was most useful when identifying large, genuine team-strength gaps. That is exactly where an Elo baseline should be strongest.

### 3. Rolling updates added some value

Using prior tournament results improved all three main probability scores and added two correct picks across 104 matches. The idea of updating strength during the event was sound, even though the actual cache key and logging system did not reliably deliver or preserve those updates.

### 4. Spain became the correct final-match pick

The pre-tournament tournament simulation badly underrated Spain, but the reconstructed rolling match model favored Spain in the final and assigned the winning outcome 50.4%. This is a useful example of why tournament priors and current match forecasts should be tracked separately.

### 5. The project preserved useful raw material

Nightly match and standings snapshots, Git history, saved simulation artifacts, and one exact prediction cache made this audit possible. The raw evidence was incomplete, but far better than having only screenshots or prose claims.

## What went wrong

### Biggest match-level misses

These are ranked by the probability assigned to the actual result in the reconstructed rolling model.

| Match | Model's top call | Stated probability | Actual result probability | Result |
|---|---|---:|---:|---:|
| Turkey–USA | USA | 81.7% | 4.3% | 3–2 |
| Ecuador–Germany | Germany | 79.3% | 5.9% | 2–1 |
| Netherlands–Japan | Netherlands | 87.6% | 9.8% draw | 2–2 |
| Argentina–Cape Verde | Argentina | 85.6% | 11.3% draw | 1–1 |
| Netherlands–Morocco | Netherlands | 83.0% | 12.1% draw | 1–1 |
| Belgium–Egypt | Belgium | 84.6% | 12.5% draw | 1–1 |
| France–Spain | France | 69.5% | 13.1% Spain | 0–2 |
| France–England | France | 66.4% | 14.7% England | 4–6 |

The pattern is more important than any single upset: the model repeatedly compressed the weaker side toward the 0.25-goal floor and assigned elite favorites too much certainty. Draws against strong favorites were particularly underpriced.

### Tournament forecast failure

The June 11 simulation's leading championship probabilities were Netherlands 27.7%, France 19.2%, Argentina 10.0%, Brazil 5.2%, and Belgium 4.9%. Champion Spain was 11th at 2.3%.

That miss is not primarily bad luck. The artifact was structurally invalid:

- 20 of its 48 teams were not in the actual field, including Chile, Denmark, Nigeria, and Poland.
- 20 real participants were absent, including Norway, Egypt, Ghana, and Sweden.
- It randomly shuffled all 32 qualifiers rather than applying FIFA's bracket mapping.
- It replayed the entire group stage every night instead of fixing completed results and current standings.
- It did not eliminate teams from later simulations after they were knocked out.
- It used an unseeded global random generator, so runs were not reproducible.

The advancement columns summed to the correct field sizes, so the Monte Carlo mechanics looked plausible in aggregate. That was not enough: it was simulating the wrong competition.

### Goal and scoreline weakness

The rolling model predicted 286 goals against 301 actual goals. More importantly, over/under 2.5 accuracy was only 53.8%, team-goal MAE was 0.921, and exact-score performance was weak. The “xG” outputs were not shot-based expected goals; they were model-implied scoring rates from Elo. Calling them simply “xG” overstated what the data represented.

## What was learned

1. **Probability quality matters more than pick accuracy.** A model can call many favorites correctly and still be too confident, lose against the market, and create bad “value” signals.
2. **The market is a mandatory baseline.** On the exact saved sample, bookmaker probabilities beat the model on accuracy, log loss, and Brier. Any future claim should be relative to the market, not just relative to chance.
3. **A simulation is only as valid as its state and bracket.** Increasing from 10,000 to 25,000 runs cannot repair the wrong participant list, random knockout paths, or replayed completed games.
4. **Immutable prediction logs are part of the model.** Without them, a postmortem becomes reconstruction. Forecast time, data time, model version, inputs, outputs, and offered price all need to be stored before kickoff.
5. **Large model–market disagreements are often alerts, not opportunities.** An 89.8% forecast at market odds of 2.45 should first prompt checks for team aliases, reversed home/away mapping, stale ratings, and bad inputs.
6. **Simple models still deserve proper fitting.** The current goal model is a hand-built transformation, not fitted Poisson regression and not Dixon–Coles despite documentation that uses those labels.
7. **Tournament updates should be conditional, not fresh restarts.** Once a match is complete, uncertainty concerns the remaining paths only.
8. **Operational data quality dominated feature scarcity.** Missing odds, zero scorer rows, stale caches, lost dates, and a final still marked scheduled caused more immediate damage than the absence of a boosted-tree layer.

## Bottom line

Keep Elo–Poisson as a transparent benchmark, not as the production truth. The project demonstrated that team strength contains useful signal, but it did not demonstrate a betting edge or a reliable tournament simulator. The next version should earn complexity only after it can replay historical tournaments without leakage, log every forecast immutably, condition on current tournament state, and beat both simple and market baselines out of sample.

Detailed root causes are in [MODEL_PIPELINE_AUDIT_2026.md](MODEL_PIPELINE_AUDIT_2026.md). The implementation sequence and acceptance gates are in [MODEL_IMPROVEMENT_ROADMAP.md](MODEL_IMPROVEMENT_ROADMAP.md).
