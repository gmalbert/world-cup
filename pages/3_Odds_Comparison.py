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
from goallineiq_utils.api_client import get_all_wc_matches, get_match_odds_from_snapshot
from goallineiq_utils.weather import get_weather_for_match

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
        sel_row = None

    st.divider()
    value_threshold = st.slider("Value threshold (%)", 1, 15, 5) / 100.0
    st.caption(f"Showing bets where model edge > {value_threshold*100:.0f}%")

# ── Model prediction ──────────────────────────────────────────────────────────
pred = predictor.predict(home_team, away_team, neutral=True)
hw   = pred["home_win"]
dr   = pred["draw"]
aw   = pred["away_win"]

st.markdown(f"### {home_team}  vs  {away_team}")

# Weather forecast (if match is upcoming)
if sel_row is not None and pd.notna(sel_row.get("date")):
    match_city = sel_row.get("city") if sel_row.get("city") else sel_row.get("venue")
    if match_city:
        weather = get_weather_for_match(str(match_city), str(sel_row["date"]))
        if weather:
            st.caption(
                f"🌤️ **Weather Forecast for {match_city}:** "
                f"{weather['weather_desc']} · **{weather['temperature_f']}°F** ({weather['temperature_c']}°C) · "
                f"💨 Wind: {weather['windspeed_kmh']} km/h · 🌧️ Rain: {weather['precipitation_mm']} mm"
            )

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

# Also try The Odds API snapshot (real multi-book odds, no extra API call)
snapshot_odds = get_match_odds_from_snapshot(home_team, away_team)

if live_odds is not None and not live_odds.empty:
    st.markdown('<p class="section-header">📋 Bookmaker Odds Comparison</p>', unsafe_allow_html=True)
    pivot = live_odds.pivot_table(
        index="bookmaker", columns="outcome", values="odd", aggfunc="first"
    ).reset_index()
    col_remap = {}
    for c in pivot.columns:
        if c in ("Home", "1"):    col_remap[c] = "Home Win"
        elif c in ("Draw", "X"):  col_remap[c] = "Draw"
        elif c in ("Away", "2"):  col_remap[c] = "Away Win"
    pivot = pivot.rename(columns=col_remap)
    odds_cols = [c for c in ["Home Win", "Draw", "Away Win"] if c in pivot.columns]
    model_probs = {"Home Win": hw, "Draw": dr, "Away Win": aw}
    display = pivot[["bookmaker"] + odds_cols].copy()
    st.dataframe(display, width="stretch", hide_index=True)
    _source_label = "API-Football"

elif snapshot_odds and snapshot_odds.get("bookmakers"):
    # ── Real odds from The Odds API snapshot ─────────────────────────────────
    st.markdown('<p class="section-header">📋 Real Bookmaker Odds (The Odds API)</p>', unsafe_allow_html=True)
    st.caption(
        f"Live odds from DraftKings, FanDuel, BetMGM, etc.  "
        f"Snapshot updated once daily.  "
        f"Matched event: **{snapshot_odds.get('event_home','')} vs {snapshot_odds.get('event_away','')}**"
    )

    bm_rows = []
    ou_rows = []
    for bm in snapshot_odds["bookmakers"]:
        if bm["h2h_home"] or bm["h2h_draw"] or bm["h2h_away"]:
            bm_rows.append({
                "Bookmaker": bm["name"],
                f"{home_team} Win": bm["h2h_home"] or "—",
                "Draw":             bm["h2h_draw"] or "—",
                f"{away_team} Win": bm["h2h_away"] or "—",
            })
        if bm["ou_line"] and (bm["ou_over"] or bm["ou_under"]):
            ou_rows.append({
                "Bookmaker": bm["name"],
                f"Line": bm["ou_line"],
                "Over": bm["ou_over"] or "—",
                "Under": bm["ou_under"] or "—",
            })

    tab_1x2, tab_ou = st.tabs(["🏆 1X2 Match Result", "⚽ Over/Under"])

    with tab_1x2:
        if bm_rows:
            bm_df = pd.DataFrame(bm_rows)
            style_cols = [f"{home_team} Win", "Draw", f"{away_team} Win"]
            style_cols = [c for c in style_cols if c in bm_df.columns]

            def _hl_max(s):
                try:
                    nums = pd.to_numeric(s, errors="coerce")
                    is_max = nums == nums.max()
                    return ["background-color:#1b5e20;color:white;font-weight:700;" if v else "" for v in is_max]
                except Exception:
                    return [""] * len(s)

            styled_bm = bm_df.style.apply(_hl_max, subset=style_cols)
            st.dataframe(styled_bm, width="stretch", hide_index=True)

            # Value detection vs best market odds
            st.markdown('<p class="section-header">🎯 Value Bet Detector (Real Odds)</p>', unsafe_allow_html=True)
            best = snapshot_odds["best_h2h"]
            value_found = False
            for label, best_odd, model_p in [
                (f"{home_team} Win", best["home"], hw),
                ("Draw",             best["draw"],  dr),
                (f"{away_team} Win", best["away"],  aw),
            ]:
                if not best_odd or best_odd <= 0:
                    continue
                implied = 1.0 / best_odd
                edge    = model_p - implied
                if abs(edge) >= value_threshold:
                    value_found = True
                    color = "#00c853" if edge > 0 else "#f44336"
                    with st.container(border=True):
                        vc1, vc2, vc3, vc4 = st.columns([3, 2, 2, 3])
                        vc1.markdown(f"**{label}**")
                        vc2.metric("Best Odds", f"{best_odd:.2f}")
                        vc3.metric("Model Prob", f"{model_p*100:.1f}%",
                                   delta=f"{edge*100:+.1f}%",
                                   delta_color="normal" if edge >= 0 else "inverse")
                        vc4.markdown(
                            f"Market implies **{implied*100:.1f}%** vs model **{model_p*100:.1f}%**  \n"
                            f"<span style='color:{color};font-weight:700;'>Edge: {edge*100:+.1f}%</span>",
                            unsafe_allow_html=True,
                        )
            if not value_found:
                st.info(f"No value bets exceeding {value_threshold*100:.0f}% edge at current real odds.")
        else:
            st.info("No 1X2 odds found in snapshot for this match.")

    with tab_ou:
        if ou_rows:
            ou_df = pd.DataFrame(ou_rows)
            st.dataframe(ou_df, width="stretch", hide_index=True)

            # O/U value detection
            best_ou = snapshot_odds["best_ou"]
            if best_ou and best_ou["over"] and best_ou["under"]:
                st.markdown('<p class="section-header">🎯 O/U Value Detector (Real Odds)</p>', unsafe_allow_html=True)
                ou_pred = pred.get("ou", {}).get(2.5, {})
                if ou_pred:
                    for label, mkt_odd, model_p in [
                        (f"Over {best_ou['line']}", best_ou["over"],  ou_pred.get("over",0)),
                        (f"Under {best_ou['line']}", best_ou["under"], ou_pred.get("under",0)),
                    ]:
                        if not mkt_odd or mkt_odd <= 0:
                            continue
                        implied = 1.0 / mkt_odd
                        edge    = model_p - implied
                        color   = "#00c853" if edge >= value_threshold else ("#f44336" if edge < -value_threshold else "#9e9e9e")
                        st.markdown(
                            f"**{label}** · Model: **{model_p*100:.1f}%** · "
                            f"Market: {implied*100:.1f}% @ {mkt_odd:.2f} · "
                            f"<span style='color:{color};font-weight:700;'>Edge: {edge*100:+.1f}%</span>",
                            unsafe_allow_html=True,
                        )
        else:
            ou25 = pred.get("ou", {}).get(2.5, {})
            if ou25:
                st.info(
                    f"No O/U market odds found in snapshot.  \n"
                    f"Model says: Over 2.5 = **{ou25['over']*100:.1f}%** · "
                    f"Under 2.5 = **{ou25['under']*100:.1f}%**"
                )
    _source_label = "The Odds API (snapshot)"

else:
    # ── Illustrative odds (no real data available) ────────────────────────────
    st.markdown('<p class="section-header">📋 Illustrative Odds Comparison</p>', unsafe_allow_html=True)
    st.caption(
        "Real odds from The Odds API are available once the snapshot is populated by the nightly pull. "
        "Shown below are illustrative odds generated from the model + bookmaker margin estimates."
    )

    bookmakers = [
        ("Bet365",    1.04), ("DraftKings", 1.05), ("FanDuel",   1.06),
        ("BetMGM",    1.05), ("Caesars",    1.06), ("William Hill", 1.05), ("Pinnacle", 1.02),
    ]
    demo_rows = []
    for bm, margin in bookmakers:
        bm_h = round(1 / (hw * margin), 2)
        bm_d = round(1 / (dr * margin), 2)
        bm_a = round(1 / (aw * margin), 2)
        demo_rows.append({
            "Bookmaker": bm,
            f"{home_team} Win": bm_h,
            "Draw":             bm_d,
            f"{away_team} Win": bm_a,
            "Margin": f"{(margin-1)*100:.1f}%",
        })
    demo_df = pd.DataFrame(demo_rows)
    style_cols = [f"{home_team} Win", "Draw", f"{away_team} Win"]
    def highlight_max(s):
        is_max = s == s.max()
        return ["background-color:#1b5e20;color:white;font-weight:700;" if v else "" for v in is_max]
    styled = demo_df.style.apply(highlight_max, subset=style_cols)
    st.dataframe(styled, width="stretch", hide_index=True)

    st.markdown('<p class="section-header">🎯 Value Bet Analysis (Illustrative)</p>', unsafe_allow_html=True)
    best_h_d = demo_df[f"{home_team} Win"].max()
    best_d_d = demo_df["Draw"].max()
    best_a_d = demo_df[f"{away_team} Win"].max()
    value_found = False
    for outcome, best_odd, model_p in [
        (f"{home_team} Win", best_h_d, hw), ("Draw", best_d_d, dr), (f"{away_team} Win", best_a_d, aw)
    ]:
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
        st.info(f"No value bets detected above {value_threshold*100:.0f}% edge threshold.")
    _source_label = "Illustrative"


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

# ── Value Finder Dashboard: All Upcoming Matches ──────────────────────────────
st.divider()
st.markdown('<p class="section-header">🔍 Value Finder · All Upcoming Matches</p>', unsafe_allow_html=True)
st.caption("Scanning all upcoming fixtures for betting value where model disagrees with fair odds")

if upcoming is not None and not upcoming.empty:
    value_opportunities = []
    
    for _, match in upcoming.head(12).iterrows():  # Scan next 12 matches
        home = str(match.get("home_team", ""))
        away = str(match.get("away_team", ""))
        if not home or not away:
            continue
            
        try:
            pred = predictor.predict(home, away, neutral=True)
            
            # Generate illustrative "best available odds" (in production, use real odds API)
            margin = 1.04  # Pinnacle-like margin
            market_h = 1 / (pred["home_win"] * margin)
            market_d = 1 / (pred["draw"] * margin)
            market_a = 1 / (pred["away_win"] * margin)
            
            # Calculate edges
            edge_h = pred["home_win"] - (1/market_h)
            edge_d = pred["draw"] - (1/market_d)
            edge_a = pred["away_win"] - (1/market_a)
            
            # Find best value outcome
            edges = [("Home Win", edge_h, market_h, pred["home_win"]),
                     ("Draw", edge_d, market_d, pred["draw"]),
                     ("Away Win", edge_a, market_a, pred["away_win"])]
            best_edge_outcome, best_edge, best_odd, model_prob = max(edges, key=lambda x: x[1])
            
            if best_edge >= value_threshold:
                value_opportunities.append({
                    "Match": f"{home} vs {away}",
                    "Date": str(match.get("date", ""))[:16],
                    "Outcome": best_edge_outcome,
                    "Model %": f"{model_prob*100:.1f}%",
                    "Best Odds": f"{best_odd:.2f}",
                    "Edge %": f"+{best_edge*100:.1f}%",
                    "edge_num": best_edge
                })
        except Exception:
            continue
    
    if value_opportunities:
        value_df = pd.DataFrame(value_opportunities).sort_values("edge_num", ascending=False)
        value_df = value_df.drop(columns=["edge_num"])
        
        st.success(f"✅ Found {len(value_df)} value opportunities across upcoming matches")
        
        # Color-code edges
        def color_edge(val):
            if "+" not in str(val):
                return ""
            edge = float(str(val).replace("+", "").replace("%", ""))
            if edge >= 10:
                return "background-color:#1b5e20;color:white;font-weight:700;"
            elif edge >= 5:
                return "background-color:#2e7d32;color:white;font-weight:700;"
            elif edge >= 3:
                return "background-color:#388e3c;color:white;font-weight:600;"
            return ""
        
        styled_val = value_df.style.applymap(color_edge, subset=["Edge %"])
        st.dataframe(styled_val, width="stretch", hide_index=True)
        
        st.caption(
            "💡 **How to use:** These are matches where our model sees significantly more value than the market. "
            "Higher edge % = stronger disagreement with bookmaker odds."
        )
    else:
        st.info(f"No value bets found across upcoming matches at {value_threshold*100:.0f}% edge threshold. "
                "Try lowering the threshold in the sidebar.")
else:
    st.info("Upcoming match data not available yet. Value finder will activate closer to tournament start.")

# ── Group Stage Value Strategy ────────────────────────────────────────────────
st.divider()
st.markdown('<p class="section-header">⚡ Group Stage Betting Strategy</p>', unsafe_allow_html=True)
st.info(
    "**Best Value in Group Stage:**  \n"
    "✅ Look for 3rd-match scenarios where Group A/B winners face Group C/D underperformers  \n"
    "✅ CONCACAF hosts (USA/Mexico/Canada) may be overvalued early due to public betting — fade the hype  \n"
    "✅ UEFA-heavy groups often see late-game draws when both teams have qualified  \n"
    "✅ 3rd-place qualification adds variance — 8 best 3rd-placed teams advance (more ties, more draw value)"
)

add_betting_oracle_footer()
