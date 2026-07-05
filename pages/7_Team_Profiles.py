"""
Team Profiles — Comprehensive team intelligence dashboard with Elo history,
squad depth, playing style, recent form, World Cup history, and head-to-head records.
"""
import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

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
    .team-header {font-size:2.5rem;font-weight:800;margin-bottom:0;}
    .stat-card {border-radius:10px;padding:1rem;margin:0.5rem 0;}
    .style-badge {background:#1565c0;color:#fff;padding:4px 10px;border-radius:6px;
        font-size:0.85rem;font-weight:700;margin:0 4px;}
    .wc-trophy {color:#ffd700;font-size:1.2rem;}
</style>
""", unsafe_allow_html=True)

from goallineiq_utils.api_client import get_all_wc_matches
from goallineiq_utils.models import build_predictor, WC2026_GROUPS, FALLBACK_ELO

# ── Load data ─────────────────────────────────────────────────────────────────
all_matches = get_all_wc_matches()
predictor = build_predictor(all_matches)

st.title("🏆 Team Intelligence Hub")
st.caption("Deep-dive analysis · Elo history · Playing style · World Cup heritage")
st.divider()

# ── Team selector ─────────────────────────────────────────────────────────────
all_teams = sorted(set(t for teams in WC2026_GROUPS.values() for t in teams))

selected_team = st.selectbox(
    "Select Team",
    all_teams,
    index=all_teams.index("Brazil") if "Brazil" in all_teams else 0
)

# ── Team header with flag and quick stats ────────────────────────────────────
FLAG_MAP = {
    "Argentina": "🇦🇷", "Brazil": "🇧🇷", "France": "🇫🇷", "Germany": "🇩🇪", 
    "Spain": "🇪🇸", "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Portugal": "🇵🇹", "Netherlands": "🇳🇱",
    "Belgium": "🇧🇪", "Croatia": "🇭🇷", "Uruguay": "🇺🇾", "Colombia": "🇨🇴",
    "Mexico": "🇲🇽", "USA": "🇺🇸", "Canada": "🇨🇦", "Morocco": "🇲🇦",
    "Senegal": "🇸🇳", "Japan": "🇯🇵", "South Korea": "🇰🇷", "Australia": "🇦🇺",
    "Denmark": "🇩🇰", "Switzerland": "🇨🇭", "Italy": "🇮🇹", "Poland": "🇵🇱",
    "Chile": "🇨🇱", "Ecuador": "🇪🇨", "Peru": "🇵🇪", "Costa Rica": "🇨🇷",
    "Nigeria": "🇳🇬", "Cameroon": "🇨🇲", "Ghana": "🇬🇭", "Egypt": "🇪🇬",
    "Algeria": "🇩🇿", "Tunisia": "🇹🇳", "Iran": "🇮🇷", "Saudi Arabia": "🇸🇦",
}

flag = FLAG_MAP.get(selected_team, "🏴")

# World Cup titles (simplified data)
WC_TITLES = {
    "Brazil": 5, "Germany": 4, "Italy": 4, "Argentina": 3, "France": 2,
    "Uruguay": 2, "Spain": 1, "England": 1
}
titles = WC_TITLES.get(selected_team, 0)

st.markdown(
    f'<div class="team-header">{flag} {selected_team} ' +
    (f'<span class="wc-trophy">{"🏆" * titles}</span>' if titles > 0 else '') +
    '</div>',
    unsafe_allow_html=True
)
st.caption(f"FIFA World Cup Analysis — {titles} {'title' if titles == 1 else 'titles'}")
st.divider()

# ── Current Elo and form ──────────────────────────────────────────────────────
try:
    pred = predictor.predict(selected_team, selected_team, neutral=True)
    current_elo = int(pred["home_elo"])
except Exception:
    current_elo = FALLBACK_ELO.get(selected_team, 1500)

# Calculate rank among 2026 teams
team_elos = {}
for team in all_teams:
    try:
        p = predictor.predict(team, team, neutral=True)
        team_elos[team] = int(p["home_elo"])
    except Exception:
        team_elos[team] = FALLBACK_ELO.get(team, 1500)

sorted_teams = sorted(team_elos.items(), key=lambda x: x[1], reverse=True)
rank = next(i for i, (t, e) in enumerate(sorted_teams, 1) if t == selected_team)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Current Elo Rating", f"{current_elo}", help="Higher = Stronger team")
col2.metric("2026 Rank", f"#{rank} / 48", help="Rank among all qualified teams")

# Recent form (last 5 matches)
team_matches = all_matches[
    (all_matches["home_team"] == selected_team) | 
    (all_matches["away_team"] == selected_team)
].copy()

if not team_matches.empty:
    team_matches = team_matches.sort_values("date", ascending=False).head(5)
    wins = 0
    draws = 0
    losses = 0
    
    for _, m in team_matches.iterrows():
        is_home = m["home_team"] == selected_team
        hg, ag = m.get("home_goals", 0), m.get("away_goals", 0)
        
        if pd.notna(hg) and pd.notna(ag):
            if (is_home and hg > ag) or (not is_home and ag > hg):
                wins += 1
            elif hg == ag:
                draws += 1
            else:
                losses += 1
    
    form_str = f"{wins}W-{draws}D-{losses}L"
    form_pct = (wins * 3 + draws) / (len(team_matches) * 3) * 100 if len(team_matches) > 0 else 0
    
    col3.metric("Recent Form (Last 5)", form_str, f"{form_pct:.0f}% pts")
    col4.metric("Matches Analyzed", len(team_matches), help="Historical matches in database")
else:
    col3.metric("Recent Form", "N/A", help="No recent match data")
    col4.metric("Matches Analyzed", 0)

st.divider()

# ── Elo history trend ─────────────────────────────────────────────────────────
st.markdown('<p class="section-header">📈 Elo Rating Trend</p>', unsafe_allow_html=True)

if not team_matches.empty:
    # Simulate Elo progression (in production, track actual Elo changes)
    elo_history = []
    base_elo = current_elo
    
    for i, (_, m) in enumerate(reversed(list(team_matches.iterrows()))):
        date = m.get("date", "")
        # Simple simulation: vary Elo based on result
        is_home = m["home_team"] == selected_team
        hg, ag = m.get("home_goals", 0), m.get("away_goals", 0)
        
        if pd.notna(hg) and pd.notna(ag):
            if (is_home and hg > ag) or (not is_home and ag > hg):
                delta = 15
            elif hg == ag:
                delta = 0
            else:
                delta = -15
        else:
            delta = 0
        
        base_elo = base_elo - delta * (len(team_matches) - i) / len(team_matches)
        elo_history.append({"date": date, "elo": int(base_elo)})
    
    elo_history.reverse()
    elo_df = pd.DataFrame(elo_history)
    
    if not elo_df.empty and "date" in elo_df.columns:
        elo_df["date"] = pd.to_datetime(elo_df["date"], errors="coerce")
        elo_df = elo_df.dropna(subset=["date"]).sort_values("date")
        
        fig_elo = go.Figure()
        fig_elo.add_trace(go.Scatter(
            x=elo_df["date"],
            y=elo_df["elo"],
            mode="lines+markers",
            line=dict(color="#00c853", width=3),
            marker=dict(size=8),
            name="Elo Rating"
        ))
        
        fig_elo.update_layout(
            paper_bgcolor=_BG,
            plot_bgcolor=_BG,
            font_color=_FC,
            height=350,
            xaxis=dict(title="Date", showgrid=True, gridcolor="#2c2f4a"),
            yaxis=dict(title="Elo Rating", showgrid=True, gridcolor="#2c2f4a"),
            hovermode="x unified"
        )
        
        st.plotly_chart(fig_elo, width="stretch")
    else:
        st.info("Insufficient date data to plot Elo trend")
else:
    st.info(f"No historical match data available for {selected_team}")

st.divider()

# ── Playing style analysis ────────────────────────────────────────────────────
st.markdown('<p class="section-header">⚽ Playing Style & Tactical Profile</p>', unsafe_allow_html=True)

# Simplified style classification based on historical data
if not team_matches.empty:
    avg_goals_scored = team_matches.apply(
        lambda m: m["home_goals"] if m["home_team"] == selected_team else m["away_goals"],
        axis=1
    ).mean()
    
    avg_goals_conceded = team_matches.apply(
        lambda m: m["away_goals"] if m["home_team"] == selected_team else m["home_goals"],
        axis=1
    ).mean()
    
    # Classify style
    if avg_goals_scored > 2.0:
        attack_style = "Attacking"
    elif avg_goals_scored > 1.2:
        attack_style = "Balanced"
    else:
        attack_style = "Defensive"
    
    if avg_goals_conceded < 0.8:
        defense_style = "Solid Defense"
    elif avg_goals_conceded < 1.5:
        defense_style = "Average Defense"
    else:
        defense_style = "Vulnerable Defense"
    
    style_col1, style_col2 = st.columns(2)
    
    with style_col1:
        with st.container(border=True):
            st.markdown(f"### 🎯 Attack Rating")
            st.metric("Goals per Match", f"{avg_goals_scored:.2f}")
            st.markdown(
                f'<span class="style-badge">{attack_style}</span>',
                unsafe_allow_html=True
            )
    
    with style_col2:
        with st.container(border=True):
            st.markdown(f"### 🛡️ Defense Rating")
            st.metric("Goals Conceded per Match", f"{avg_goals_conceded:.2f}")
            st.markdown(
                f'<span class="style-badge">{defense_style}</span>',
                unsafe_allow_html=True
            )
    
    st.info(
        f"**Tactical Summary:** {selected_team} plays an {attack_style.lower()} style, "
        f"averaging {avg_goals_scored:.1f} goals scored and {avg_goals_conceded:.1f} conceded per match. "
        f"Their defense is classified as '{defense_style.lower()}'."
    )
else:
    st.info("Playing style analysis requires historical match data")

st.divider()

# ── Head-to-head vs top teams ─────────────────────────────────────────────────
st.markdown('<p class="section-header">🥊 Head-to-Head vs Elite Teams</p>', unsafe_allow_html=True)
st.caption("Model predictions against top-ranked opponents · Neutral venue")

top_opponents = ["Brazil", "France", "Spain", "England", "Germany", "Argentina", "Portugal", "Netherlands"]
top_opponents = [t for t in top_opponents if t != selected_team][:6]

h2h_data = []
for opp in top_opponents:
    try:
        pred = predictor.predict(selected_team, opp, neutral=True)
        h2h_data.append({
            "Opponent": opp,
            "Win %": f"{pred['home_win']*100:.1f}%",
            "Draw %": f"{pred['draw']*100:.1f}%",
            "Lose %": f"{pred['away_win']*100:.1f}%",
            "xG": f"{pred['home_xg']:.2f}",
            "Opp xG": f"{pred['away_xg']:.2f}",
            "win_num": pred['home_win']
        })
    except Exception:
        continue

if h2h_data:
    h2h_df = pd.DataFrame(h2h_data).sort_values("win_num", ascending=False)
    h2h_df = h2h_df.drop(columns=["win_num"])
    
    st.dataframe(h2h_df, width="stretch", hide_index=True)
    st.caption("💡 These matchups assume neutral venue. Host advantage would shift probabilities for USA/Mexico/Canada.")
else:
    st.info("Head-to-head analysis not available")

st.divider()

# ── World Cup history ─────────────────────────────────────────────────────────
st.markdown('<p class="section-header">🏆 World Cup Heritage</p>', unsafe_allow_html=True)

# Historical World Cup data (simplified)
WC_HISTORY = {
    "Brazil": {"titles": 5, "finals": 7, "best": "🏆 Champions (5x)", "years": "1958, 1962, 1970, 1994, 2002"},
    "Germany": {"titles": 4, "finals": 8, "best": "🏆 Champions (4x)", "years": "1954, 1974, 1990, 2014"},
    "Italy": {"titles": 4, "finals": 6, "best": "🏆 Champions (4x)", "years": "1934, 1938, 1982, 2006"},
    "Argentina": {"titles": 3, "finals": 6, "best": "🏆 Champions (3x)", "years": "1978, 1986, 2022"},
    "France": {"titles": 2, "finals": 4, "best": "🏆 Champions (2x)", "years": "1998, 2018"},
    "Uruguay": {"titles": 2, "finals": 2, "best": "🏆 Champions (2x)", "years": "1930, 1950"},
    "Spain": {"titles": 1, "finals": 1, "best": "🏆 Champions (1x)", "years": "2010"},
    "England": {"titles": 1, "finals": 1, "best": "🏆 Champions (1x)", "years": "1966"},
}

if selected_team in WC_HISTORY:
    history = WC_HISTORY[selected_team]
    wc_col1, wc_col2, wc_col3 = st.columns(3)
    wc_col1.metric("World Cup Titles", f"🏆 {history['titles']}")
    wc_col2.metric("Finals Reached", history['finals'])
    wc_col3.metric("Best Finish", history['best'])
    st.caption(f"**Championship Years:** {history['years']}")
else:
    st.info(f"{selected_team} has not won a FIFA World Cup title yet. 2026 could be their year!")

add_betting_oracle_footer()
