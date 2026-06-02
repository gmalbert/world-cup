# GoallineIQ — Model Suggested Enhancements

## Priority 1: Elo Model

### World Cup Specific Adjustments
- Club Elo and international Elo differ significantly. Calibrate the `FALLBACK_ELO` values using historical World Cup results (not club data).
- Apply a regression-to-mean at the start of each knockout round (momentum carry should be partial, not full).

### Player Availability Impact
- Key players absent (injury, suspension) in major tournaments shift probabilities significantly.
- Add a `key_player_absent_adj` parameter: when a top-3 ranked squad member is out, apply a calibrated −5 to −12 Elo adjustment.

### Tournament Stage Weighting
- Group stage matches have different incentive structures than knockout rounds.
- Apply a `neutral_court_adj` (already present) and a `tournament_stage_multiplier` for knockout rounds.

## Priority 2: Dixon-Coles Goal Model

### Rho Re-Estimation
- Dixon-Coles `rho` correction is for low-scoring draws. World Cup matches tend to have fewer draws than club football; recalibrate `rho` on historical World Cup data.

### Squad Quality Integration
- Blend individual player-level FiFA ratings (available as historical CSVs) with Elo as an attack feature.

## Priority 3: Group Stage Simulation

### Tiebreaker Simulation
- Group advancement depends on goal difference, goals scored, and H2H results when teams are level on points.
- Ensure `simulator.py` applies all FIFA tiebreaker rules in order.

### Group Draw Difficulty
- Encode `group_strength` (sum of Elo ratings of group opponents) as a feature for predicting group winners.

## Priority 4: Calibration

- Track model accuracy per round (group stage, R16, quarters, semis, final) in historical simulations.
- Apply Platt scaling to knockout-round probability outputs.
