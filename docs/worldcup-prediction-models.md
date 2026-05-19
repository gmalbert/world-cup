# World Cup 2026 — Prediction Models & ML Approaches

> Part of a 3-document series. See also:
> - [`worldcup-site-overview.md`](worldcup-site-overview.md) — Data landscape, APIs, legal framework
> - [`worldcup-site-features.md`](worldcup-site-features.md) — Site features, UX and tech stack

---

## 1. The Core Challenge

World Cup prediction is harder than domestic league prediction for one fundamental reason: **data scarcity**. The World Cup produces only 64–104 matches per edition. Contrast this with the Premier League's 380 matches per season, over which a model can learn rich patterns.

The solution is to train on a broader international football dataset and use features that transfer across competitions:
- All international matches (not just WC) since ~2000
- Major qualifying campaigns (UEFA, CONMEBOL, CAF, AFC, CONCACAF)
- Continental championships (Euros, Copa América, AFCON, Asia Cup)
- Key features from club football as proxies for player quality

---

## 2. Model Architecture: Recommended Approach

Research consensus (2026) is that **gradient-boosted tree ensembles (XGBoost/CatBoost) fed with domain-specific rating features outperform standalone statistical models**. The best production systems layer multiple approaches:

```
Layer 1: Base Models
├── Poisson Regression   → Goal count probabilities
├── Elo Rating Model     → Team strength differential
├── XGBoost Classifier   → Match outcome (W/D/L)
└── LSTM / GRU Network   → Recent form & momentum

Layer 2: Meta-Learner
├── Stacking with secondary XGBoost
└── Dynamic weight adjustment per match context

Layer 3: Calibration & Real-Time Adjustment
├── xG-based calibration
├── Team news/injury adjustment
└── Market odds as prior (Pinnacle closing line)
```

For a **solo or small-team project**, start with Layer 1 (Poisson + Elo + XGBoost) and add layers over time.

---

## 3. Model 1: Elo-Based Poisson Regression (Recommended Starting Point)

This is the most academically validated approach for international tournament prediction and was used by multiple teams in the 2017 Soccer Prediction Challenge. It is also relatively easy to implement.

### How It Works

1. **Assign Elo ratings** to each team based on all historical international results. The international Elo rating system (eloratings.net) already does this — just download and use it.

2. **Fit a Poisson regression** for goals scored as a function of:
   - Elo rating difference (attacker minus defender)
   - Home/neutral venue indicator
   - Tournament type (WC vs. qualifier vs. friendly — friendlies get less weight)

3. **Predict goal distributions** for each team independently, then:
   - Compute P(Home Wins), P(Draw), P(Away Wins) by summing over all score combinations
   - Compute over/under probabilities from the combined goal distribution

### Expected Accuracy

- Match outcome accuracy: ~55–65%
- Ranked Probability Score (RPS): ~0.19–0.21
- Comparable to bookmaker implied probabilities for international matches

### Training Data Required

- All international football results from eloratings.net / rsssf.com (free)
- Download from: `https://www.eloratings.net/downloads`
- ~50,000+ international matches available

### Python Sketch

```python
import pandas as pd
import numpy as np
from scipy.stats import poisson
from scipy.optimize import minimize

def poisson_prob(lambda_home, lambda_away, max_goals=10):
    """Compute win/draw/loss probabilities from expected goals."""
    prob_matrix = np.outer(
        poisson.pmf(range(max_goals+1), lambda_home),
        poisson.pmf(range(max_goals+1), lambda_away)
    )
    home_win = np.sum(np.tril(prob_matrix, -1))
    draw     = np.sum(np.diag(prob_matrix))
    away_win = np.sum(np.triu(prob_matrix, 1))
    return home_win, draw, away_win

def expected_goals(elo_home, elo_away, base_rate=1.35, elo_k=400):
    """Convert Elo ratings to expected goals using sigmoid transform."""
    elo_diff = elo_home - elo_away
    home_prob = 1 / (1 + 10**(-elo_diff / elo_k))
    # Scale to goals — tune base_rate on historical data
    lambda_home = base_rate * (home_prob / 0.5)
    lambda_away = base_rate * ((1 - home_prob) / 0.5)
    return lambda_home, lambda_away

# Example: France (Elo 2046) vs Morocco (Elo 1874)
lh, la = expected_goals(2046, 1874)
p_home, p_draw, p_away = poisson_prob(lh, la)
print(f"France win: {p_home:.1%}, Draw: {p_draw:.1%}, Morocco win: {p_away:.1%}")
```

---

## 4. Model 2: XGBoost Classifier (Best Single-Model Accuracy)

XGBoost achieves approximately **67% match outcome accuracy** in research benchmarks, the highest of any single model class for football prediction.

### Feature Engineering

This is where most of the model's value comes from. Features fall into 4 categories:

#### Team Strength Features
| Feature | Source | Notes |
|---|---|---|
| Current Elo rating | eloratings.net | Most important single feature |
| FIFA ranking points | FIFA / scraped | Less precise than Elo but widely cited |
| Squad market value | Transfermarkt | Strong proxy for talent depth |
| Average squad age | Transfermarkt / API | Experience vs. freshness tradeoff |
| Star player presence | Manual / transfer data | Top-10 player in squad (binary) |

#### Recent Form Features
| Feature | Source | Notes |
|---|---|---|
| W/D/L in last 5 matches | API-Football / eloratings | Weighted by recency |
| Goals scored per match (last 5) | API-Football | Use exponential decay weighting |
| Goals conceded per match (last 5) | API-Football | |
| xG for/against (last 5) | Understat / BALLDONTLIE | More stable than raw goals |
| Elo rating trend (3-month change) | eloratings.net | Momentum signal |
| Days since last match | API | Freshness / fatigue |

#### Head-to-Head Features
| Feature | Source | Notes |
|---|---|---|
| All-time H2H record | BALLDONTLIE / rsssf | Win rate vs. this specific opponent |
| Last 5 H2H results | API-Football | |
| Goals scored/conceded vs. this opponent | API-Football | |
| Last meeting score | API-Football | Psychological edge? |

#### Contextual Features
| Feature | Source | Notes |
|---|---|---|
| Tournament stage | Fixture data | Groups vs. knockout (no draws) |
| Venue continent | Fixture data | Home-region advantage |
| Altitude of venue | Manual / stadium data | Matters for some teams |
| Rest days since last match | Computed | Important in knockout rounds |
| Bookmaker implied probability | The Odds API / OddsPapi | Use Pinnacle as the most efficient prior |

### Target Variable Options

For a 3-class classifier (W/D/L):
- Standard: one-hot `[1,0,0]`, `[0,1,0]`, `[0,0,1]`
- Better for calibration: predict continuous probability outputs using `softprob` objective

### Training Setup

```python
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.calibration import CalibratedClassifierCV

# IMPORTANT: Use TimeSeriesSplit — never shuffle sports data
# Future results must not leak into training

tscv = TimeSeriesSplit(n_splits=5)

model = xgb.XGBClassifier(
    objective='multi:softprob',
    num_class=3,
    n_estimators=500,
    max_depth=5,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    eval_metric='mlogloss',
    early_stopping_rounds=50
)

# Calibrate to convert raw probabilities to well-calibrated ones
calibrated = CalibratedClassifierCV(model, cv='prefit', method='isotonic')
```

### Validation Metrics

- **Accuracy:** % of match outcomes correctly predicted (W/D/L)
- **Ranked Probability Score (RPS):** measures calibration across ordered outcomes; lower is better; target <0.20
- **Log Loss:** penalizes overconfident wrong predictions
- **Closing Line Value (CLV):** if your pre-match probability × bookmaker odds > 1.0 at closing, your model has edge

---

## 5. Model 3: Tournament Simulator (Monte Carlo)

Once you have per-match probabilities from Models 1 or 2, the simulator is straightforward:

```python
import numpy as np

def simulate_tournament(teams, group_fixtures, match_probs_fn, n_simulations=10000):
    """
    teams: list of 48 team dicts with group assignments
    group_fixtures: list of all group stage fixtures
    match_probs_fn: function(team_a, team_b) -> (p_a_win, p_draw, p_b_win)
    """
    results = {team['name']: {'QF': 0, 'SF': 0, 'Final': 0, 'Winner': 0}
               for team in teams}

    for sim in range(n_simulations):
        # Simulate group stage
        group_standings = simulate_group_stage(group_fixtures, match_probs_fn)

        # Determine qualified teams (top 2 per group + 8 best 3rd-placed)
        qualifiers = determine_qualifiers(group_standings)

        # Simulate knockout rounds
        champion = simulate_knockouts(qualifiers, match_probs_fn)

        # Record results
        for stage, team in champion.items():
            results[team][stage] += 1

    # Convert to percentages
    return {team: {k: v/n_simulations for k, v in stages.items()}
            for team, stages in results.items()}
```

Run this after every match result to provide updated "probability of winning the tournament" for every remaining team. This is one of the most engaging features on the site — it changes after every goal.

---

## 6. Using Bookmaker Odds as a Prior

**The most important insight in sports betting analytics:** bookmaker closing odds (especially Pinnacle's) are the best predictors of match outcomes available. Rather than ignoring the market, incorporate it:

### Strategy 1: Odds as a Feature
Include Pinnacle's implied probability as an input feature to XGBoost. The model then learns how to deviate from the market based on other features.

### Strategy 2: Bayesian Blending
Blend your model's probability with the market prior:
```
final_prob = α × model_prob + (1 - α) × market_implied_prob
```
Start with α = 0.3 (30% model, 70% market) and tune on historical data. As your model proves itself, increase α.

### Strategy 3: Value Detection
Your model's primary purpose for bettors isn't to replace the market — it's to identify where the market might be wrong:
```
edge = model_probability - bookmaker_implied_probability
if edge > 0.05:  # Model gives >5% more probability than market
    display_as_value_bet()
```

---

## 7. Model Limitations & Honest Communication

Be transparent with users about what models can and cannot do:

### Hard Limits
- **67% accuracy is the ceiling** for match outcome prediction with current approaches — football is fundamentally unpredictable
- Models are calibrated on historical data; major upsets (Iceland 2016, Morocco 2022) happen and no model fully captures them
- Late injury news, team selection surprises, and weather are often not captured in pre-match features
- The World Cup has only been played 22 times — training data is inherently limited

### What to Tell Users
- Frame predictions as **probabilities, not certainties**: "Our model gives Spain a 58% chance of winning, not a guarantee"
- Show **model confidence** — predictions far from 50/50 are more reliable
- Show **historical accuracy** on previous tournaments so users can calibrate trust
- Always include responsible gambling messaging alongside any betting-related content

---

## 8. Evaluation Plan

### Backtesting on 2022 World Cup
Before the 2026 tournament, evaluate your model on Qatar 2022 data (fully available via BALLDONTLIE):
- Train on all international matches up to 2022
- Test on 64 WC 2022 matches
- Report accuracy, RPS, and CLV vs. Pinnacle closing odds

### Live Evaluation During 2026
- Log every prediction before the match kicks off (timestamped)
- After each match, compute whether the predicted outcome was correct
- Display running accuracy on the site — this builds trust and is transparent

### Calibration Check
A well-calibrated model means: of all matches where you predicted 70% chance of a home win, ~70% of those matches should have been home wins. Use a reliability diagram (calibration curve) to verify.

---

## 9. Quick-Start Implementation Plan

For the fastest path to a working model for the 2026 WC:

**Day 1–2:** Data collection
- Download all-time international results from eloratings.net
- Pull WC 2022 and 2026 data from BALLDONTLIE API
- Pull current odds from OddsPapi

**Day 3–4:** Baseline model
- Implement Poisson + Elo model in Python
- Backtest on WC 2022; measure RPS
- Deploy as FastAPI endpoint returning JSON probabilities

**Day 5–7:** XGBoost model
- Build feature engineering pipeline
- Train on international matches 2010–2022
- Validate on WC 2022; compare to Poisson baseline
- Add Pinnacle odds as feature; revalidate

**Week 2+:** Ensemble & simulator
- Blend Poisson and XGBoost outputs
- Build Monte Carlo tournament simulator
- Hook into frontend for live probability updates after results

**Ongoing:** Recalibration
- Retrain/update Elo ratings after each WC 2026 match
- Update form features daily
- Monitor CLV — if your model consistently beats Pinnacle closing lines, you've built something genuinely valuable

---

## 10. Open Source Resources

- **football-data-analysis (GitHub):** Multiple notebooks for Poisson, Elo, Dixon-Coles models in Python
- **StatsBomb open data:** Full 2018 WC event data (every pass, shot, dribble) — free on GitHub
- **WorldFootballR (R package):** Scrapes FBref, Transfermarkt, Understat cleanly
- **Socceraction (Python):** VAEP and xT models for valuing player actions
- **mplsoccer (Python):** Pitch visualization, shot maps, heatmaps for your frontend charts
- **penaltyblog (Python):** Pre-built Dixon-Coles and other football probability models

---

## Appendix: Accuracy Benchmarks (Published Research)

| Model Type | Accuracy (W/D/L) | RPS | Source |
|---|---|---|---|
| Random baseline | 33% | ~0.33 | — |
| Home-team-always-wins | ~45% | ~0.27 | — |
| Bookmaker odds (Pinnacle) | ~54% | ~0.196 | Multiple |
| Elo + Poisson | ~55–58% | ~0.200–0.210 | Gilch & Müller 2018 |
| XGBoost (best features) | ~67% | ~0.193 | Gol Sinyali 2026 |
| CatBoost + pi-ratings | ~55.8% | ~0.1925 | Razali et al. |
| Ensemble (XGB + Elo + NN) | ~65–70% | ~0.190 | Industry estimates |
| Neural Network (LSTM, large data) | 65–98%* | — | Various |

*The 98% neural network figure appears in controlled lab conditions with data leakage concerns — treat with skepticism. Real-world accuracy for NN on football rarely exceeds XGBoost ensembles.

**Target for your model:** Beat Pinnacle's implied accuracy (~54%) on WC matches — if you can reach 58–62% accuracy with good calibration, you have a genuinely useful and defensible product.
