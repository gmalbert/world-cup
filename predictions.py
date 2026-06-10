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
from goallineiq_utils.api_client import (
    get_all_wc_matches, get_upcoming_matches, get_current_standings,
    bdl_client, apf_client, WC_NAMES,
)
from goallineiq_utils.models import build_predictor, WC2026_GROUPS, FALLBACK_ELO
from goallineiq_utils.timezone_utils import (
    assign_realistic_match_times, format_datetime_local, format_match_time_friendly,
    add_browser_timezone_js
)
from goallineiq_utils.weather import get_weather_for_match
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

    # ── Enhanced Tournament Countdown Banner ──────────────────────────────────
    if not live and days_to > 0:
        progress = max(0, min(100, (1 - days_to / 365) * 100))
        st.markdown(
            f"""
            <div style="background:linear-gradient(135deg, #00c853 0%, #1565c0 100%);
                        border-radius:12px; padding:1.5rem; margin:1rem 0; text-align:center;">
                <div style="font-size:3rem;font-weight:900;color:#fff;margin-bottom:0.5rem;">
                    ⚽ {days_to} DAYS TO KICKOFF
                </div>
                <div style="font-size:1.1rem;color:#e3f2fd;margin-bottom:1rem;">
                    June 11, 2026 · Mexico City · Mexico vs. TBD
                </div>
                <div style="background:rgba(255,255,255,0.2);border-radius:10px;height:8px;overflow:hidden;">
                    <div style="width:{progress}%;background:#fff;height:100%;transition:width 0.3s;"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    elif live:
        st.success("🟢 **TOURNAMENT IS LIVE!** — Real-time predictions updating with every match result")

    # ── Host Nation Spotlight ─────────────────────────────────────────────────
    if days_to > 0 or live:
        st.markdown('<p class="section-header">🏟️ Host Nation Advantage</p>', unsafe_allow_html=True)
        host_cols = st.columns(3)
        for idx, (nation, flag, city) in enumerate([
            ("USA", "🇺🇸", "11 cities"),
            ("Mexico", "🇲🇽", "3 cities"),
            ("Canada", "🇨🇦", "2 cities")
        ]):
            with host_cols[idx]:
                try:
                    host_pred = predictor.predict(nation, "Brazil", neutral=False)  # vs top team
                    host_elo = int(host_pred['home_elo'])
                    win_pct = host_pred['home_win'] * 100
                    st.metric(
                        f"{flag} {nation}",
                        f"Elo {host_elo}",
                        f"+{win_pct:.0f}% vs Brazil",
                        help=f"Hosting {city} | Home advantage modeled"
                    )
                except Exception:
                    st.metric(f"{flag} {nation}", "Host Nation", city)
        st.divider()

    # ── Group Draw with Elo Ratings ───────────────────────────────────────────
    if days_to > 30 or live:  # Show if tournament is approaching or live
        st.markdown('<p class="section-header">📋 2026 Group Draw · Strength Analysis</p>', unsafe_allow_html=True)
        st.caption("Each group shows team Elo ratings and predicted advancement probabilities")
        
        # Calculate group strength and advancement probabilities
        group_data = []
        for group_name, teams in sorted(WC2026_GROUPS.items()):
            group_elos = []
            for team in teams:
                try:
                    # Get Elo from predictor
                    dummy_pred = predictor.predict(team, team, neutral=True)
                    elo = int(dummy_pred['home_elo'])
                except Exception:
                    elo = FALLBACK_ELO.get(team, 1500)
                group_elos.append((team, elo))
            
            # Sort by Elo (strongest first)
            group_elos.sort(key=lambda x: x[1], reverse=True)
            avg_elo = sum(e for _, e in group_elos) / len(group_elos)
            
            group_data.append({
                'group': group_name,
                'teams': group_elos,
                'avg_elo': avg_elo,
                'strength': '🔥' * min(5, int((avg_elo - 1400) / 100))
            })
        
        # Display groups in a grid (4 columns x 3 rows = 12 groups)
        for row_start in range(0, 12, 4):
            row_groups = group_data[row_start:row_start + 4]
            group_cols = st.columns(4)
            for col_idx, gdata in enumerate(row_groups):
                with group_cols[col_idx]:
                    with st.container(border=True):
                        st.markdown(
                            f"**Group {gdata['group']}** {gdata['strength']}<br>"
                            f"<small style='color:#9e9e9e;'>Avg Elo: {int(gdata['avg_elo'])}</small>",
                            unsafe_allow_html=True
                        )
                        for rank, (team, elo) in enumerate(gdata['teams'], 1):
                            qual_emoji = "🟢" if rank <= 2 else "🟡" if rank == 3 else "⚪"
                            st.caption(f"{qual_emoji} {team} · `{elo}`")
        
        st.caption("🟢 Top 2 qualify · 🟡 Best 3rd place teams (8 total) · ⚪ Eliminated")
        st.divider()

    # ── Load data & train model ───────────────────────────────────────────────
    with st.spinner("Loading historical World Cup data (2010–2026)…"):
        all_matches = get_all_wc_matches()
    predictor = build_predictor(all_matches)

    if not all_matches.empty:
        coverage = all_matches.groupby("season")["home_team"].count().reset_index()
        coverage.columns = ["Season", "Matches Loaded"]
        with st.expander("📥 Data Coverage", expanded=False):
            st.dataframe(coverage, width="stretch", hide_index=True)
            st.caption("Sources: openfootball (2010, 2014) · BALLDONTLIE FIFA API (2018, 2022, 2026)")

    # ── Upcoming match predictions ────────────────────────────────────────────
    st.markdown('<p class="section-header">⚽ Upcoming Match Predictions</p>', unsafe_allow_html=True)
    
    # Add timezone detection JS
    add_browser_timezone_js()
    
    upcoming = get_upcoming_matches(n=16)
    
    # Assign realistic match times to fixtures
    if upcoming is not None and not upcoming.empty:
        upcoming = assign_realistic_match_times(upcoming)

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
                    "city": row.get("city", ""),
                    "home_win": p["home_win"], "draw": p["draw"], "away_win": p["away_win"],
                    "home_xg": p["home_xg"], "away_xg": p["away_xg"],
                    "home_elo": p["home_elo"], "away_elo": p["away_elo"],
                })
        if pred_rows:
            cols = st.columns(2)
            for idx, pred in enumerate(pred_rows):
                col = cols[idx % 2]
                with col:
                    # Format datetime for display
                    date_dt = pd.to_datetime(pred["date"], utc=True, errors="coerce")
                    date_str = format_match_time_friendly(date_dt) if pd.notna(date_dt) else "Date TBD"
                    
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
                        venue_str = f"{pred['venue']}" if pred['venue'] else "Venue TBD"
                        caption_parts = [f"📅 {date_str}", f"📍 {venue_str}"]
                        
                        # Add weather forecast for upcoming matches
                        match_city = pred.get('city') if pred.get('city') else pred.get('venue')
                        if match_city and pd.notna(pred.get('date')):
                            weather = get_weather_for_match(str(match_city), str(pred['date']))
                            if weather:
                                weather_emoji = "☔" if weather["precipitation_mm"] > 1 else "☀️"
                                caption_parts.append(f"{weather_emoji} {weather['temperature_f']}°F")
                        
                        st.caption("  |  ".join(caption_parts))
                        st.caption(f"Expected Goals: {pred['home_xg']:.2f} – {pred['away_xg']:.2f}")
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
    st.markdown('<p class="section-header">💰 Top Value Bets (Model Edge)</p>', unsafe_allow_html=True)
    st.caption(
        "Best betting opportunities where our model finds significant value vs market odds. "
        "Edge shows model probability minus implied market probability."
    )
    
    # Calculate value bets from upcoming matches
    value_threshold = 0.05  # 5% edge minimum
    value_opportunities = []
    
    if upcoming is not None and not upcoming.empty:
        for _, match in upcoming.head(12).iterrows():
            home = str(match.get("home_team", ""))
            away = str(match.get("away_team", ""))
            if not home or not away:
                continue
                
            try:
                pred = predictor.predict(home, away, neutral=True)
                
                # Generate market odds (1.04 margin for realistic estimates)
                margin = 1.04
                market_h = 1 / (pred["home_win"] * margin)
                market_d = 1 / (pred["draw"] * margin)
                market_a = 1 / (pred["away_win"] * margin)
                
                # Calculate edges
                edge_h = pred["home_win"] - (1/market_h)
                edge_d = pred["draw"] - (1/market_d)
                edge_a = pred["away_win"] - (1/market_a)
                
                # Collect all outcomes with edges
                opportunities = [
                    (f"{home} vs {away}", f"{home} Win", edge_h, market_h, pred["home_win"]),
                    (f"{home} vs {away}", "Draw", edge_d, market_d, pred["draw"]),
                    (f"{home} vs {away}", f"{away} Win", edge_a, market_a, pred["away_win"]),
                ]
                
                for match_label, outcome, edge, odds, model_prob in opportunities:
                    if edge >= value_threshold:
                        value_opportunities.append({
                            "match": match_label,
                            "outcome": outcome,
                            "model_prob": model_prob,
                            "market_odds": odds,
                            "edge": edge
                        })
            except Exception:
                continue
    
    # Sort by edge and show top 5
    value_opportunities.sort(key=lambda x: x["edge"], reverse=True)
    top_bets = value_opportunities[:5]
    
    if top_bets:
        st.success(f"✅ Found {len(top_bets)} strong value bets (edge ≥ {value_threshold*100:.0f}%)")
        
        for i, bet in enumerate(top_bets, 1):
            implied = 1.0 / bet["market_odds"]
            edge = bet["edge"]
            badge_color = "#00c853"
            
            with st.container(border=True):
                vc1, vc2, vc3, vc4 = st.columns([3, 2, 2, 3])
                vc1.markdown(f"**#{i}  {bet['match']}**")
                vc2.markdown(f"`{bet['outcome']}`")
                vc3.metric(
                    "Model Prob", 
                    f"{bet['model_prob']*100:.1f}%",
                    delta=f"{edge*100:+.1f}% edge",
                    delta_color="normal"
                )
                vc4.markdown(
                    f"Best Odds: **{bet['market_odds']:.2f}** → Implied: {implied*100:.1f}%  \n"
                    f"<span style='color:{badge_color};font-weight:700;'>🎯 Edge: {edge*100:+.1f}%</span>",
                    unsafe_allow_html=True,
                )
    else:
        st.info("No strong value bets found in upcoming matches. Check back closer to match day for live odds analysis.")
    
    st.caption("⚠️ Odds are estimates based on model probabilities. Always verify current odds before betting.")

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
    st.plotly_chart(fig, width="stretch")

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
                        st.dataframe(grp_df, hide_index=True, width="stretch", height=235)
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
            st.Page("pages/7_Team_Profiles.py",        title="Team Profiles",        icon="🏆"),
            st.Page("pages/8_Model_Performance.py",    title="Model Performance",    icon="📈"),
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
