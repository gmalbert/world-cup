"""
Odds Comparison — Multi-bookmaker odds, implied probability vs. model,
value bet detector, and odds movement.
"""
import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

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
    .value-cell {background:#1b5e20;color:#fff;padding:2px 6px;border-radius:4px;font-weight:700;}
    .best-odds {color:#00c853;font-weight:800;}
    .disclaimer {background:#1a1c2e;border-radius:8px;padding:0.8rem 1rem;
        border:1px solid #ff1744;font-size:0.78rem;color:#ef9a9a;margin-top:2rem;}
    div[data-testid="stMetricValue"] {color:#00c853;}
</style>
""", unsafe_allow_html=True)

from goallineiq_utils.api_client import get_upcoming_matches, apf_client
from goallineiq_utils.models import build_predictor, get_predictor, FALLBACK_ELO, WC2026_GROUPS
from goallineiq_utils.api_client import get_all_wc_matches

# ── Load ──────────────────────────────────────────────────────────────────────
all_matches = get_all_wc_matches()
predictor   = build_predictor(all_matches)

st.title("💰 Odds Comparison & Value Bets")
st.caption("Compare bookmaker odds · Detect value where model disagrees with the market")
st.divider()

# ── Match selector ────────────────────────────────────────────────────────────
upcoming = get_upcoming_matches(n=20)

with st.sidebar:
    st.markdown("### Select Match")

    if upcoming is not None and not upcoming.empty:
        upcoming["label"] = upcoming.apply(
            lambda r: f"{r.get('home_team','?')} vs {r.get('away_team','?')}",
            axis=1,
        )
        sel_label = st.selectbox("Fixture", upcoming["label"].tolist())
        sel_row   = upcoming[upcoming["label"] == sel_label].iloc[0]
        home_team = str(sel_row["home_team"])
        away_team = str(sel_row["away_team"])
        fixture_id = sel_row.get("id")
    else:
        all_teams = sorted(set(t for teams in WC2026_GROUPS.values() for t in teams))
        home_team  = st.selectbox("Team A", all_teams, index=0)
        away_team  = st.selectbox("Team B", all_teams, index=1)
        fixture_id = None

    st.divider()
    value_threshold = st.slider("Value threshold (%)", 1, 15, 5) / 100.0
    st.caption(f"Showing bets where model edge > {value_threshold*100:.0f}%")

# ── Model prediction ──────────────────────────────────────────────────────────
pred = predictor.predict(home_team, away_team, neutral=True)
hw   = pred["home_win"]
dr   = pred["draw"]
aw   = pred["away_win"]

st.markdown(f"### {home_team}  vs  {away_team}")
st.caption(f"Elo: {int(pred['home_elo'])} vs {int(pred['away_elo'])}  ·  Model xG: {pred['home_xg']:.2f} – {pred['away_xg']:.2f}")
st.divider()

# ── Fair odds from model ──────────────────────────────────────────────────────
fair_h = round(1 / hw, 2) if hw > 0 else 0
fair_d = round(1 / dr, 2) if dr > 0 else 0
fair_a = round(1 / aw, 2) if aw > 0 else 0

mc1, mc2, mc3 = st.columns(3)
mc1.metric(f"Model: {home_team} Win", f"{hw*100:.1f}%", help=f"Fair odds: {fair_h}")
mc2.metric("Model: Draw",             f"{dr*100:.1f}%", help=f"Fair odds: {fair_d}")
mc3.metric(f"Model: {away_team} Win", f"{aw*100:.1f}%", help=f"Fair odds: {fair_a}")

st.divider()

# ── Live odds from API-Football ───────────────────────────────────────────────
live_odds = pd.DataFrame()
if fixture_id:
    live_odds = apf_client.get_fixture_odds(int(fixture_id))

if live_odds is not None and not live_odds.empty:
    st.markdown('<p class="section-header">📋 Bookmaker Odds Comparison</p>', unsafe_allow_html=True)

    # Pivot: bookmaker × outcome
    pivot = live_odds.pivot_table(
        index="bookmaker", columns="outcome", values="odd", aggfunc="first"
    ).reset_index()

    # Map columns to Home / Draw / Away
    col_remap = {}
    for c in pivot.columns:
        if c in ("Home", "1"):
            col_remap[c] = "Home Win"
        elif c in ("Draw", "X"):
            col_remap[c] = "Draw"
        elif c in ("Away", "2"):
            col_remap[c] = "Away Win"
    pivot = pivot.rename(columns=col_remap)

    odds_cols = [c for c in ["Home Win", "Draw", "Away Win"] if c in pivot.columns]
    model_probs = {"Home Win": hw, "Draw": dr, "Away Win": aw}

    # Highlight best odds
    display = pivot[["bookmaker"] + odds_cols].copy()
    for col in odds_cols:
        if col in display.columns:
            max_val = display[col].max()
            implied = 1.0 / display[col].where(display[col] > 0, np.nan)
            edge    = model_probs.get(col, 0) - (1.0 / max_val if max_val > 0 else 0)

    st.dataframe(display, width="stretch", hide_index=True)

    # Value bets
    st.markdown('<p class="section-header">🎯 Value Bet Detector</p>', unsafe_allow_html=True)
    value_found = False
    for col in odds_cols:
        if col not in display.columns:
            continue
        best_odd = display[col].max()
        if best_odd <= 0:
            continue
        bm_name = display.loc[display[col].idxmax(), "bookmaker"]
        implied  = 1.0 / best_odd
        model_p  = model_probs.get(col, 0)
        edge     = model_p - implied

        if edge >= value_threshold:
            value_found = True
            with st.container(border=True):
                vc1, vc2, vc3, vc4 = st.columns([3, 2, 2, 3])
                vc1.markdown(f"**{col}**  \n`{home_team} vs {away_team}`")
                vc2.metric("Best Odds", f"{best_odd}", help=f"Bookmaker: {bm_name}")
                vc3.metric("Model Prob", f"{model_p*100:.1f}%", delta=f"+{edge*100:.1f}% vs market")
                vc4.markdown(
                    f"Our model gives **{model_p*100:.1f}%** probability; "
                    f"{bm_name} implies **{implied*100:.1f}%** — "
                    f"a **{edge*100:.1f}% edge**.",
                )

    if not value_found:
        st.info(f"No value bets exceeding {value_threshold*100:.0f}% edge detected at current odds.")

else:
    # ── Demo/illustrative odds table ─────────────────────────────────────────
    st.markdown('<p class="section-header">📋 Illustrative Odds Comparison</p>', unsafe_allow_html=True)
    st.caption(
        "Live odds are fetched from API-Football when a fixture ID is available. "
        "Shown below are illustrative odds generated from the model + bookmaker margin estimates."
    )

    bookmakers = [
        ("Bet365",    1.04), ("DraftKings", 1.05), ("FanDuel",   1.06),
        ("BetMGM",    1.05), ("Caesars",    1.06), ("Unibet",    1.04),
        ("William Hill", 1.05), ("Pinnacle", 1.02),
    ]

    demo_rows = []
    for bm, margin in bookmakers:
        bm_h = round(1 / (hw * margin), 2)
        bm_d = round(1 / (dr * margin), 2)
        bm_a = round(1 / (aw * margin), 2)
        noise_h = np.random.uniform(-0.04, 0.04)
        noise_d = np.random.uniform(-0.03, 0.03)
        noise_a = np.random.uniform(-0.04, 0.04)
        demo_rows.append({
            "Bookmaker": bm,
            f"{home_team} Win": round(bm_h + noise_h, 2),
            "Draw":             round(bm_d + noise_d, 2),
            f"{away_team} Win": round(bm_a + noise_a, 2),
            "Overround":        f"{(margin-1)*100:.1f}%",
        })

    demo_df = pd.DataFrame(demo_rows)

    # Highlight best odds per column
    style_cols = [f"{home_team} Win", "Draw", f"{away_team} Win"]
    def highlight_max(s):
        is_max = s == s.max()
        return ["background-color:#1b5e20;color:white;font-weight:700;" if v else "" for v in is_max]

    styled = demo_df.style.apply(highlight_max, subset=style_cols)
    st.dataframe(styled, width="stretch", hide_index=True)

    # Value bet analysis against demo odds
    st.markdown('<p class="section-header">🎯 Value Bet Analysis</p>', unsafe_allow_html=True)

    best_h = demo_df[f"{home_team} Win"].max()
    best_d = demo_df["Draw"].max()
    best_a = demo_df[f"{away_team} Win"].max()

    outcomes = [
        (f"{home_team} Win", best_h, hw),
        ("Draw", best_d, dr),
        (f"{away_team} Win", best_a, aw),
    ]

    value_found = False
    for outcome, best_odd, model_p in outcomes:
        if best_odd <= 0:
            continue
        implied = 1.0 / best_odd
        edge    = model_p - implied
        if abs(edge) >= value_threshold:
            value_found = True
            color = "#00c853" if edge > 0 else "#f44336"
            with st.container(border=True):
                vc1, vc2, vc3 = st.columns(3)
                vc1.markdown(f"**{outcome}**  \nBest odds: `{best_odd}`")
                vc2.metric("Model Probability", f"{model_p*100:.1f}%")
                vc3.markdown(
                    f"Market implies: {implied*100:.1f}%  \n"
                    f"<span style='color:{color};font-weight:700;'>Edge: {edge*100:+.1f}%</span>",
                    unsafe_allow_html=True,
                )

    if not value_found:
        st.info(f"No value bets detected above {value_threshold*100:.0f}% edge threshold in the illustrative odds.")

    # Overround chart
    st.divider()
    st.markdown('<p class="section-header">📉 Bookmaker Margin (Overround)</p>', unsafe_allow_html=True)
    st.caption("Lower overround = closer to fair value. Pinnacle typically has the lowest margin.")

    demo_df["Overround_num"] = [m[1] - 1 for m in bookmakers]
    fig_over = go.Figure(go.Bar(
        x=demo_df["Bookmaker"],
        y=demo_df["Overround_num"] * 100,
        marker_color=["#00c853" if x == demo_df["Overround_num"].min() else "#2c5f2e"
                      for x in demo_df["Overround_num"]],
        text=[f"{x*100:.1f}%" for x in demo_df["Overround_num"]],
        textposition="outside",
    ))
    fig_over.update_layout(
        title="Bookmaker Margin (%)", height=300,
        paper_bgcolor=_BG, plot_bgcolor=_BG,
        font_color=_FC, margin=dict(l=10, r=10, t=40, b=10),
        yaxis=dict(title="Overround %", ticksuffix="%"),
    )
    st.plotly_chart(fig_over, width="stretch")


# ── Implied probability radar ─────────────────────────────────────────────────
st.divider()
st.markdown('<p class="section-header">📊 Implied Probability Summary</p>', unsafe_allow_html=True)

sample_bm_odds = [
    ("Pinnacle (sharp)",   round(1/(hw*1.02), 2), round(1/(dr*1.02), 2), round(1/(aw*1.02), 2)),
    ("Bet365",             round(1/(hw*1.06), 2), round(1/(dr*1.06), 2), round(1/(aw*1.06), 2)),
    ("DraftKings",         round(1/(hw*1.05), 2), round(1/(dr*1.05), 2), round(1/(aw*1.05), 2)),
    ("GoallineIQ Model",   fair_h, fair_d, fair_a),
]

fig_ip = go.Figure()
categories = [f"{home_team} Win", "Draw", f"{away_team} Win"]
for bm, oh, od, oa in sample_bm_odds:
    probs = [round(1/oh*100, 1), round(1/od*100, 1), round(1/oa*100, 1)] if all(o > 0 for o in [oh, od, oa]) else [33.3, 33.3, 33.3]
    color = "#00c853" if "Model" in bm else None
    fig_ip.add_trace(go.Bar(
        name=bm,
        x=categories,
        y=probs,
        text=[f"{p:.1f}%" for p in probs],
        textposition="outside",
        marker_color=color,
    ))

fig_ip.update_layout(
    barmode="group", height=350,
    paper_bgcolor=_BG, plot_bgcolor=_BG,
    font_color=_FC, margin=dict(l=10, r=10, t=10, b=10),
    yaxis=dict(title="Implied Probability %", ticksuffix="%"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
)
st.plotly_chart(fig_ip, width="stretch")

add_betting_oracle_footer()
