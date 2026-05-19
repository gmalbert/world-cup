"""
Pre-Match Analysis — Per-match deep dive with model probabilities,
H2H history, form guide, xG analysis, and predicted lineup.
"""
import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv()
from footer import add_betting_oracle_footer

_is_day = st.session_state.get("_is_day", False)
_BG = "#e3f2fd" if _is_day else "#071528"
_FC = "#0d1b2a" if _is_day else "#e0f7fa"


st.markdown(f"""
<style>
    .section-header {{font-size:1.2rem;font-weight:700;color:#00c853;
        border-bottom:1px solid #2c2f4a;padding-bottom:0.4rem;margin-bottom:1rem;}}
    .prob-label {{font-size:2rem;font-weight:800;text-align:center;}}
    .team-title {{font-size:1.4rem;font-weight:800;}}
    .elo-tag {{background:{'#dce8f0' if _is_day else '#1a1c2e'};padding:3px 8px;border-radius:4px;font-size:0.8rem;color:{'#546e7a' if _is_day else '#9e9e9e'};}}
    .edge-pos {{color:#00c853;font-weight:700;}}
    .edge-neg {{color:#f44336;font-weight:700;}}
</style>
""", unsafe_allow_html=True)

from utils.api_client import get_all_wc_matches, get_upcoming_matches, apf_client
from utils.models import build_predictor, FALLBACK_ELO, WC2026_GROUPS

# ── Load data & model ─────────────────────────────────────────────────────────
all_matches = get_all_wc_matches()
predictor   = build_predictor(all_matches)

# ── All teams list (union of known 2026 teams + historical) ───────────────────
wc26_teams = sorted(set(t for teams in WC2026_GROUPS.values() for t in teams))
if all_matches is not None and not all_matches.empty:
    hist_teams = sorted(set(
        all_matches["home_team"].dropna().tolist()
        + all_matches["away_team"].dropna().tolist()
    ))
    all_teams_list = sorted(set(wc26_teams + hist_teams))
else:
    all_teams_list = wc26_teams

st.title("🔍 Pre-Match Analysis")
st.caption("Select any match to get model probabilities, H2H history, form, and xG analysis.")
st.divider()

# ── Match selector ────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Match Selector")

    upcoming = get_upcoming_matches(n=30)

    if upcoming is not None and not upcoming.empty:
        upcoming["label"] = upcoming.apply(
            lambda r: f"{r.get('home_team','?')} vs {r.get('away_team','?')}  ({str(r.get('date',''))[:10]})",
            axis=1,
        )
        match_options = ["— Custom —"] + upcoming["label"].tolist()
        selected_label = st.selectbox("Upcoming fixture", match_options)

        if selected_label != "— Custom —":
            sel_row = upcoming[upcoming["label"] == selected_label].iloc[0]
            default_home = str(sel_row["home_team"])
            default_away = str(sel_row["away_team"])
            fixture_id   = sel_row.get("id")
        else:
            default_home, default_away = "France", "Spain"
            fixture_id = None
    else:
        default_home, default_away = "France", "Spain"
        fixture_id = None

    st.divider()
    home_team = st.selectbox(
        "Home / Team A",
        all_teams_list,
        index=all_teams_list.index(default_home) if default_home in all_teams_list else 0,
    )
    away_team = st.selectbox(
        "Away / Team B",
        all_teams_list,
        index=all_teams_list.index(default_away) if default_away in all_teams_list else 1,
    )
    neutral = st.toggle("Neutral venue", value=True)

    st.divider()
    st.caption("📊 Model: Elo + Poisson Regression  \n🎲 10 000 MC simulations on Simulator page")

# ── Generate prediction ───────────────────────────────────────────────────────
pred = predictor.predict(home_team, away_team, neutral)
hw  = pred["home_win"]  * 100
dr  = pred["draw"]      * 100
aw  = pred["away_win"]  * 100

# ── Header ────────────────────────────────────────────────────────────────────
hc1, hc2, hc3 = st.columns([5, 2, 5])
with hc1:
    st.markdown(f'<p class="team-title">{home_team}</p>', unsafe_allow_html=True)
    st.markdown(f'<span class="elo-tag">Elo {int(pred["home_elo"])}</span>', unsafe_allow_html=True)
with hc2:
    st.markdown("<div style='text-align:center;padding-top:10px;font-size:1.5rem;color:#9e9e9e;'>VS</div>", unsafe_allow_html=True)
with hc3:
    st.markdown(f'<p class="team-title">{away_team}</p>', unsafe_allow_html=True)
    st.markdown(f'<span class="elo-tag">Elo {int(pred["away_elo"])}</span>', unsafe_allow_html=True)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
t1, t2, t3, t4 = st.tabs([
    "📊 Model Probabilities", "🔄 Head-to-Head", "📈 Form Guide", "⚽ xG & Scorelines"
])


# ── Tab 1: Model Probabilities ────────────────────────────────────────────────
with t1:
    st.markdown('<p class="section-header">Model Win Probabilities (Elo + Poisson)</p>', unsafe_allow_html=True)

    # Gauge charts
    def make_gauge(value: float, title: str, color: str) -> go.Figure:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=value,
            number={"suffix": "%", "font": {"size": 32, "color": _FC}},
            title={"text": title, "font": {"size": 14, "color": "#546e7a" if _is_day else "#9e9e9e"}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#546e7a" if _is_day else "#9e9e9e"},
                "bar": {"color": color},
                "bgcolor": _BG,
                "bordercolor": "#90caf9" if _is_day else "#2c2f4a",
                "steps": [
                    {"range": [0, 33], "color": "#bbdefb" if _is_day else "#0d1117"},
                    {"range": [33, 66], "color": "#e3f2fd" if _is_day else "#111827"},
                    {"range": [66, 100], "color": "#bbdefb" if _is_day else "#0d1117"},
                ],
                "threshold": {
                    "line": {"color": "white", "width": 2},
                    "thickness": 0.75,
                    "value": 50,
                },
            },
        ))
        fig.update_layout(
            height=220, margin=dict(l=20, r=20, t=30, b=0),
            paper_bgcolor=_BG, font_color=_FC,
        )
        return fig

    gc1, gc2, gc3 = st.columns(3)
    gc1.plotly_chart(make_gauge(hw, f"{home_team} Win", "#00c853"), width="stretch")
    gc2.plotly_chart(make_gauge(dr, "Draw", "#ffd600"),             width="stretch")
    gc3.plotly_chart(make_gauge(aw, f"{away_team} Win", "#2196f3"), width="stretch")

    # Stacked horizontal bar
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        name=f"{home_team} Win", x=[hw], y=[""],
        orientation="h", marker_color="#00c853",
        text=[f"{hw:.1f}%"], textposition="inside",
    ))
    fig_bar.add_trace(go.Bar(
        name="Draw", x=[dr], y=[""],
        orientation="h", marker_color="#ffd600",
        text=[f"{dr:.1f}%"], textposition="inside",
    ))
    fig_bar.add_trace(go.Bar(
        name=f"{away_team} Win", x=[aw], y=[""],
        orientation="h", marker_color="#2196f3",
        text=[f"{aw:.1f}%"], textposition="inside",
    ))
    fig_bar.update_layout(
        barmode="stack", height=100, showlegend=True,
        paper_bgcolor=_BG, plot_bgcolor=_BG, font_color=_FC,
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(range=[0, 100], showticklabels=False, showgrid=False),
        yaxis=dict(showticklabels=False),
    )
    st.plotly_chart(fig_bar, width="stretch")

    # xG Comparison
    st.markdown('<p class="section-header">Expected Goals (Model xG)</p>', unsafe_allow_html=True)
    xg_col1, xg_col2 = st.columns(2)
    xg_col1.metric(f"{home_team} xG", f"{pred['home_xg']:.2f}")
    xg_col2.metric(f"{away_team} xG", f"{pred['away_xg']:.2f}")

    # Market comparison (simulated odds for demo)
    st.divider()
    st.markdown('<p class="section-header">Model vs. Market (Illustrative)</p>', unsafe_allow_html=True)
    st.caption(
        "Bookmaker odds sourced from API-Football when available. "
        "Sample market odds shown below for demonstration — check the Odds Comparison page for live data."
    )

    # Calculate illustrative bookmaker odds from model probs + 5% overround
    overround = 1.05
    demo_odds_h = round(1 / (pred["home_win"] * overround), 2)
    demo_odds_d = round(1 / (pred["draw"]     * overround), 2)
    demo_odds_a = round(1 / (pred["away_win"] * overround), 2)

    # Check if fixture odds available
    real_odds = pd.DataFrame()
    API_FOOTBALL_KEY_SET = bool(os.getenv("API_FOOTBALL_KEY"))
    if fixture_id and API_FOOTBALL_KEY_SET:
        real_odds = apf_client.get_fixture_odds(int(fixture_id))

    if real_odds is not None and not real_odds.empty:
        odds_pivot = real_odds.pivot_table(
            index="bookmaker", columns="outcome", values="odd", aggfunc="first"
        ).reset_index()
        st.dataframe(odds_pivot, width="stretch", hide_index=True)
    else:
        compare_df = pd.DataFrame({
            "Source": ["GoallineIQ Model", "Market (illustrative)"],
            f"{home_team} Win": [f"{hw:.1f}%", f"{1/demo_odds_h*100:.1f}% ({demo_odds_h})"],
            "Draw":             [f"{dr:.1f}%", f"{1/demo_odds_d*100:.1f}% ({demo_odds_d})"],
            f"{away_team} Win": [f"{aw:.1f}%", f"{1/demo_odds_a*100:.1f}% ({demo_odds_a})"],
        })
        st.dataframe(compare_df, width="stretch", hide_index=True)
        st.caption("Live bookmaker odds visible on the Odds Comparison page when API data is available.")


# ── Tab 2: Head-to-Head ───────────────────────────────────────────────────────
with t2:
    st.markdown(f'<p class="section-header">Head-to-Head: {home_team} vs {away_team}</p>', unsafe_allow_html=True)

    h2h_data = pd.DataFrame()

    # First try from our historical WC matches
    if all_matches is not None and not all_matches.empty:
        mask = (
            (
                (all_matches["home_team"] == home_team) & (all_matches["away_team"] == away_team)
            ) | (
                (all_matches["home_team"] == away_team) & (all_matches["away_team"] == home_team)
            )
        ) & all_matches["home_goals"].notna()
        h2h_data = all_matches[mask].copy()

    if h2h_data.empty:
        st.info(f"No World Cup head-to-head history found between {home_team} and {away_team} in the loaded dataset.")
    else:
        h2h_data["date"] = pd.to_datetime(h2h_data["date"], errors="coerce", utc=True)
        h2h_data = h2h_data.sort_values("date", ascending=False)

        # Summary stats
        total = len(h2h_data)
        home_wins = sum(
            (h2h_data["home_team"] == home_team) & (h2h_data["home_goals"] > h2h_data["away_goals"])
            | (h2h_data["away_team"] == home_team) & (h2h_data["away_goals"] > h2h_data["home_goals"])
        )
        draws = sum(h2h_data["home_goals"] == h2h_data["away_goals"])
        away_wins = total - home_wins - draws

        s1, s2, s3 = st.columns(3)
        s1.metric(f"{home_team} Wins", home_wins)
        s2.metric("Draws", draws)
        s3.metric(f"{away_team} Wins", away_wins)

        st.divider()

        display = h2h_data[["season", "date", "round", "home_team", "home_goals",
                              "away_goals", "away_team", "venue"]].copy()
        display["date"] = display["date"].dt.strftime("%Y-%m-%d")
        display.columns = ["Season", "Date", "Round", "Home", "HG", "AG", "Away", "Venue"]
        st.dataframe(display, width="stretch", hide_index=True)


# ── Tab 3: Form Guide ─────────────────────────────────────────────────────────
with t3:
    st.markdown('<p class="section-header">Recent Form — Last 10 World Cup Matches</p>', unsafe_allow_html=True)
    st.caption("Form guide based on World Cup matches in the dataset (2010–2026). Not inclusive of qualifying or friendlies.")

    def get_team_form(team: str, n: int = 10) -> pd.DataFrame:
        if all_matches is None or all_matches.empty:
            return pd.DataFrame()
        mask = (
            (all_matches["home_team"] == team) | (all_matches["away_team"] == team)
        ) & all_matches["home_goals"].notna()
        df = all_matches[mask].copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
        df = df.sort_values("date", ascending=False).head(n)

        def result_for_team(row):
            if row["home_team"] == team:
                gf, ga = row["home_goals"], row["away_goals"]
                opp = row["away_team"]
            else:
                gf, ga = row["away_goals"], row["home_goals"]
                opp = row["home_team"]
            res = "W" if gf > ga else ("D" if gf == ga else "L")
            return pd.Series({"Opponent": opp, "GF": int(gf), "GA": int(ga), "Result": res,
                               "Season": row["season"],
                               "Date": row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else ""})

        form_df = df.apply(result_for_team, axis=1)
        return form_df

    form_col1, form_col2 = st.columns(2)
    with form_col1:
        st.markdown(f"**{home_team}**")
        home_form = get_team_form(home_team)
        if not home_form.empty:
            def color_result(val):
                if val == "W":
                    return "background-color:#1b5e20;color:white;"
                elif val == "D":
                    return "background-color:#f57f17;color:white;"
                else:
                    return "background-color:#b71c1c;color:white;"
            st.dataframe(
                home_form.style.map(color_result, subset=["Result"]),
                width="stretch", hide_index=True,
            )
            wins = (home_form["Result"] == "W").sum()
            draws = (home_form["Result"] == "D").sum()
            avg_gf = home_form["GF"].mean()
            avg_ga = home_form["GA"].mean()
            st.caption(f"W{wins} D{draws} L{len(home_form)-wins-draws}  ·  Avg {avg_gf:.1f}–{avg_ga:.1f}")
        else:
            st.info("No historical WC data found for this team.")

    with form_col2:
        st.markdown(f"**{away_team}**")
        away_form = get_team_form(away_team)
        if not away_form.empty:
            st.dataframe(
                away_form.style.map(color_result, subset=["Result"]),
                width="stretch", hide_index=True,
            )
            wins = (away_form["Result"] == "W").sum()
            draws = (away_form["Result"] == "D").sum()
            avg_gf = away_form["GF"].mean()
            avg_ga = away_form["GA"].mean()
            st.caption(f"W{wins} D{draws} L{len(away_form)-wins-draws}  ·  Avg {avg_gf:.1f}–{avg_ga:.1f}")
        else:
            st.info("No historical WC data found for this team.")


# ── Tab 4: xG & Scorelines ────────────────────────────────────────────────────
with t4:
    st.markdown('<p class="section-header">Expected Goals & Most Likely Scorelines</p>', unsafe_allow_html=True)

    # xG visual
    xg_fig = go.Figure()
    xg_fig.add_trace(go.Bar(
        name=home_team,
        x=[home_team],
        y=[pred["home_xg"]],
        marker_color="#00c853",
        text=[f"{pred['home_xg']:.2f}"],
        textposition="outside",
    ))
    xg_fig.add_trace(go.Bar(
        name=away_team,
        x=[away_team],
        y=[pred["away_xg"]],
        marker_color="#2196f3",
        text=[f"{pred['away_xg']:.2f}"],
        textposition="outside",
    ))
    xg_fig.update_layout(
        title="Model Expected Goals (xG)",
        height=280,
        paper_bgcolor=_BG, plot_bgcolor=_BG, font_color=_FC,
        margin=dict(l=10, r=10, t=40, b=10),
        showlegend=False,
        yaxis=dict(title="xG", range=[0, max(pred["home_xg"], pred["away_xg"]) * 1.4]),
    )
    st.plotly_chart(xg_fig, width="stretch")

    # Top scorelines
    st.markdown('<p class="section-header">Most Likely Scorelines</p>', unsafe_allow_html=True)
    scorelines = pred.get("top_scorelines", [])
    if scorelines:
        sl_df = pd.DataFrame(scorelines, columns=["Scoreline", "Probability"])
        sl_df["Probability %"] = (sl_df["Probability"] * 100).round(1).astype(str) + "%"
        sl_df[f"{home_team} Goals"] = sl_df["Scoreline"].apply(lambda x: x.split("-")[0])
        sl_df[f"{away_team} Goals"] = sl_df["Scoreline"].apply(lambda x: x.split("-")[1])
        sl_df = sl_df[[f"{home_team} Goals", f"{away_team} Goals", "Probability %"]]

        fig_sl = px.bar(
            pd.DataFrame(scorelines, columns=["Scoreline", "p"]),
            x="Scoreline", y="p",
            labels={"p": "Probability"},
            title="Scoreline Probability Distribution",
            color="p",
            color_continuous_scale=["#1a237e", "#00c853"],
            height=280,
        )
        fig_sl.update_layout(
            paper_bgcolor=_BG, plot_bgcolor=_BG,
            font_color=_FC, coloraxis_showscale=False,
            margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(fig_sl, width="stretch")
        st.dataframe(sl_df, width="stretch", hide_index=True)

    # BTTS / Over 2.5 derived from Poisson
    from scipy.stats import poisson as poisson_dist
    lh, la = pred["home_xg"], pred["away_xg"]
    p_over25 = 1 - sum(
        poisson_dist.pmf(h, lh) * poisson_dist.pmf(a, la)
        for h in range(4) for a in range(4) if h + a <= 2
    )
    p_btts = (1 - poisson_dist.pmf(0, lh)) * (1 - poisson_dist.pmf(0, la))

    st.divider()
    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Over 2.5 Goals", f"{p_over25*100:.1f}%")
    mc2.metric("Both Teams Score", f"{p_btts*100:.1f}%")
    mc3.metric("Under 2.5 Goals", f"{(1-p_over25)*100:.1f}%")

add_betting_oracle_footer()
