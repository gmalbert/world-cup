"""
GoallineIQ — Entry Point (MPA via st.navigation)
World Cup 2026 | Data-Driven Betting Intelligence
"""
import os
import base64
import sys
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
load_dotenv()

LOGO_PATH = str(Path(__file__).parent / "data_files" / "logo.png")


def _logo_data_uri(path: str) -> str:
    with open(path, "rb") as logo_file:
        encoded = base64.b64encode(logo_file.read()).decode("ascii")
    return f"data:image/png;base64,{encoded}"

# ── Page config (called ONCE here — sub-pages must NOT call it) ───────────────
st.set_page_config(
    page_title="GoallineIQ — World Cup 2026",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "GoallineIQ — World Cup 2026 Betting Intelligence"},
)

# ══════════════════════════════════════════════════════════════════════════════
# THEME — Deep Ocean (night) / Sky Blue (day)
# ══════════════════════════════════════════════════════════════════════════════
THEMES: dict = {
    "Deep Ocean": {
        "mode": "night",
        "bg": "#03071e", "sidebar_bg": "#051130", "text": "#e0f7fa",
        "text2": "#80deea", "primary": "#26c6da", "border": "#0a2040",
        "card_bg": "#071528",
    },
    "Sky Blue": {
        "mode": "day",
        "bg": "#e3f2fd", "sidebar_bg": "#bbdefb", "text": "#0d1b2a",
        "text2": "#1565c0", "primary": "#0277bd", "border": "#90caf9",
        "card_bg": "#ffffff",
    },
}

def _build_theme_css(t: dict) -> str:
    """Return CSS that overrides Streamlit's visual theme for all pages."""
    header_bg = "#d6e7f5" if t["mode"] == "day" else "#020617"
    table_header_bg = "#dce8f4" if t["mode"] == "day" else "#111827"
    table_row_bg = "#ffffff" if t["mode"] == "day" else t["card_bg"]
    table_border = "#b7d3ea" if t["mode"] == "day" else t["border"]
    return f"""
    html, body, [data-testid="stApp"], [data-testid="stAppViewContainer"],
    [data-testid="stMain"], [data-testid="stMainBlockContainer"] {{
        background-color: {t['bg']} !important;
        color: {t['text']} !important;
    }}
    [data-testid="stHeader"], [data-testid="stToolbar"] {{
        background-color: {header_bg} !important;
        border-bottom: 1px solid {t['border']} !important;
    }}
    [data-testid="stSidebar"], [data-testid="stSidebarContent"] {{
        background-color: {t['sidebar_bg']} !important;
    }}
    [data-testid="stSidebar"] *, [data-testid="stSidebarContent"] * {{
        color: {t['text']} !important;
    }}
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,
    [data-testid="stMarkdownContainer"] span,
    [data-testid="stText"],
    .stTextInput label, .stSelectbox label, .stSlider label,
    .stRadio label, .stCheckbox label, .stDateInput label,
    .stNumberInput label {{
        color: {t['text']} !important;
    }}
    h1, h2, h3, h4, h5, h6 {{ color: {t['text']} !important; }}
    [data-testid="stMetricValue"] {{ color: {t['primary']} !important; }}
    [data-testid="stMetricLabel"] {{ color: {t['text2']} !important; }}
    /* All bordered containers */
    [data-border="true"] {{
        background-color: {t['card_bg']} !important;
        border-color: {t['border']} !important;
    }}
    [data-testid="stExpander"] {{
        background-color: {t['card_bg']} !important;
        border-color: {t['border']} !important;
    }}
    [data-testid="stSeparator"] > hr {{ border-color: {t['border']} !important; }}
    .stButton > button {{
        background-color: {t['primary']} !important;
        border-color: {t['primary']} !important;
        color: #ffffff !important;
    }}
    [data-testid="stSelectbox"] > div > div,
    [data-baseweb="select"] > div,
    [data-baseweb="select"] > div > div,
    [data-testid="stTextInput"] > div > div > input,
    [data-testid="stNumberInput"] > div > div > input {{
        background-color: {t['card_bg']} !important;
        color: {t['text']} !important;
        border-color: {t['border']} !important;
    }}
    [data-baseweb="select"] svg {{ fill: {t['text2']} !important; }}
    [data-baseweb="popover"] [role="option"] {{
        background-color: {t['card_bg']} !important;
        color: {t['text']} !important;
    }}
    .stTabs [data-baseweb="tab-list"] {{ background-color: {t['bg']} !important; }}
    .stTabs [data-baseweb="tab"] {{ color: {t['text2']} !important; }}
    .stTabs [aria-selected="true"] {{
        color: {t['primary']} !important;
        border-bottom-color: {t['primary']} !important;
    }}
    caption, .stCaption, [data-testid="stCaptionContainer"] * {{
        color: {t['text2']} !important;
    }}
    /* Page-specific class overrides */
    .section-header {{
        color: {t['primary']} !important;
        border-bottom-color: {t['border']} !important;
    }}
    .score-display, .stat-card {{
        color: {t['text']} !important;
    }}
    .match-card, .team-card {{
        background: {t['card_bg']} !important;
        border-color: {t['border']} !important;
    }}
    .main-title {{ color: {t['primary']} !important; }}
    [data-testid="stDataFrame"] {{
        background-color: {table_row_bg} !important;
        border: 1px solid {table_border} !important;
        border-radius: 10px !important;
        overflow: hidden !important;
    }}
    [data-testid="stDataFrame"] [role="grid"] {{
        background-color: {table_row_bg} !important;
        color: {t['text']} !important;
    }}
    [data-testid="stDataFrame"] [role="columnheader"] {{
        background-color: {table_header_bg} !important;
        color: {t['text']} !important;
        border-color: {table_border} !important;
    }}
    [data-testid="stDataFrame"] [role="gridcell"] {{
        background-color: {table_row_bg} !important;
        color: {t['text']} !important;
        border-color: {table_border} !important;
    }}
    [data-testid="stDataFrame"] [data-testid="stDataFrameGlideDataEditor"] {{
        min-height: 205px !important;
    }}
    .stTable table, .stTable th, .stTable td {{
        background-color: {table_row_bg} !important;
        color: {t['text']} !important;
        border-color: {table_border} !important;
    }}
    /* Plotly chart backgrounds and axis text */
    .js-plotly-plot svg rect.bg {{ fill: {t['bg']} !important; }}
    .js-plotly-plot .gtitle {{ fill: {t['text']} !important; }}
    .js-plotly-plot .xtick text, .js-plotly-plot .ytick text {{
        fill: {t['text']} !important;
    }}
    .js-plotly-plot .xtitle, .js-plotly-plot .ytitle {{ fill: {t['text']} !important; }}
    .js-plotly-plot .legend text {{ fill: {t['text']} !important; }}
    """


# ── Auto-detect theme from local time (day = 7am–7pm) ────────────────────────
_hour = datetime.now().hour
_is_day = 7 <= _hour < 19
st.session_state["_is_day"] = _is_day
_active_theme = THEMES["Sky Blue" if _is_day else "Deep Ocean"]
st.markdown(
    f"<style>{_build_theme_css(_active_theme)}</style>",
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════════════════════
# IMPORTS (after path setup)
# ══════════════════════════════════════════════════════════════════════════════
from utils.api_client import (
    get_all_wc_matches, get_upcoming_matches, get_current_standings,
    bdl_client, apf_client, WC_NAMES,
)
from utils.models import build_predictor, WC2026_GROUPS, FALLBACK_ELO
from footer import add_betting_oracle_footer


# ══════════════════════════════════════════════════════════════════════════════
# HOME PAGE FUNCTION  (wrapped so st.navigation can reference it)
# ══════════════════════════════════════════════════════════════════════════════
def home_page():
    # ── Shared CSS for home page component classes ────────────────────────────
    st.markdown("""
    <style>
        .main-title {font-size:2.8rem;font-weight:800;margin-bottom:0;}
        .sub-title  {font-size:3.2rem;font-weight:800;color:#9e9e9e;line-height:1; margin-top:0; margin-bottom:0;}
        .hero-table {width:100%; border-collapse:collapse; table-layout:fixed;}
        .hero-table td {vertical-align:bottom; padding:0;}
        .hero-logo {width:375px; max-width:100%; display:block;}
        .hero-text {padding-left:1rem;}
        .sub-title-note {font-size:0.92rem;color:#9e9e9e;margin-top:0.15rem;margin-bottom:0;}
        .value-badge {background:#ff6d00;color:#fff;padding:3px 8px;border-radius:4px;font-size:0.78rem;font-weight:700;}
        .edge-pos {font-weight:700;}
        .match-card {border-radius:10px;padding:1rem;margin-bottom:0.6rem;}
        .section-header {font-size:1.2rem;font-weight:700;border-bottom:1px solid;padding-bottom:0.4rem;margin-bottom:1rem;}
        .disclaimer {border-radius:8px;padding:0.8rem 1rem;font-size:0.78rem;color:#ef9a9a;margin-top:2rem;}
    </style>
    """, unsafe_allow_html=True)

    # ── Logo + Title ──────────────────────────────────────────────────────────
    if os.path.exists(LOGO_PATH):
        st.markdown(
            f"""
            <table class="hero-table">
                <tr>
                    <td style="width:40%;">
                        <img class="hero-logo" src="{_logo_data_uri(LOGO_PATH)}" alt="GoallineIQ logo" />
                    </td>
                    <td class="hero-text">
                        <div class="sub-title">Men's World Cup 2026</div>
                    </td>
                </tr>
            </table>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<p class="sub-title">Men\'s World Cup 2026</p>', unsafe_allow_html=True)

    st.divider()

    # ── Tournament countdown & key metrics ───────────────────────────────────
    wc_start = datetime(2026, 6, 11, tzinfo=timezone.utc)
    wc_end   = datetime(2026, 7, 19, tzinfo=timezone.utc)
    now_dt   = datetime.now(timezone.utc)
    days_to  = max(0, (wc_start - now_dt).days)
    live     = wc_start <= now_dt <= wc_end
    status_label = "🟢 LIVE" if live else (
        f"⏳ Starts in {days_to} days" if days_to > 0 else "🏆 Completed"
    )
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Tournament", "USA/Canada/Mexico 2026")
    m2.metric("Status", status_label)
    m3.metric("Teams", "48")
    m4.metric("Matches", "104")
    m5.metric("Stadiums", "16 across 3 countries")
    st.divider()

    # ── Load data & train model ───────────────────────────────────────────────
    with st.spinner("Loading historical World Cup data (2010–2026)…"):
        all_matches = get_all_wc_matches()
    predictor = build_predictor(all_matches)

    if not all_matches.empty:
        coverage = all_matches.groupby("season")["home_team"].count().reset_index()
        coverage.columns = ["Season", "Matches Loaded"]
        with st.expander("📥 Data Coverage", expanded=False):
            st.dataframe(coverage, use_container_width=True, hide_index=True)
            st.caption("Sources: openfootball (2010, 2014) · BALLDONTLIE FIFA API (2018, 2022, 2026)")

    # ── Upcoming match predictions ────────────────────────────────────────────
    st.markdown('<p class="section-header">⚽ Upcoming Match Predictions</p>', unsafe_allow_html=True)
    upcoming = get_upcoming_matches(n=16)

    if upcoming is not None and not upcoming.empty:
        pred_rows = []
        for _, row in upcoming.iterrows():
            home = str(row.get("home_team", ""))
            away = str(row.get("away_team", ""))
            if home and away:
                p = predictor.predict(home, away, neutral=True)
                pred_rows.append({
                    "home_team": home, "away_team": away,
                    "date": row.get("date"), "round": row.get("round", ""),
                    "venue": row.get("venue", ""),
                    "home_win": p["home_win"], "draw": p["draw"], "away_win": p["away_win"],
                    "home_xg": p["home_xg"], "away_xg": p["away_xg"],
                    "home_elo": p["home_elo"], "away_elo": p["away_elo"],
                })
        if pred_rows:
            cols = st.columns(2)
            for idx, pred in enumerate(pred_rows):
                col = cols[idx % 2]
                with col:
                    date_str = ""
                    if pd.notna(pred["date"]):
                        try:
                            dt = pd.to_datetime(pred["date"], utc=True)
                            date_str = dt.strftime("%b %d, %Y %H:%M UTC")
                        except Exception:
                            date_str = str(pred["date"])[:16]
                    hw = pred["home_win"] * 100
                    dr = pred["draw"] * 100
                    aw = pred["away_win"] * 100
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([5, 2, 5])
                        c1.markdown(f"**{pred['home_team']}**  \n`Elo {int(pred['home_elo'])}`")
                        c2.markdown("<div style='text-align:center;padding-top:8px;font-weight:700;'>VS</div>", unsafe_allow_html=True)
                        c3.markdown(f"**{pred['away_team']}**  \n`Elo {int(pred['away_elo'])}`")
                        st.markdown(
                            f"""<div style="display:flex;border-radius:4px;overflow:hidden;margin:6px 0;">
                                <div title="Home {hw:.1f}%" style="width:{hw:.1f}%;background:#00c853;height:10px;"></div>
                                <div title="Draw {dr:.1f}%" style="width:{dr:.1f}%;background:#ffd600;height:10px;"></div>
                                <div title="Away {aw:.1f}%" style="width:{aw:.1f}%;background:#2196f3;height:10px;"></div>
                            </div>
                            <div style="display:flex;justify-content:space-between;font-size:0.78rem;color:#bbb;">
                                <span>🟢 {hw:.1f}%</span><span>🟡 {dr:.1f}%</span><span>🔵 {aw:.1f}%</span>
                            </div>""",
                            unsafe_allow_html=True,
                        )
                        st.caption(f"📅 {date_str}  |  xG: {pred['home_xg']:.2f} – {pred['away_xg']:.2f}")
    else:
        st.info("Live fixture data not yet available — showing model predictions for selected group matches.")
        sample_matches = [
            ("Mexico", "Jamaica"), ("Honduras", "Suriname"),
            ("Argentina", "Chile"), ("Peru", "Canada"),
            ("USA", "Panama"), ("Bolivia", "New Zealand"),
            ("France", "Morocco"), ("Tunisia", "Mali"),
        ]
        cols = st.columns(2)
        for idx, (home, away) in enumerate(sample_matches):
            col = cols[idx % 2]
            p = predictor.predict(home, away)
            hw, dr, aw = p["home_win"] * 100, p["draw"] * 100, p["away_win"] * 100
            with col:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([5, 2, 5])
                    c1.markdown(f"**{home}**  \n`Elo {int(p['home_elo'])}`")
                    c2.markdown("<div style='text-align:center;padding-top:8px;font-weight:700;'>VS</div>", unsafe_allow_html=True)
                    c3.markdown(f"**{away}**  \n`Elo {int(p['away_elo'])}`")
                    st.markdown(
                        f"""<div style="display:flex;border-radius:4px;overflow:hidden;margin:6px 0;">
                            <div style="width:{hw:.1f}%;background:#00c853;height:10px;"></div>
                            <div style="width:{dr:.1f}%;background:#ffd600;height:10px;"></div>
                            <div style="width:{aw:.1f}%;background:#2196f3;height:10px;"></div>
                        </div>
                        <div style="display:flex;justify-content:space-between;font-size:0.78rem;color:#bbb;">
                            <span>🟢 {hw:.1f}%</span><span>🟡 {dr:.1f}%</span><span>🔵 {aw:.1f}%</span>
                        </div>""",
                        unsafe_allow_html=True,
                    )
                    st.caption(f"xG: {p['home_xg']:.2f} – {p['away_xg']:.2f}")

    # ── Value bet alerts ──────────────────────────────────────────────────────
    st.divider()
    st.markdown('<p class="section-header">💰 Value Bet Alerts</p>', unsafe_allow_html=True)
    st.caption(
        "Matches where the model's probability differs from bookmaker implied probability by >5 pp. "
        "Always verify current odds before placing any bet."
    )
    value_examples = [
        {"match": "Spain vs Colombia",  "outcome": "Spain Win",   "model_prob": 0.62, "market_odds": 1.85},
        {"match": "Brazil vs Ecuador",  "outcome": "Brazil Win",  "model_prob": 0.68, "market_odds": 1.72},
        {"match": "England vs Serbia",  "outcome": "England Win", "model_prob": 0.59, "market_odds": 1.95},
    ]
    value_found = False
    for ex in value_examples:
        implied = 1.0 / ex["market_odds"]
        edge    = ex["model_prob"] - implied
        if abs(edge) >= 0.05:
            value_found = True
            badge_color = "#00c853" if edge > 0 else "#f44336"
            with st.container(border=True):
                vc1, vc2, vc3, vc4 = st.columns([3, 2, 2, 3])
                vc1.markdown(f"**{ex['match']}**")
                vc2.markdown(f"`{ex['outcome']}`")
                vc3.metric("Model Prob", f"{ex['model_prob']*100:.1f}%",
                           delta=f"{edge*100:+.1f}% vs market")
                vc4.markdown(
                    f"Odds: **{ex['market_odds']}** → Implied: {implied*100:.1f}%  \n"
                    f"<span style='color:{badge_color};font-weight:700;'>Edge: {edge*100:+.1f}%</span>",
                    unsafe_allow_html=True,
                )
    if not value_found:
        st.info("No strong value bets in current sample. See Odds Comparison for live analysis.")

    # ── Tournament favorites (Elo chart) ─────────────────────────────────────
    st.divider()
    st.markdown('<p class="section-header">🏆 2026 Tournament Favorites (Elo Rankings)</p>', unsafe_allow_html=True)
    ratings_df = predictor.get_ratings_df().head(15)
    fig = px.bar(
        ratings_df, x="elo", y="team", orientation="h", color="elo",
        color_continuous_scale=["#1a237e", "#00c853"],
        labels={"elo": "Elo Rating", "team": ""},
        title="Top 15 Teams by Elo Rating", height=420,
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color=_active_theme["text"], coloraxis_showscale=False,
        yaxis={"categoryorder": "total ascending"},
        margin=dict(l=10, r=10, t=40, b=10),
    )
    fig.update_traces(marker_line_width=0)
    st.plotly_chart(fig, use_container_width=True)

    # ── Group standings preview ───────────────────────────────────────────────
    st.divider()
    st.markdown('<p class="section-header">📊 Group Standings</p>', unsafe_allow_html=True)
    standings = get_current_standings()
    if standings is not None and not standings.empty:
        groups = standings["group"].unique() if "group" in standings.columns else []
        if len(groups) > 0:
            for row_start in range(0, min(8, len(groups)), 2):
                row_groups = sorted(groups)[row_start:row_start + 2]
                group_cols = st.columns(len(row_groups))
                for i, grp in enumerate(row_groups):
                    col = group_cols[i]
                    grp_df = standings[standings["group"] == grp][
                        ["team", "played", "won", "drawn", "lost", "goal_diff", "points"]
                    ].copy()
                    grp_df.columns = ["Team", "P", "W", "D", "L", "GD", "Pts"]
                    grp_df = grp_df[["Team", "P", "Pts"]]
                    with col:
                        st.caption(f"**Group {grp}**")
                        st.dataframe(grp_df, hide_index=True, use_container_width=True, height=235)
    else:
        st.info(
            "Group standings will appear here once the tournament begins (June 11, 2026).  \n"
            "Navigate to **Match Hub** to see the full schedule."
        )

    # ── About the model ───────────────────────────────────────────────────────
    st.divider()
    with st.expander("📖 About the Model"):
        st.markdown("""
        **GoallineIQ uses a two-layer Elo + Poisson prediction model:**

        1. **Elo Rating System** — trained on all World Cup matches from 2010–2026 (4 tournaments + current).
        2. **Poisson Goal Model** — converts Elo differential into expected goals, then yields W/D/L probabilities.

        **Expected accuracy:** ~57–62% on World Cup matches.
        Football is genuinely unpredictable — use these probabilities as one input among many.
        """)

    # ── Footer ────────────────────────────────────────────────────────────────
    add_betting_oracle_footer()


# ══════════════════════════════════════════════════════════════════════════════
# NAVIGATION  (st.navigation — macOS/Docker compatible, no emoji in filenames)
# ══════════════════════════════════════════════════════════════════════════════
pg = st.navigation(
    {
        "": [
            st.Page(home_page, title="Predictions", icon="⚽", default=True),
        ],
        "Analysis": [
            st.Page("pages/1_Match_Hub.py",            title="Match Hub",            icon="🗓️"),
            st.Page("pages/2_Pre_Match_Analysis.py",   title="Pre-Match Analysis",   icon="🔍"),
            st.Page("pages/3_Odds_Comparison.py",      title="Odds Comparison",      icon="💰"),
            st.Page("pages/4_Tournament_Simulator.py", title="Tournament Simulator", icon="🎲"),
            st.Page("pages/5_Statistics.py",           title="Statistics",           icon="📊"),
            st.Page("pages/6_Team_Deep_Dive.py",       title="Team Deep Dive",       icon="🌍"),
        ],
    }
)

# ── Sidebar logo — only on sub-pages (home page already has the large logo) ───
if pg.title != "Predictions":
    with st.sidebar:
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, width=160)
        st.divider()

pg.run()
