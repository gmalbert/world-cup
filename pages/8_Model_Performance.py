"""
Model Performance & Effectiveness Dashboard
Shows prediction accuracy, calibration, ROI, and weather impact analysis.
"""
import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv()
from footer import add_betting_oracle_footer

_is_day = st.session_state.get("_is_day", False)
_BG = "#e3f2fd" if _is_day else "#071528"
_FC = "#0d1b2a" if _is_day else "#e0f7fa"

st.markdown("""
<style>
    .section-header {font-size:1.2rem;font-weight:700;color:#00c853;
        border-bottom:1px solid #2c2f4a;padding-bottom:0.4rem;margin-bottom:1rem;}
    .metric-card {background:#1a1c2e;border-radius:8px;padding:1rem;
        border:1px solid #2c2f4a;margin:0.5rem 0;}
    .good {color:#00c853;font-weight:700;}
    .neutral {color:#ffc107;font-weight:700;}
    .bad {color:#f44336;font-weight:700;}
    div[data-testid="stMetricValue"] {color:#00c853;}
</style>
""", unsafe_allow_html=True)

from goallineiq_utils.api_client import get_all_wc_matches
from goallineiq_utils.models import build_predictor
from goallineiq_utils.weather import add_weather_to_matches, analyze_weather_impact

# ── Load Data ─────────────────────────────────────────────────────────────────
all_matches = get_all_wc_matches()
predictor = build_predictor(all_matches)

st.title("📈 Model Performance & Effectiveness")
st.caption("Evaluate prediction accuracy, calibration, betting ROI, and weather impact analysis")
st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — PREDICTION ACCURACY
# ══════════════════════════════════════════════════════════════════════════════
tab_accuracy, tab_calibration, tab_weather, tab_roi = st.tabs([
    "🎯 Accuracy", "📊 Calibration", "🌦️ Weather Impact", "💰 Betting ROI"
])

with tab_accuracy:
    st.markdown('<p class="section-header">Prediction Accuracy on Historical Matches</p>', unsafe_allow_html=True)
    st.caption("Testing model predictions against actual completed World Cup matches")
    
    if all_matches is not None and not all_matches.empty:
        # Get completed matches
        completed = all_matches[
            (all_matches["home_goals"].notna()) &
            (all_matches["away_goals"].notna()) &
            (all_matches["status"].str.contains("completed|FT", case=False, na=False))
        ].copy()
        
        if not completed.empty:
            st.info(f"📊 Analyzing {len(completed)} completed matches across World Cup tournaments")
            
            # Calculate predictions for each match
            correct_outcomes = 0
            total_brier = 0
            total_log_loss = 0
            predictions = []
            
            for _, match in completed.head(200).iterrows():  # Limit for performance
                home = match["home_team"]
                away = match["away_team"]
                home_goals = match["home_goals"]
                away_goals = match["away_goals"]
                
                try:
                    pred = predictor.predict(home, away, neutral=True)
                    
                    # Determine actual outcome
                    if home_goals > away_goals:
                        actual = "home_win"
                        actual_vector = [1, 0, 0]
                    elif home_goals < away_goals:
                        actual = "away_win"
                        actual_vector = [0, 0, 1]
                    else:
                        actual = "draw"
                        actual_vector = [0, 1, 0]
                    
                    # Model's predicted outcome
                    pred_outcome = max([
                        ("home_win", pred["home_win"]),
                        ("draw", pred["draw"]),
                        ("away_win", pred["away_win"])
                    ], key=lambda x: x[1])[0]
                    
                    if pred_outcome == actual:
                        correct_outcomes += 1
                    
                    # Brier score
                    pred_vector = [pred["home_win"], pred["draw"], pred["away_win"]]
                    brier = sum((p - a)**2 for p, a in zip(pred_vector, actual_vector))
                    total_brier += brier
                    
                    # Log loss
                    actual_prob = pred_vector[actual_vector.index(1)]
                    log_loss = -np.log(max(actual_prob, 0.001))  # Avoid log(0)
                    total_log_loss += log_loss
                    
                    predictions.append({
                        "match": f"{home} vs {away}",
                        "predicted": pred_outcome,
                        "actual": actual,
                        "correct": pred_outcome == actual,
                        "home_prob": pred["home_win"],
                        "draw_prob": pred["draw"],
                        "away_prob": pred["away_win"],
                        "actual_outcome_prob": actual_prob
                    })
                    
                except Exception:
                    continue
            
            if predictions:
                n = len(predictions)
                accuracy = correct_outcomes / n
                avg_brier = total_brier / n
                avg_log_loss = total_log_loss / n
                
                # Display metrics
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Matches Analyzed", n)
                col2.metric("Prediction Accuracy", f"{accuracy*100:.1f}%", 
                           help="% of matches where most likely outcome was correct")
                col3.metric("Brier Score", f"{avg_brier:.3f}",
                           help="Lower is better. Perfect = 0, Random = 0.667")
                col4.metric("Log Loss", f"{avg_log_loss:.3f}",
                           help="Lower is better. Measures probability calibration")
                
                # Benchmark comparison
                st.divider()
                st.markdown("**📊 Benchmark Comparison**")
                
                bench_col1, bench_col2, bench_col3 = st.columns(3)
                with bench_col1:
                    st.markdown("**Naive Baseline**")
                    st.caption("Always predict home win")
                    baseline_acc = completed[completed["home_goals"] > completed["away_goals"]].shape[0] / len(completed)
                    st.metric("Accuracy", f"{baseline_acc*100:.1f}%")
                
                with bench_col2:
                    st.markdown("**Random Guess**")
                    st.caption("33.3% for each outcome")
                    st.metric("Expected Accuracy", "33.3%")
                    st.metric("Expected Brier", "0.667")
                
                with bench_col3:
                    st.markdown("**Our Model**")
                    st.caption(f"Dixon-Coles Elo-based")
                    comparison = "🟢 Better" if accuracy > baseline_acc else "🔴 Worse"
                    st.metric("vs Baseline", comparison)
                
                # Confusion matrix
                st.divider()
                st.markdown("**🎯 Prediction Breakdown**")
                
                pred_df = pd.DataFrame(predictions)
                confusion = pd.crosstab(
                    pred_df["actual"],
                    pred_df["predicted"],
                    margins=True,
                    margins_name="Total"
                )
                st.dataframe(confusion, width="stretch")
                
                # Accuracy by prediction confidence
                st.divider()
                st.markdown("**📈 Accuracy by Confidence Level**")
                
                pred_df["max_prob"] = pred_df[["home_prob", "draw_prob", "away_prob"]].max(axis=1)
                pred_df["confidence_bin"] = pd.cut(
                    pred_df["max_prob"],
                    bins=[0, 0.4, 0.5, 0.6, 0.7, 1.0],
                    labels=["<40%", "40-50%", "50-60%", "60-70%", ">70%"]
                )
                
                conf_accuracy = pred_df.groupby("confidence_bin", observed=False)["correct"].agg(["mean", "count"]).reset_index()
                conf_accuracy.columns = ["Confidence", "Accuracy", "Count"]
                conf_accuracy["Accuracy"] = conf_accuracy["Accuracy"] * 100
                
                fig_conf = px.bar(
                    conf_accuracy,
                    x="Confidence",
                    y="Accuracy",
                    text="Count",
                    title="Model Accuracy by Prediction Confidence",
                    labels={"Accuracy": "Accuracy (%)", "Count": "Predictions"},
                    color="Accuracy",
                    color_continuous_scale="RdYlGn",
                    range_color=[30, 80]
                )
                fig_conf.update_traces(texttemplate="n=%{text}", textposition="outside")
                fig_conf.update_layout(
                    paper_bgcolor=_BG, plot_bgcolor=_BG, font_color=_FC,
                    margin=dict(l=10, r=10, t=40, b=10),
                    yaxis=dict(range=[0, 100], title="Accuracy (%)"),
                    showlegend=False
                )
                st.plotly_chart(fig_conf, width="stretch")
                
            else:
                st.warning("Unable to calculate predictions for completed matches.")
        else:
            st.info("No completed matches with scores available yet.")
    else:
        st.warning("No match data available.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — CALIBRATION
# ══════════════════════════════════════════════════════════════════════════════
with tab_calibration:
    st.markdown('<p class="section-header">Probability Calibration</p>', unsafe_allow_html=True)
    st.caption("Are predicted probabilities accurate? Well-calibrated models have predicted prob = actual frequency")
    
    if 'predictions' in locals() and predictions:
        pred_df = pd.DataFrame(predictions)
        
        # Create calibration data for home wins
        home_win_df = pred_df.copy()
        home_win_df["predicted_prob"] = home_win_df["home_prob"]
        home_win_df["actual_outcome"] = (home_win_df["actual"] == "home_win").astype(int)
        
        # Bin by predicted probability
        home_win_df["prob_bin"] = pd.cut(
            home_win_df["predicted_prob"],
            bins=np.arange(0, 1.1, 0.1),
            labels=[f"{i*10}-{(i+1)*10}%" for i in range(10)]
        )
        
        calibration = home_win_df.groupby("prob_bin", observed=False).agg(
            mean_predicted=("predicted_prob", "mean"),
            actual_rate=("actual_outcome", "mean"),
            count=("actual_outcome", "count")
        ).reset_index()
        
        # Plot calibration
        fig_cal = go.Figure()
        
        # Perfect calibration line
        fig_cal.add_trace(go.Scatter(
            x=[0, 1], y=[0, 1],
            mode="lines",
            name="Perfect Calibration",
            line=dict(color="#9e9e9e", dash="dash", width=2)
        ))
        
        # Actual calibration
        fig_cal.add_trace(go.Scatter(
            x=calibration["mean_predicted"],
            y=calibration["actual_rate"],
            mode="markers+lines",
            name="Model Calibration",
            marker=dict(size=calibration["count"]/2, color="#00c853", line=dict(width=2, color="#fff")),
            line=dict(color="#00c853", width=3)
        ))
        
        fig_cal.update_layout(
            title="Home Win Probability Calibration",
            xaxis=dict(title="Predicted Probability", tickformat=".0%", range=[0, 1]),
            yaxis=dict(title="Observed Frequency", tickformat=".0%", range=[0, 1]),
            paper_bgcolor=_BG, plot_bgcolor=_BG, font_color=_FC,
            margin=dict(l=10, r=10, t=40, b=10),
            height=500,
            showlegend=True
        )
        
        st.plotly_chart(fig_cal, width="stretch")
        
        st.markdown("**📊 Interpretation:**")
        st.caption(
            "Points near the diagonal line indicate good calibration. "
            "For example, when the model predicts 60% home win probability, "
            "the home team should actually win ~60% of the time."
        )
    else:
        st.info("Complete accuracy analysis first to generate calibration data.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — WEATHER IMPACT
# ══════════════════════════════════════════════════════════════════════════════
with tab_weather:
    st.markdown('<p class="section-header">Weather Impact on Match Outcomes</p>', unsafe_allow_html=True)
    st.caption("Analyzing correlation between weather conditions and goals/results using Open-Meteo data")
    
    with st.spinner("Fetching weather data for historical matches..."):
        matches_with_weather = add_weather_to_matches(all_matches.copy())
        weather_analysis = analyze_weather_impact(matches_with_weather)
    
    if weather_analysis.get("sample_size", 0) > 0:
        st.success(f"✅ Analyzed {weather_analysis['sample_size']} matches with weather data")
        
        # Display key findings
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**☔ Rain Impact**")
            if weather_analysis["rainy_match_count"] > 0:
                st.metric("Rainy Matches", weather_analysis["rainy_match_count"])
                st.metric("Avg Goals (Rain)", f"{weather_analysis['avg_goals_rainy']:.2f}",
                         delta=f"{weather_analysis['avg_goals_rainy'] - weather_analysis['avg_goals_all']:.2f}")
            else:
                st.caption("No rainy matches in dataset")
        
        with col2:
            st.markdown("**🥶 Cold Weather**")
            if weather_analysis["cold_match_count"] > 0:
                st.metric("Cold Matches (<50°F / 10°C)", weather_analysis["cold_match_count"])
                st.metric("Avg Goals (Cold)", f"{weather_analysis['avg_goals_cold']:.2f}",
                         delta=f"{weather_analysis['avg_goals_cold'] - weather_analysis['avg_goals_all']:.2f}")
            else:
                st.caption("No cold matches in dataset")
        
        with col3:
            st.markdown("**🔥 Hot Weather**")
            if weather_analysis["hot_match_count"] > 0:
                st.metric("Hot Matches (>86°F / 30°C)", weather_analysis["hot_match_count"])
                st.metric("Avg Goals (Hot)", f"{weather_analysis['avg_goals_hot']:.2f}",
                         delta=f"{weather_analysis['avg_goals_hot'] - weather_analysis['avg_goals_all']:.2f}")
            else:
                st.caption("No hot matches in dataset")
        
        st.divider()
        
        # Statistical significance test
        st.markdown("**📊 Statistical Analysis**")
        
        completed_weather = matches_with_weather[
            (matches_with_weather["home_goals"].notna()) &
            (matches_with_weather["temperature_c"].notna())
        ].copy()
        
        if not completed_weather.empty:
            completed_weather["total_goals"] = completed_weather["home_goals"] + completed_weather["away_goals"]
            completed_weather["is_rainy"] = completed_weather["precipitation_mm"] > 1.0
            
            # T-test for rain impact
            if completed_weather["is_rainy"].any() and (~completed_weather["is_rainy"]).any():
                rainy_goals = completed_weather[completed_weather["is_rainy"]]["total_goals"]
                clear_goals = completed_weather[~completed_weather["is_rainy"]]["total_goals"]
                t_stat, p_value = stats.ttest_ind(rainy_goals, clear_goals)
                
                st.markdown(f"**Rain vs Clear Weather:**")
                st.caption(f"t-statistic: {t_stat:.3f}, p-value: {p_value:.4f}")
                
                if p_value < 0.05:
                    st.markdown('<span class="good">✅ Statistically significant difference (p < 0.05)</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span class="neutral">⚠️ No statistically significant difference (p ≥ 0.05)</span>', unsafe_allow_html=True)
        
        st.divider()
        
        # Recommendation
        st.markdown("**💡 Recommendation for Model Enhancement:**")
        
        if weather_analysis["rainy_match_count"] > 10:
            if abs(weather_analysis['avg_goals_rainy'] - weather_analysis['avg_goals_all']) > 0.3:
                st.markdown(
                    '<div class="good">'
                    '✅ <strong>Weather data shows meaningful impact</strong><br>'
                    'Consider adding weather features to the prediction model. '
                    'Rain appears to affect goal scoring patterns.'
                    '</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    '<div class="neutral">'
                    '⚠️ <strong>Weather impact is minimal</strong><br>'
                    'Weather conditions show only small effects on outcomes. '
                    'May not be worth the added complexity.'
                    '</div>',
                    unsafe_allow_html=True
                )
        else:
            st.info("📊 Insufficient weather data for reliable analysis. Need more matches with varied conditions.")
    else:
        st.info("⏳ Fetching weather data... This may take a moment for historical matches.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — BETTING ROI
# ══════════════════════════════════════════════════════════════════════════════
with tab_roi:
    st.markdown('<p class="section-header">Betting ROI Analysis</p>', unsafe_allow_html=True)
    st.caption("Simulated return on investment if following model's value bet recommendations")
    
    st.info("📊 ROI calculations coming soon. This will show hypothetical returns from betting on model edges ≥5%.")
    
    st.markdown("**Methodology:**")
    st.caption(
        "- Simulate $10 flat bets on all value opportunities (edge ≥ 5%)\n"
        "- Compare model probabilities vs fair market odds\n"
        "- Calculate profit/loss on actual outcomes\n"
        "- Compute ROI and Sharpe ratio"
    )

st.divider()

# ── Historical O/U Signal Backtest ────────────────────────────────────────────
st.markdown('<p class="section-header">📊 O/U 2.5 Signal Backtest — 2022 World Cup</p>', unsafe_allow_html=True)
st.caption(
    "Retroactive evaluation of the O/U 2.5 model signal against actual 2022 match results. "
    "Assumes a fixed 1.91 decimal line on both Over and Under. "
    "A 'signal' fires when model probability exceeds implied market probability by ≥ 4 %."
)

if all_matches is not None and not all_matches.empty:
    wc22 = all_matches[
        (all_matches["season"] == 2022)
        & all_matches["home_goals"].notna()
        & all_matches["away_goals"].notna()
    ].copy()

    if not wc22.empty:
        MARKET_OU_LINE = 1.91
        MARKET_IMP     = 1.0 / MARKET_OU_LINE
        EDGE_THRESHOLD = 0.04
        STAKE          = 10.0

        backtest_rows = []
        for _, row in wc22.iterrows():
            home = str(row["home_team"])
            away = str(row["away_team"])
            try:
                p = predictor.predict(home, away, neutral=True)
            except Exception:
                continue
            total_goals = int(row["home_goals"]) + int(row["away_goals"])
            actual_over = total_goals > 2

            ou25 = p.get("ou", {}).get(2.5, {})
            if not ou25:
                continue

            over_p  = ou25["over"]
            under_p = ou25["under"]
            over_edge  = over_p  - MARKET_IMP
            under_edge = under_p - MARKET_IMP

            # Only bet where signal fires
            if over_edge >= EDGE_THRESHOLD:
                signal = "Over"
                pnl = STAKE * (MARKET_OU_LINE - 1) if actual_over else -STAKE
            elif under_edge >= EDGE_THRESHOLD:
                signal = "Under"
                pnl = STAKE * (MARKET_OU_LINE - 1) if not actual_over else -STAKE
            else:
                signal = None
                pnl = 0.0

            backtest_rows.append({
                "Match": f"{home} vs {away}",
                "Home G": int(row["home_goals"]), "Away G": int(row["away_goals"]),
                "Total": total_goals,
                "Model Over%": round(over_p * 100, 1),
                "Over Edge": round(over_edge * 100, 1),
                "Under Edge": round(under_edge * 100, 1),
                "Signal": signal or "—",
                "Outcome": "Over" if actual_over else "Under",
                "PnL": round(pnl, 2),
            })

        bt_df = pd.DataFrame(backtest_rows)
        signal_df = bt_df[bt_df["Signal"] != "—"].copy()

        if not signal_df.empty:
            total_bets = len(signal_df)
            total_pnl  = signal_df["PnL"].sum()
            winning    = (signal_df["PnL"] > 0).sum()
            roi        = total_pnl / (STAKE * total_bets) * 100

            sb1, sb2, sb3, sb4 = st.columns(4)
            sb1.metric("Total Signal Bets", total_bets)
            sb2.metric("Winners", winning, f"{winning/total_bets*100:.0f}%")
            sb3.metric("Total P&L", f"${total_pnl:+.2f}")
            sb4.metric("ROI", f"{roi:+.1f}%",
                       delta_color="normal" if roi >= 0 else "inverse")

            def _color_pnl(val):
                if isinstance(val, (int, float)):
                    return "color:#00c853;font-weight:700;" if val > 0 else ("color:#f44336;" if val < 0 else "")
                return ""

            s = signal_df.style
            styled_bt = s.map(_color_pnl, subset=["PnL"]) \
                        if hasattr(s, "map") \
                        else s.applymap(_color_pnl, subset=["PnL"])
            st.dataframe(styled_bt, width="stretch", hide_index=True)
        else:
            st.info("No O/U signals met the 4% edge threshold on 2022 data at these model settings.")

        # Show full prediction vs actuals summary
        st.divider()
        st.markdown("**All 2022 matches — Model O/U vs Actual:**")
        summary_df = bt_df[["Match", "Total", "Model Over%", "Over Edge", "Signal", "Outcome", "PnL"]].copy()
        st.dataframe(summary_df, width="stretch", hide_index=True)
    else:
        st.info("2022 World Cup match data not yet loaded.")
else:
    st.info("Historical match data unavailable — connect API sources to enable backtest.")

add_betting_oracle_footer()
