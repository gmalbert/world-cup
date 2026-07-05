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


# ── Auto-detect theme from browser-local time (day = 7am–7pm) ────────────────
try:
    from zoneinfo import ZoneInfo
    _browser_timezone = getattr(st.context, "timezone", None) or "UTC"
    _hour = datetime.now(ZoneInfo(_browser_timezone)).hour
except Exception:
    _hour = datetime.now(timezone.utc).hour
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
    bdl_client, apf_client, WC_NAMES, load_predictions_cache,
)
from goallineiq_utils.models import build_predictor, WC2026_GROUPS, FALLBACK_ELO
from goallineiq_utils.timezone_utils import (
    assign_realistic_match_times, format_datetime_local, format_match_time_friendly,
    add_browser_timezone_js, format_match_time_local, get_user_timezone,
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
        .hero-table {width:100%; border-collapse:collapse; table-layout:fixed; border:none !important;}
        .hero-table tr, .hero-table td {border:none !important; vertical-align:bottom; padding:0;}
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

    # ── Load data & train model ───────────────────────────────────────────────
    # Try pre-computed cache first (nightly GitHub Actions) to avoid live Elo training
    _predictions_cache = load_predictions_cache()
    _using_cache = _predictions_cache is not None

    with st.spinner("Loading historical World Cup data (2010–2026)…"):
        all_matches = get_all_wc_matches()
    predictor = build_predictor(all_matches)

    if not all_matches.empty:
        coverage = all_matches.groupby("season")["home_team"].count().reset_index()
        coverage.columns = ["Season", "Matches Loaded"]
        with st.expander("📥 Data Coverage & Model Reference", expanded=False):
            st.dataframe(coverage, width="stretch", hide_index=True)
            st.caption("Sources: openfootball (2010, 2014) · BALLDONTLIE FIFA API (2018, 2022, 2026)")
            st.divider()
            st.markdown("#### 📖 Elo & Model Data Dictionary")
            st.markdown("""
| Term | Description |
|---|---|
| **Elo Rating** | A numerical team strength score updated after every match. Higher = stronger. World-class teams sit around 1950–2100; average WC teams around 1800–1900. |
| **Elo Differential** | The gap between two teams' Elo ratings. Drives the win-probability calculation — a +200 Elo gap implies ~76 % win probability for the stronger side. |
| **K-Factor** | Controls how quickly Elo updates after a result. World Cup matches use K=60; qualifiers K=40; friendlies K=20. Larger K = bigger swings. |
| **Home Advantage** | +80 Elo points added to the home team when `neutral=False` (non-neutral venue). All tournament predictions use neutral site. |
| **xG (Expected Goals)** | Model-estimated goals for each side based on Elo differential and an average World Cup scoring rate of 1.32 goals/team/match. Scaled by average team Elo so elite matchups produce higher totals. |
| **home_win / draw / away_win** | Win/draw/loss probabilities derived from the Poisson score distribution. Always sum to 1. |
| **O/U 1.5 / 2.5 / 3.5** | Probability that the total goals in the match exceeds that line, computed from the joint Poisson distribution of home and away goals. |
| **Elo Factor** | Per-match scaling applied to xG: `1 + (avg_elo − 1850) / 1500`. Ranges ~0.75× (weakest) to ~1.40× (strongest elite clash). Ensures O/U varies realistically by matchup quality. |
| **Market Implied Probability** | `1 / decimal_odds`. A 1.91 line implies 52.4 %. Sum of all implied probs for a market > 1 = bookmaker overround. |
| **Edge** | `model_probability − market_implied_probability`. Positive edge = model thinks the outcome is more likely than the price implies. |
| **Overround (Vig)** | The bookmaker's built-in margin. Typical sportsbooks run 4–6 % on 1X2; O/U 2.5 lines usually offered at 1.91/1.91 (~4.7 % overround). |
| **Fair Odds** | `1 / model_probability` — what the decimal odds *would* be at zero margin. |
""")

    # ── Upcoming match predictions ────────────────────────────────────────────
    st.markdown('<p class="section-header">⚽ Upcoming Match Predictions</p>', unsafe_allow_html=True)

    # Render sidebar timezone selector (stores choice in session_state for format_match_time_local)
    get_user_timezone()

    upcoming = get_upcoming_matches(n=16)
    
    # Assign realistic match times to fixtures
    if upcoming is not None and not upcoming.empty:
        upcoming = assign_realistic_match_times(upcoming)

    if upcoming is not None and not upcoming.empty:
        # Use pre-computed cache when available; fall back to live prediction
        if _using_cache and _predictions_cache.get("match_predictions"):
            # Only reuse entries that still exist in the current fixture set.
            # Keeping the cache's first 16 rows made the page show yesterday's
            # teams after the knockout bracket advanced.
            _up_map = {}
            for _, _ur in upcoming.iterrows():
                _key = (str(_ur.get("home_team","")), str(_ur.get("away_team","")))
                _up_map[_key] = _ur
            pred_rows = []
            for _cached in _predictions_cache["match_predictions"]:
                pr = dict(_cached)
                _ur = _up_map.get((pr.get("home_team",""), pr.get("away_team","")))
                if _ur is not None:
                    pr["date"]  = _ur.get("date", pr.get("date"))
                    pr["venue"] = _ur.get("venue", pr.get("venue",""))
                    pr["city"]  = _ur.get("city",  pr.get("city",""))
                    pred_rows.append(pr)

            # Compute newly resolved fixtures immediately instead of waiting
            # for the next nightly cache build.
            cached_keys = {
                (pr.get("home_team", ""), pr.get("away_team", "")) for pr in pred_rows
            }
            missing = upcoming[
                ~upcoming.apply(
                    lambda row: (str(row.get("home_team", "")), str(row.get("away_team", ""))) in cached_keys,
                    axis=1,
                )
            ]
        else:
            pred_rows = []
            missing = upcoming

        if missing is not None and not missing.empty:
            for _, row in missing.iterrows():
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
                        "ou": p.get("ou", {}),
                    })
        pred_rows = pred_rows[:16]
        if pred_rows:
            _cache_age = ""
            if _using_cache:
                _gen = _predictions_cache.get("generated_at", "")
                _cache_age = f"  ·  Predictions cached {_gen[:10]}" if _gen else ""
            st.caption(f"Showing {len(pred_rows)} upcoming fixtures{_cache_age}")
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
                        # O/U row
                        ou    = pred.get("ou", {})
                        ou25  = ou.get(2.5, {})
                        if ou25:
                            over_p  = ou25["over"]  * 100
                            under_p = ou25["under"] * 100
                            MARKET_OU_IMP = 1.0 / 1.91
                            ou_edge  = ou25["over"]  - MARKET_OU_IMP
                            u_edge   = ou25["under"] - MARKET_OU_IMP
                            if ou_edge >= 0.04:
                                ou_sig = f"🟢 OVER +{ou_edge*100:.1f}%"
                            elif u_edge >= 0.04:
                                ou_sig = f"🔴 UNDER +{u_edge*100:.1f}%"
                            else:
                                ou_sig = "⚪ no edge"
                            st.caption(
                                f"xG: {pred['home_xg']:.2f} – {pred['away_xg']:.2f}  "
                                f"|  ⚽ O/U 2.5: Over {over_p:.0f}% / Under {under_p:.0f}%  {ou_sig}"
                            )
                        else:
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
                    ou25 = p.get("ou", {}).get(2.5, {})
                    if ou25:
                        ov = ou25["over"] * 100
                        un = ou25["under"] * 100
                        MARKET_OU_IMP = 1.0 / 1.91
                        ou_edge = ou25["over"] - MARKET_OU_IMP
                        u_edge  = ou25["under"] - MARKET_OU_IMP
                        if ou_edge >= 0.04:
                            ou_sig = f"🟢 OVER +{ou_edge*100:.1f}%"
                        elif u_edge >= 0.04:
                            ou_sig = f"🔴 UNDER +{u_edge*100:.1f}%"
                        else:
                            ou_sig = "⚪ no edge"
                        st.caption(
                            f"xG: {p['home_xg']:.2f} – {p['away_xg']:.2f}  "
                            f"|  ⚽ O/U 2.5: Over {ov:.0f}% / Under {un:.0f}%  {ou_sig}"
                        )
                    else:
                        st.caption(f"xG: {p['home_xg']:.2f} – {p['away_xg']:.2f}")

    # ── Today's Best Bets — top recommendations with confidence ─────────────
    st.divider()
    st.markdown('<p class="section-header">🏆 Today\'s Best Bets</p>', unsafe_allow_html=True)
    st.caption(
        "Model's top picks ranked by edge vs market benchmarks. "
        "1X2 edge vs 5 % margin proxy · O/U edge vs 1.91 line. "
        "Confidence = model win probability."
    )

    # Pull real odds from snapshot once (no extra API call)
    try:
        from goallineiq_utils.api_client import get_match_odds_from_snapshot as _get_odds
        _real_odds_available = True
    except Exception:
        _real_odds_available = False

    _best_bets_list: list[dict] = []
    _src_upcoming = upcoming if (upcoming is not None and not upcoming.empty) else None

    if _src_upcoming is not None:
        for _, _match in _src_upcoming.head(12).iterrows():
            _home = str(_match.get("home_team", ""))
            _away = str(_match.get("away_team", ""))
            if not _home or not _away:
                continue
            try:
                _pred = predictor.predict(_home, _away, neutral=True)
            except Exception:
                continue

            _hw_p, _dr_p, _aw_p = _pred["home_win"], _pred["draw"], _pred["away_win"]
            _ou25 = _pred.get("ou", {}).get(2.5, {"over": 0.5, "under": 0.5})
            _xg_total = round(_pred["home_xg"] + _pred["away_xg"], 2)

            # Try real snapshot odds first; fall back to 5% margin benchmark
            _mkt_h = _mkt_d = _mkt_a = _mkt_ou_over = _mkt_ou_under = None
            _odds_source = "proxy"
            if _real_odds_available:
                _snap = _get_odds(_home, _away)
                if _snap and _snap.get("best_h2h"):
                    _b = _snap["best_h2h"]
                    if _b.get("home"): _mkt_h = 1.0 / _b["home"]
                    if _b.get("draw"): _mkt_d = 1.0 / _b["draw"]
                    if _b.get("away"): _mkt_a = 1.0 / _b["away"]
                    _bou = _snap.get("best_ou", {})
                    if _bou.get("over"):  _mkt_ou_over  = 1.0 / _bou["over"]
                    if _bou.get("under"): _mkt_ou_under = 1.0 / _bou["under"]
                    if any([_mkt_h, _mkt_d, _mkt_a]):
                        _odds_source = "real"

            # Fall back to margin proxy
            if _mkt_h is None: _mkt_h = _hw_p / 1.05
            if _mkt_d is None: _mkt_d = _dr_p / 1.05
            if _mkt_a is None: _mkt_a = _aw_p / 1.05
            if _mkt_ou_over  is None: _mkt_ou_over  = 1.0 / 1.91
            if _mkt_ou_under is None: _mkt_ou_under = 1.0 / 1.91

            _THRESH = 0.04
            for _label, _prob, _mkt_imp, _bet_type in [
                (f"{_home} Win",  _hw_p,             _mkt_h,        "1X2"),
                ("Draw",          _dr_p,             _mkt_d,        "1X2"),
                (f"{_away} Win",  _aw_p,             _mkt_a,        "1X2"),
                ("Over 2.5",      _ou25["over"],     _mkt_ou_over,  "O/U"),
                ("Under 2.5",     _ou25["under"],    _mkt_ou_under, "O/U"),
            ]:
                _edge = _prob - _mkt_imp
                if _edge >= _THRESH:
                    _best_bets_list.append({
                        "match": f"{_home} vs {_away}",
                        "bet": _label,
                        "bet_type": _bet_type,
                        "prob": _prob,
                        "edge": _edge,
                        "xg_total": _xg_total if _bet_type == "O/U" else None,
                        "odds_source": _odds_source,
                        "home_elo": int(_pred["home_elo"]),
                        "away_elo": int(_pred["away_elo"]),
                    })

    _best_bets_list.sort(key=lambda x: x["edge"], reverse=True)
    _top_bets = _best_bets_list[:8]

    if _top_bets:
        st.success(f"✅ Found **{len(_top_bets)}** value bets for upcoming fixtures")
        _bbcols = st.columns(2)
        for _i, _bet in enumerate(_top_bets):
            _col = _bbcols[_i % 2]
            _prob_pct = _bet["prob"] * 100
            _edge_pct = _bet["edge"] * 100
            if _prob_pct >= 65:
                _conf_label, _conf_color = "HIGH", "#00c853"
            elif _prob_pct >= 50:
                _conf_label, _conf_color = "MEDIUM", "#ffd600"
            else:
                _conf_label, _conf_color = "SPECULATIVE", "#ff9800"

            _src_badge = "📡 Real odds" if _bet["odds_source"] == "real" else "📐 Model proxy"
            _xg_note = f"  xG {_bet['xg_total']}" if _bet["xg_total"] else ""

            with _col:
                with st.container(border=True):
                    st.markdown(
                        f"<div style='font-size:0.8rem;color:#9e9e9e;'>{_bet['match']}{_xg_note} · {_src_badge}</div>"
                        f"<div style='font-size:1.3rem;font-weight:800;margin:4px 0;'>BET: {_bet['bet']}</div>"
                        f"<div style='display:flex;gap:8px;align-items:center;'>"
                        f"<span style='background:{_conf_color};color:#000;padding:2px 8px;"
                        f"border-radius:4px;font-size:0.78rem;font-weight:700;'>{_conf_label}</span>"
                        f"<span style='font-size:0.9rem;'>Model: <strong>{_prob_pct:.1f}%</strong>"
                        f" · Edge: <strong style='color:{_conf_color};'>+{_edge_pct:.1f}%</strong></span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    # Confidence bar
                    st.markdown(
                        f"<div style='background:#1a1c2e;border-radius:4px;height:6px;margin:6px 0;overflow:hidden;'>"
                        f"<div style='width:{_prob_pct:.0f}%;background:{_conf_color};height:100%;'></div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    # Plain-English reasoning
                    _elo_gap = abs(_bet["home_elo"] - _bet["away_elo"])
                    if _bet["bet_type"] == "O/U":
                        _reason = (
                            f"xG total {_bet['xg_total']} {'above' if 'Over' in _bet['bet'] else 'below'} "
                            f"the 2.5 line. Model sees {'a high-scoring' if 'Over' in _bet['bet'] else 'a tight, low-scoring'} match."
                        )
                    elif "Draw" in _bet["bet"]:
                        _reason = f"Teams are closely matched (Elo gap {_elo_gap}). A draw is underpriced by the market."
                    else:
                        _favoured = "home" if "Win" in _bet["bet"] and _bet["home_elo"] > _bet["away_elo"] else "away"
                        _reason = f"Elo advantage of {_elo_gap} pts. Market undervalues the {'stronger' if _elo_gap > 100 else 'slightly favoured'} side."
                    st.caption(_reason)
    else:
        st.info("No clear value bets found for upcoming fixtures. Check back closer to match day with live odds active.")

    # ── Upset Watch ───────────────────────────────────────────────────────────
    st.divider()
    st.markdown('<p class="section-header">⚡ Upset Watch</p>', unsafe_allow_html=True)
    st.caption(
        "Upcoming matches where the Elo underdog has a meaningful win chance. "
        "Probabilities ≥ 25 % trigger an alert."
    )

    # Use current fixtures so kickoff times and newly resolved teams stay fresh;
    # the date-only cache is only an offline fallback.
    if (upcoming is None or upcoming.empty) and _using_cache and _predictions_cache.get("upset_watch"):
        _upset_raw = _predictions_cache["upset_watch"]
        _upset_rows = []
        for _ur2 in _upset_raw:
            _raw_date = _ur2.get("date", "TBD")
            _dt2 = pd.NaT
            try:
                _dt2 = pd.to_datetime(_raw_date, utc=True, errors="coerce")
                _date_str2 = format_match_time_local(_dt2) if pd.notna(_dt2) else _raw_date
            except Exception:
                _date_str2 = _raw_date
            _upset_rows.append({
                "_Sort Date": _dt2,
                "Date": _date_str2,
                "Match": _ur2["match"],
                "Favourite": _ur2["favourite"],
                "Underdog": _ur2["underdog"],
                "Elo Gap": _ur2["elo_gap"],
                "Upset %": f"{_ur2['upset_pct']:.1f}",
                "Underdog xG": f"{_ur2['underdog_xg']:.3f}",
            })
    elif upcoming is not None and not upcoming.empty:
        _upset_rows = []
        for _, _urow in upcoming.iterrows():
            _uh = str(_urow.get("home_team", ""))
            _ua = str(_urow.get("away_team", ""))
            if not _uh or not _ua:
                continue
            try:
                _up = predictor.predict(_uh, _ua, neutral=True)
                _elo_h, _elo_a = _up["home_elo"], _up["away_elo"]
                if _elo_h < _elo_a:
                    _underdog, _fav = _uh, _ua
                    _upset_p = _up["home_win"]
                    _gap = _elo_a - _elo_h
                else:
                    _underdog, _fav = _ua, _uh
                    _upset_p = _up["away_win"]
                    _gap = _elo_h - _elo_a
                _raw_dt = _urow.get("date")
                _date_str = "TBD"
                _dt = pd.NaT
                if _raw_dt is not None:
                    try:
                        _dt = pd.to_datetime(_raw_dt, utc=True, errors="coerce")
                        if pd.notna(_dt):
                            _date_str = format_match_time_local(_dt)
                    except Exception:
                        pass
                _upset_rows.append({
                    "_Sort Date": _dt if pd.notna(_dt) else pd.NaT,
                    "Date": _date_str,
                    "Match": f"{_uh} vs {_ua}",
                    "Favourite": _fav,
                    "Underdog": _underdog,
                    "Elo Gap": int(_gap),
                    "Upset %": f"{_upset_p * 100:.1f}",
                    "Underdog xG": f"{(_up['home_xg'] if _underdog == _uh else _up['away_xg']):.3f}",
                })
            except Exception:
                continue
    else:
        _upset_rows = []

    if _upset_rows:
            _upset_df = pd.DataFrame(_upset_rows).sort_values(
                "_Sort Date", ascending=False, na_position="last"
            )
            _display_upset_df = _upset_df.drop(columns=["_Sort Date"])

            def _upset_col(val):
                # val is now a string like "31.0" — compare numerically
                try:
                    f = float(val)
                    if f >= 30: return "color:#00c853;font-weight:700;"
                    if f >= 20: return "color:#ffd600;font-weight:700;"
                except Exception:
                    pass
                return ""

            _su = _display_upset_df.style
            _styled_u = _su.map(_upset_col, subset=["Upset %"]) \
                        if hasattr(_su, "map") \
                        else _su.applymap(_upset_col, subset=["Upset %"])
            st.dataframe(_styled_u, width="stretch", hide_index=True)

            _big = _upset_df[_upset_df["Upset %"].astype(float) >= 25]
            if not _big.empty:
                st.warning(
                    f"⚠️ {len(_big)} upset alert(s): "
                    + ", ".join(
                        f"**{r['Underdog']}** vs {r['Favourite']} ({float(r['Upset %']):.0f}%)"
                        for _, r in _big.iterrows()
                    )
                )
    else:
        st.info("Upcoming fixture data not yet available for upset analysis.")

    # ── Bet Assessment (O/U + 1X2 vs real market benchmarks) ─────────────────
    st.divider()
    st.markdown('<p class="section-header">💰 Bet Assessment — Model vs Market Lines</p>', unsafe_allow_html=True)
    st.caption(
        "**O/U 2.5:** model probability vs standard 1.91 line (52.4 % implied each side).  "
        "**1X2:** model fair odds vs a 5 % bookmaker margin proxy.  "
        "Edge ≥ 4 % flagged as value (✅).  "
        "For live sportsbook prices visit the **Odds Comparison** page."
    )

    BM_MARGIN_1X2  = 1.05
    MARKET_OU_LINE = 1.91
    MARKET_OU_IMP  = 1.0 / MARKET_OU_LINE
    VALUE_THRESHOLD = 0.04

    bet_rows: list[dict] = []
    src_df = upcoming if (upcoming is not None and not upcoming.empty) else None

    if src_df is not None:
        for _, match in src_df.head(12).iterrows():
            home = str(match.get("home_team", ""))
            away = str(match.get("away_team", ""))
            if not home or not away:
                continue
            try:
                pred = predictor.predict(home, away, neutral=True)
            except Exception:
                continue

            hw_p, dr_p, aw_p = pred["home_win"], pred["draw"], pred["away_win"]
            ou25 = pred.get("ou", {}).get(2.5, {"over": 0.5, "under": 0.5})

            # Fair decimal odds (zero margin)
            fair_h = round(1 / hw_p, 2) if hw_p > 0 else 0
            fair_d = round(1 / dr_p, 2) if dr_p > 0 else 0
            fair_a = round(1 / aw_p, 2) if aw_p > 0 else 0

            # Market-implied probs after BM_MARGIN_1X2 overround
            mkt_h = hw_p / BM_MARGIN_1X2
            mkt_d = dr_p / BM_MARGIN_1X2
            mkt_a = aw_p / BM_MARGIN_1X2
            mkt_h_odds = round(1 / mkt_h, 2)
            mkt_d_odds = round(1 / mkt_d, 2)
            mkt_a_odds = round(1 / mkt_a, 2)

            def _sig(edge_val: float) -> str:
                return f"✅ +{edge_val*100:.1f}%" if edge_val >= VALUE_THRESHOLD else "—"

            ou_over_edge  = ou25["over"]  - MARKET_OU_IMP
            ou_under_edge = ou25["under"] - MARKET_OU_IMP
            if ou_over_edge >= VALUE_THRESHOLD:
                ou_sig = f"✅ OVER +{ou_over_edge*100:.1f}%"
            elif ou_under_edge >= VALUE_THRESHOLD:
                ou_sig = f"✅ UNDER +{ou_under_edge*100:.1f}%"
            else:
                ou_sig = "—"

            bet_rows.append({
                "Match": f"{home} vs {away}",
                "xG": round(pred["home_xg"] + pred["away_xg"], 3),
                "Over 2.5": f"{ou25['over']*100:.1f}%",
                "Under 2.5": f"{ou25['under']*100:.1f}%",
                "O/U Edge": ou_sig,
                "Home Win": f"{hw_p*100:.1f}%",
                "H Fair": fair_h, "H Mkt": mkt_h_odds,
                "H Edge": _sig(hw_p - mkt_h),
                "Draw": f"{dr_p*100:.1f}%",
                "D Fair": fair_d, "D Mkt": mkt_d_odds,
                "D Edge": _sig(dr_p - mkt_d),
                "Away Win": f"{aw_p*100:.1f}%",
                "A Fair": fair_a, "A Mkt": mkt_a_odds,
                "A Edge": _sig(aw_p - mkt_a),
            })

    if bet_rows:
        bet_df = pd.DataFrame(bet_rows)
        tab_ou, tab_1x2 = st.tabs(["⚽ Over/Under 2.5", "🏆 1X2 Result"])

        def _green_if_value(val):
            if isinstance(val, str) and val.startswith("✅"):
                return "color:#00c853;font-weight:700;"
            return ""

        with tab_ou:
            st.caption(
                f"Benchmark: 1.91 / 1.91 (52.4 % implied each side).  "
                f"Edge ≥ {VALUE_THRESHOLD*100:.0f} % flagged ✅."
            )
            ou_cols = ["Match", "xG", "Over 2.5", "Under 2.5", "O/U Edge"]
            s = bet_df[ou_cols].style
            styled_ou = s.map(_green_if_value, subset=["O/U Edge"]) if hasattr(s, "map") \
                        else s.applymap(_green_if_value, subset=["O/U Edge"])
            st.dataframe(styled_ou, width="stretch", hide_index=True)
            ou_hits = [r for r in bet_rows if r["O/U Edge"] != "—"]
            if ou_hits:
                st.success(f"✅ {len(ou_hits)} O/U value bet(s) vs standard 1.91 line")
                for v in ou_hits[:6]:
                    st.markdown(
                        f"**{v['Match']}** · xG total {v['xG']} · "
                        f"Over {v['Over 2.5']} / Under {v['Under 2.5']} · {v['O/U Edge']}"
                    )
            else:
                st.info("No O/U value bets vs the 1.91 benchmark in this fixture window.")

        with tab_1x2:
            st.caption(
                f"Benchmark: model fair odds ÷ 1.05 overround (~5 % margin proxy).  "
                f"For live odds use **Odds Comparison**.  "
                f"Edge ≥ {VALUE_THRESHOLD*100:.0f} % flagged ✅."
            )
            x12_cols = [
                "Match",
                "Home Win", "H Fair", "H Mkt", "H Edge",
                "Draw",     "D Fair", "D Mkt", "D Edge",
                "Away Win", "A Fair", "A Mkt", "A Edge",
            ]
            s2 = bet_df[x12_cols].style
            styled_x12 = s2.map(_green_if_value, subset=["H Edge", "D Edge", "A Edge"]) \
                         if hasattr(s2, "map") \
                         else s2.applymap(_green_if_value, subset=["H Edge", "D Edge", "A Edge"])
            st.dataframe(styled_x12, width="stretch", hide_index=True)
    else:
        st.info("Bet assessment will appear once upcoming fixture data is loaded.")

    st.caption(
        "⚠️ Benchmarks are proxies, not live sportsbook prices.  "
        "O/U edge uses a fixed 1.91 line; 1X2 edge uses a 5 % overround model.  "
        "Always verify current odds before placing bets."
    )

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
