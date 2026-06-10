"""
Tournament Simulator — Monte Carlo simulation of the 2026 FIFA World Cup.
Shows probability of each team advancing through every stage based on
nightly pre-computed simulations (25,000+ iterations).
Stage progression: Group Stage → R32 → R16 → QF → SF → Final → Winner.
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

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
    .win-highlight {color:#00c853;font-weight:800;}
    .disclaimer {background:#1a1c2e;border-radius:8px;padding:0.8rem 1rem;
        border:1px solid #ff1744;font-size:0.78rem;color:#ef9a9a;margin-top:2rem;}
    div[data-testid="stMetricValue"] {color:#00c853;}
</style>
""", unsafe_allow_html=True)

from goallineiq_utils.models import WC2026_GROUPS

# ── Load pre-computed simulation results ──────────────────────────────────────
SIMULATION_FILE = Path(__file__).parent.parent / "data_files" / "tournament_simulation.json"

@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_simulation_results():
    """Load pre-computed Monte Carlo simulation results."""
    if not SIMULATION_FILE.exists():
        return None, None
    
    try:
        with open(SIMULATION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        results_df = pd.DataFrame(data["results"])
        metadata = data["metadata"]
        return results_df, metadata
    except Exception as e:
        st.error(f"Error loading simulation results: {e}")
        return None, None

simulation_results, simulation_metadata = load_simulation_results()

st.title("🎲 Tournament Simulator")
st.caption("Monte Carlo simulation — 25,000+ nightly scenarios of the 2026 FIFA World Cup")
st.divider()

# ── Show simulation metadata ──────────────────────────────────────────────────
if simulation_metadata:
    generated_at = datetime.fromisoformat(simulation_metadata["generated_at"])
    time_ago = datetime.now(timezone.utc) - generated_at
    hours_ago = int(time_ago.total_seconds() / 3600)
    
    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.metric(
            "Simulations Run",
            f"{simulation_metadata['n_simulations']:,}",
            help="Number of full tournament scenarios simulated"
        )
    with col_info2:
        st.metric(
            "Last Updated",
            f"{hours_ago}h ago" if hours_ago > 0 else "< 1h ago",
            help=f"Updated at {generated_at.strftime('%Y-%m-%d %H:%M UTC')}"
        )
    with col_info3:
        st.metric(
            "Teams Analyzed",
            simulation_metadata['num_teams'],
            help="All 48 teams in the 2026 World Cup"
        )
    
    st.info(
        "**How it works:**  \n"
        "Results are pre-computed nightly using our Elo + Poisson model. Each simulation:  \n"
        "1. Simulates all 12 groups (round-robin, Poisson-distributed goals)  \n"
        "2. Selects top 2 per group + 8 best 3rd-placed teams (32 qualifiers)  \n"
        "3. Simulates knockout rounds — no draws; ties go to simulated penalties  \n"
        "4. Updates after every match with latest team data"
    )
    st.divider()

# ── Sidebar controls ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Filter Results")
    all_teams_flat = sorted(set(t for teams in WC2026_GROUPS.values() for t in teams))
    confederation_filter = st.multiselect(
        "Confederation",
        options=["UEFA", "CONMEBOL", "CONCACAF", "CAF", "AFC", "OFC"],
        default=[],
        placeholder="All confederations",
    )
    top_n = st.slider("Show top N teams", 8, 48, 20)
    
    st.divider()
    st.caption(
        "💡 **Note:** Simulations run automatically every night after matches. "
        "This prevents server overload and ensures consistent, up-to-date predictions."
    )

# ── Confederation mapping ─────────────────────────────────────────────────────
CONFEDERATION = {
    # UEFA
    "France": "UEFA", "Spain": "UEFA", "England": "UEFA", "Germany": "UEFA",
    "Portugal": "UEFA", "Netherlands": "UEFA", "Belgium": "UEFA", "Croatia": "UEFA",
    "Denmark": "UEFA", "Switzerland": "UEFA", "Serbia": "UEFA", "Slovakia": "UEFA",
    "Austria": "UEFA", "Turkey": "UEFA", "Ukraine": "UEFA", "Wales": "UEFA",
    "Scotland": "UEFA", "Poland": "UEFA", "Greece": "UEFA", "Romania": "UEFA",
    "Czech Republic": "UEFA", "Hungary": "UEFA",
    # CONMEBOL
    "Brazil": "CONMEBOL", "Argentina": "CONMEBOL", "Uruguay": "CONMEBOL",
    "Colombia": "CONMEBOL", "Ecuador": "CONMEBOL", "Chile": "CONMEBOL",
    "Peru": "CONMEBOL", "Paraguay": "CONMEBOL", "Venezuela": "CONMEBOL",
    # CONCACAF
    "United States": "CONCACAF", "USA": "CONCACAF", "Mexico": "CONCACAF",
    "Canada": "CONCACAF", "Costa Rica": "CONCACAF", "Panama": "CONCACAF",
    "Jamaica": "CONCACAF", "Honduras": "CONCACAF", "Bolivia": "CONCACAF",
    "Suriname": "CONCACAF", "Cuba": "CONCACAF", "Guatemala": "CONCACAF",
    "El Salvador": "CONCACAF",
    # CAF
    "Morocco": "CAF", "Senegal": "CAF", "Nigeria": "CAF", "Cameroon": "CAF",
    "Ghana": "CAF", "Côte d'Ivoire": "CAF", "Ivory Coast": "CAF", "Egypt": "CAF",
    "Algeria": "CAF", "Tunisia": "CAF", "Mali": "CAF", "Zambia": "CAF",
    "Kenya": "CAF", "Tanzania": "CAF", "Libya": "CAF", "Mozambique": "CAF",
    "Sudan": "CAF", "Rwanda": "CAF",
    # AFC
    "Japan": "AFC", "South Korea": "AFC", "Australia": "AFC", "Iran": "AFC",
    "Saudi Arabia": "AFC", "Iraq": "AFC", "Jordan": "AFC", "Bahrain": "AFC",
    "Palestine": "AFC", "Philippines": "AFC", "Indonesia": "AFC",
    "New Zealand": "OFC",
}

# ── Show results ──────────────────────────────────────────────────────────────
if simulation_results is None:
    st.warning(
        "⚠️ **Simulation results not available**  \n"
        "Pre-computed results will be generated during the tournament (June 11 - July 19, 2026). "
        "The simulation runs automatically every night at 5 AM UTC."
    )
else:
    results = simulation_results.copy()
    n_sims = simulation_metadata.get("n_simulations", 25000) if simulation_metadata else 25000

    # Add confederation
    results["Confederation"] = results["team"].map(CONFEDERATION).fillna("Other")

    # Apply confederation filter
    if confederation_filter:
        results = results[results["Confederation"].isin(confederation_filter)]

    results = results.head(top_n)

    st.markdown(
        f'<p class="section-header">Results — {n_sims:,} Simulations</p>',
        unsafe_allow_html=True,
    )

    # ── Winner probability chart ───────────────────────────────────────────────
    tab_chart, tab_table, tab_heatmap = st.tabs(["📊 Chart", "📋 Table", "🗺️ Heatmap"])

    with tab_chart:
        fig_win = px.bar(
            results.head(15),
            x="Winner %", y="team",
            orientation="h",
            color="Winner %",
            color_continuous_scale=["#1a237e", "#00c853"],
            text="Winner %",
            labels={"team": "", "Winner %": "Win Probability (%)"},
            title=f"Tournament Win Probability — Top 15 Teams ({n_sims:,} sims)",
            height=460,
        )
        fig_win.update_traces(
            texttemplate="%{text:.1f}%",
            textposition="outside",
            marker_line_width=0,
        )
        fig_win.update_layout(
            paper_bgcolor=_BG, plot_bgcolor=_BG,
            font_color=_FC, coloraxis_showscale=False,
            yaxis={"categoryorder": "total ascending"},
            margin=dict(l=10, r=60, t=40, b=10),
        )
        st.plotly_chart(fig_win, width="stretch")

    with tab_table:
        # Colour scale for numeric columns
        stage_cols = ["Group Stage", "Round of 32", "Round of 16",
                      "Quarterfinal", "Semifinal", "Final", "Winner %"]
        display_cols = ["rank", "team", "Confederation"] + [c for c in stage_cols if c in results.columns]
        display = results[display_cols].copy()

        def color_pct(val):
            if not isinstance(val, (int, float)):
                return ""
            if val >= 50:
                return "color:#00c853;font-weight:700;"
            elif val >= 20:
                return "color:#ffd600;"
            elif val >= 5:
                return "color:#90caf9;"
            return "color:#757575;"

        numeric_c = [c for c in stage_cols if c in display.columns]
        styled = display.style.applymap(color_pct, subset=numeric_c)
        st.dataframe(styled, width="stretch", hide_index=True)

        st.caption(
            "All values are percentages across simulations.  \n"
            f"**Group Stage** is always 100% (all teams enter). "
            "Simulation used fallback group draw — update groups dict in models.py when official draw is finalised."
        )

    with tab_heatmap:
        stages = [c for c in ["Round of 32", "Round of 16", "Quarterfinal", "Semifinal", "Final", "Winner %"] if c in results.columns]
        hm_data = results.set_index("team")[stages]
        fig_hm = px.imshow(
            hm_data,
            color_continuous_scale="Greens",
            aspect="auto",
            title="Advancement Probability Heatmap (%)",
            labels=dict(color="Probability (%)"),
            height=max(400, len(results) * 22),
        )
        fig_hm.update_layout(
            paper_bgcolor=_BG, plot_bgcolor=_BG,
            font_color=_FC, margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(fig_hm, width="stretch")

    # ── Top 5 highlights ──────────────────────────────────────────────────────
    st.divider()
    st.markdown('<p class="section-header">🏆 Top 5 Contenders</p>', unsafe_allow_html=True)
    top5 = results.head(5)
    c1, c2, c3, c4, c5 = st.columns(5)
    for col, (_, row) in zip([c1, c2, c3, c4, c5], top5.iterrows()):
        winner_col = "Winner %" if "Winner %" in row.index else "Winner"
        with col:
            st.metric(
                label=row["team"],
                value=f"{row.get(winner_col, 0):.1f}%",
                help=f"Final: {row.get('Final', 0):.1f}%  |  SF: {row.get('Semifinal', 0):.1f}%",
            )

    # ── Share card ───────────────────────────────────────────────────────────
    st.divider()
    if not results.empty:
        top1 = results.iloc[0]
        winner_col = "Winner %" if "Winner %" in top1.index else "Winner"
        share_text = (
            f"🏆 According to GoallineIQ's 2026 World Cup Monte Carlo model "
            f"({n_sims:,} simulations):  \n"
            f"→ **{top1['team']}** has the best chance at **{top1.get(winner_col,0):.1f}%** to win it all."
        )
        st.info(share_text)

add_betting_oracle_footer()
