"""
Team Deep Dive — Nation profile, historical WC record, current squad,
playing style radar, and head-to-head record vs. any opponent.
"""
import os
import sys
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


st.markdown(f"""
<style>
    .section-header {{font-size:1.2rem;font-weight:700;color:#00c853;
        border-bottom:1px solid #2c2f4a;padding-bottom:0.4rem;margin-bottom:1rem;}}
    .team-card {{background:{'#dce8f0' if _is_day else '#1a1c2e'};border-radius:12px;padding:1.2rem 1.5rem;
        border:1px solid {'#90caf9' if _is_day else '#2c2f4a'};margin-bottom:1rem;}}
    .elo-big {{font-size:2.4rem;font-weight:800;color:#00c853;}}
    div[data-testid="stMetricValue"] {{color:#00c853;}}
</style>
""", unsafe_allow_html=True)

from utils.api_client import get_all_wc_matches, bdl_client, apf_client
from utils.models import build_predictor, WC2026_GROUPS, FALLBACK_ELO

# ── Load ──────────────────────────────────────────────────────────────────────
all_matches = get_all_wc_matches()
predictor   = build_predictor(all_matches)

# ── Team list ─────────────────────────────────────────────────────────────────
wc26_teams = sorted(set(t for teams in WC2026_GROUPS.values() for t in teams))
if all_matches is not None and not all_matches.empty:
    hist_teams = sorted(set(
        all_matches["home_team"].dropna().tolist()
        + all_matches["away_team"].dropna().tolist()
    ))
    all_teams = sorted(set(wc26_teams + hist_teams))
else:
    all_teams = wc26_teams

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Select Team")
    selected_team = st.selectbox(
        "Country",
        all_teams,
        index=all_teams.index("France") if "France" in all_teams else 0,
    )
    st.divider()
    compare_team = st.selectbox(
        "Compare vs (H2H)",
        [t for t in all_teams if t != selected_team],
        index=0,
    )

st.title(f"🌍 {selected_team} — Team Profile")
st.divider()


# ══════════════════════════════════════════════════════════════════════════════
# TEAM OVERVIEW CARD
# ══════════════════════════════════════════════════════════════════════════════
elo = predictor.elo.get(selected_team)
ratings_df = predictor.get_ratings_df()
rank_row = ratings_df[ratings_df["team"] == selected_team]
elo_rank = int(rank_row.iloc[0]["rank"]) if not rank_row.empty else "N/A"

# Find group
team_group = "—"
for g, teams in WC2026_GROUPS.items():
    if selected_team in teams:
        team_group = g
        break

col_info, col_elo = st.columns([3, 2])
with col_info:
    with st.container(border=True):
        st.markdown(f"**{selected_team}**")
        mi1, mi2, mi3 = st.columns(3)
        mi1.metric("2026 Group", team_group)
        mi2.metric("Elo Rank", f"#{elo_rank}")
        mi3.metric("Elo Rating", int(elo))

with col_elo:
    # Mini gauge
    fig_g = go.Figure(go.Indicator(
        mode="gauge+number",
        value=elo,
        title={"text": "Elo Rating", "font": {"color": "#546e7a" if _is_day else "#9e9e9e", "size": 13}},
        number={"font": {"size": 36, "color": "#00c853"}},
        gauge={
            "axis": {"range": [1500, 2200], "tickcolor": "#546e7a" if _is_day else "#9e9e9e"},
            "bar": {"color": "#00c853"},
            "bgcolor": _BG,
            "bordercolor": "#90caf9" if _is_day else "#2c2f4a",
            "steps": [
                {"range": [1500, 1700], "color": "#bbdefb" if _is_day else "#0d1117"},
                {"range": [1700, 1900], "color": "#e3f2fd" if _is_day else "#111827"},
                {"range": [1900, 2200], "color": "#bbdefb" if _is_day else "#0d1117"},
            ],
        },
    ))
    fig_g.update_layout(
        height=220, paper_bgcolor=_BG, font_color=_FC,
        margin=dict(l=20, r=20, t=30, b=0),
    )
    st.plotly_chart(fig_g, width="stretch")


# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
t1, t2, t3, t4 = st.tabs([
    "📜 WC History", "⚽ Current Form", "📡 Playing Style", "🆚 H2H Record"
])


# ── Tab 1: WC History ─────────────────────────────────────────────────────────
with t1:
    st.markdown(f'<p class="section-header">{selected_team} — World Cup History (2010–2026)</p>', unsafe_allow_html=True)

    if all_matches is None or all_matches.empty:
        st.info("Historical data not available.")
    else:
        team_matches = all_matches[
            ((all_matches["home_team"] == selected_team) | (all_matches["away_team"] == selected_team))
            & all_matches["home_goals"].notna()
        ].copy()

        if team_matches.empty:
            st.info(f"No World Cup match history found for {selected_team} in the loaded dataset.")
        else:
            # Per-tournament summary
            def summarise_wc(df, team):
                rows = []
                for season, gdf in df.groupby("season"):
                    wins = draws = losses = gf = ga = 0
                    for _, row in gdf.iterrows():
                        if row["home_team"] == team:
                            g, c = int(row["home_goals"]), int(row["away_goals"])
                        else:
                            g, c = int(row["away_goals"]), int(row["home_goals"])
                        gf += g; ga += c
                        if g > c: wins += 1
                        elif g == c: draws += 1
                        else: losses += 1
                    rows.append({
                        "Season": season, "P": wins+draws+losses,
                        "W": wins, "D": draws, "L": losses,
                        "GF": gf, "GA": ga, "GD": gf-ga,
                        "Points": wins*3+draws,
                    })
                return pd.DataFrame(rows).sort_values("Season")

            summary = summarise_wc(team_matches, selected_team)

            # Totals
            tot = summary.sum()
            mc1, mc2, mc3, mc4, mc5 = st.columns(5)
            mc1.metric("Tournaments", len(summary))
            mc2.metric("Total Wins", int(tot["W"]))
            mc3.metric("Total Draws", int(tot["D"]))
            mc4.metric("Goals For", int(tot["GF"]))
            mc5.metric("Goals Against", int(tot["GA"]))

            st.dataframe(summary, width="stretch", hide_index=True)

            # Win trend chart
            if len(summary) > 1:
                fig_wt = px.line(
                    summary, x="Season", y="W",
                    markers=True,
                    title=f"{selected_team} — Wins per World Cup",
                    labels={"W": "Wins", "Season": "Year"},
                    height=260,
                )
                fig_wt.update_traces(line_color="#00c853", marker_size=8)
                fig_wt.update_layout(
                    paper_bgcolor=_BG, plot_bgcolor=_BG,
                    font_color=_FC, margin=dict(l=10, r=10, t=40, b=10),
                )
                st.plotly_chart(fig_wt, width="stretch")

            # Match log
            st.divider()
            st.markdown("**All Matches**")
            match_log = team_matches.copy()
            match_log["date"] = pd.to_datetime(match_log["date"], errors="coerce", utc=True)
            match_log["Date"] = match_log["date"].dt.strftime("%Y-%m-%d")

            def result_label(row):
                if row["home_team"] == selected_team:
                    gf, ga = row["home_goals"], row["away_goals"]
                else:
                    gf, ga = row["away_goals"], row["home_goals"]
                return "W" if gf > ga else ("D" if gf == ga else "L")

            match_log["Result"] = match_log.apply(result_label, axis=1)
            match_log["Score"] = match_log["home_goals"].astype(int).astype(str) + "–" + match_log["away_goals"].astype(int).astype(str)
            disp_log = match_log[["Date", "season", "round", "home_team", "Score", "away_team", "Result"]].copy()
            disp_log.columns = ["Date", "Season", "Round", "Home", "Score", "Away", "Result"]

            def color_result(val):
                if val == "W": return "background-color:#1b5e20;color:white;"
                if val == "D": return "background-color:#f57f17;color:white;"
                return "background-color:#b71c1c;color:white;"

            styled_log = disp_log.style.map(color_result, subset=["Result"])
            st.dataframe(styled_log, width="stretch", hide_index=True)


# ── Tab 2: Current Form ───────────────────────────────────────────────────────
with t2:
    st.markdown(f'<p class="section-header">{selected_team} — 2026 World Cup Form</p>', unsafe_allow_html=True)

    # 2026 matches only
    if all_matches is not None and not all_matches.empty:
        team_2026 = all_matches[
            ((all_matches["home_team"] == selected_team) | (all_matches["away_team"] == selected_team))
            & (all_matches["season"] == 2026)
        ]
        if not team_2026.empty:
            completed_2026 = team_2026.dropna(subset=["home_goals", "away_goals"])
            if not completed_2026.empty:
                st.markdown("**Completed matches in 2026:**")
                st.dataframe(completed_2026[["date", "round", "home_team",
                                             "home_goals", "away_goals", "away_team"]].head(10),
                             width="stretch", hide_index=True)
            else:
                st.info(f"No completed 2026 World Cup matches yet for {selected_team} — tournament begins June 11.")
        else:
            st.info("2026 fixture data not yet loaded from API.")

    # Squad info from BALLDONTLIE
    st.divider()
    st.markdown('<p class="section-header">Squad (from BALLDONTLIE API)</p>', unsafe_allow_html=True)
    players_df = bdl_client.get_players(2026)
    if players_df is not None and not players_df.empty:
        team_players = players_df[players_df["team"].str.lower() == selected_team.lower()]
        if not team_players.empty:
            st.dataframe(
                team_players[["name", "position", "jersey_number"]].sort_values("position"),
                width="stretch", hide_index=True,
            )
        else:
            st.info(f"No squad data found for {selected_team} in the BALLDONTLIE 2026 dataset.")
    else:
        st.info("Squad data will appear here when the BALLDONTLIE API is available.")


# ── Tab 3: Playing Style Radar ────────────────────────────────────────────────
with t3:
    st.markdown(f'<p class="section-header">{selected_team} — Playing Style Profile</p>', unsafe_allow_html=True)
    st.caption(
        "Radar chart is computed from Elo rating and historical WC performance metrics. "
        "Trait scores are normalised relative to all 2026 WC participants."
    )

    # Compute style scores from available data
    elo_val = predictor.elo.get(selected_team)
    elo_all = [predictor.elo.get(t) for t in wc26_teams]
    elo_min, elo_max = min(elo_all), max(elo_all)

    def normalise(v, vmin, vmax, scale=10):
        if vmax == vmin:
            return 5.0
        return round((v - vmin) / (vmax - vmin) * scale, 1)

    attack_score = normalise(elo_val, elo_min, elo_max, 10)

    # Derive from historical match data
    def get_team_metric(team, metric="goals_scored", season=None):
        if all_matches is None or all_matches.empty:
            return 0
        df = all_matches.copy()
        if season:
            df = df[df["season"] == season]
        df = df.dropna(subset=["home_goals", "away_goals"])
        home = df[df["home_team"] == team]
        away = df[df["away_team"] == team]
        if metric == "goals_scored":
            return home["home_goals"].sum() + away["away_goals"].sum()
        elif metric == "goals_conceded":
            return home["away_goals"].sum() + away["home_goals"].sum()
        elif metric == "matches":
            return len(home) + len(away)
        return 0

    total_m  = get_team_metric(selected_team, "matches") or 1
    avg_gf   = get_team_metric(selected_team, "goals_scored") / total_m
    avg_ga   = get_team_metric(selected_team, "goals_conceded") / total_m

    # Calculate for all teams to normalise
    all_avg_gf = []
    all_avg_ga = []
    for t in wc26_teams:
        m = get_team_metric(t, "matches") or 1
        all_avg_gf.append(get_team_metric(t, "goals_scored") / m)
        all_avg_ga.append(get_team_metric(t, "goals_conceded") / m)

    gf_min, gf_max = min(all_avg_gf) if all_avg_gf else 0, max(all_avg_gf) if all_avg_gf else 1
    ga_min, ga_max = min(all_avg_ga) if all_avg_ga else 0, max(all_avg_ga) if all_avg_ga else 1

    # Lower conceded = better defensive score
    def_score = normalise(ga_max - avg_ga, 0, ga_max - ga_min, 10) if ga_max > ga_min else 5
    off_score  = normalise(avg_gf, gf_min, gf_max, 10) if gf_max > gf_min else attack_score

    categories = ["Attacking", "Defensive", "Elo Strength", "Tournament Experience", "Consistency"]
    experience_val = min(total_m / 3, 10)  # 3 matches per tournament, cap at 10
    consistency_val = normalise(
        get_team_metric(selected_team, "goals_scored") / max(total_m, 1),
        0, 3, 10
    )

    values = [off_score, def_score, attack_score, experience_val, consistency_val]

    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill="toself",
        fillcolor="rgba(0, 200, 83, 0.2)",
        line=dict(color="#00c853", width=2),
        name=selected_team,
    ))
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 10], color="#546e7a" if _is_day else "#9e9e9e"),
            angularaxis=dict(color="#546e7a" if _is_day else "#9e9e9e"),
            bgcolor=_BG,
        ),
        paper_bgcolor=_BG, font_color=_FC,
        showlegend=False, height=400,
        margin=dict(l=40, r=40, t=40, b=40),
        title=f"{selected_team} — Playing Style Radar",
    )
    st.plotly_chart(fig_radar, width="stretch")

    st.caption(
        "**Trait definitions:**  \n"
        "- **Attacking** — Avg goals scored per WC match (normalised)  \n"
        "- **Defensive** — Avg goals conceded per WC match (inverted, normalised)  \n"
        "- **Elo Strength** — Current Elo rating relative to all 2026 WC participants  \n"
        "- **Tournament Experience** — Total WC matches played (capped)  \n"
        "- **Consistency** — Historical goal scoring rate  \n"
    )


# ── Tab 4: Head-to-Head ───────────────────────────────────────────────────────
with t4:
    st.markdown(f'<p class="section-header">{selected_team} vs {compare_team} — All-Time H2H</p>', unsafe_allow_html=True)

    if all_matches is not None and not all_matches.empty:
        h2h_mask = (
            (
                (all_matches["home_team"] == selected_team) & (all_matches["away_team"] == compare_team)
            ) | (
                (all_matches["home_team"] == compare_team) & (all_matches["away_team"] == selected_team)
            )
        ) & all_matches["home_goals"].notna()
        h2h = all_matches[h2h_mask].copy()

        if h2h.empty:
            st.info(
                f"No World Cup meetings between {selected_team} and {compare_team} "
                "in the loaded dataset (2010–2026)."
            )
        else:
            total = len(h2h)
            team_wins = sum(
                ((h2h["home_team"] == selected_team) & (h2h["home_goals"] > h2h["away_goals"]))
                | ((h2h["away_team"] == selected_team) & (h2h["away_goals"] > h2h["home_goals"]))
            )
            draws = sum(h2h["home_goals"] == h2h["away_goals"])
            opp_wins = total - team_wins - draws

            hc1, hc2, hc3 = st.columns(3)
            hc1.metric(f"{selected_team} Wins", team_wins)
            hc2.metric("Draws", draws)
            hc3.metric(f"{compare_team} Wins", opp_wins)

            # Pie chart
            fig_pie = go.Figure(go.Pie(
                labels=[f"{selected_team} Win", "Draw", f"{compare_team} Win"],
                values=[team_wins, draws, opp_wins],
                hole=0.5,
                marker_colors=["#00c853", "#ffd600", "#2196f3"],
            ))
            fig_pie.update_layout(
                paper_bgcolor=_BG, font_color=_FC,
                height=280, margin=dict(l=20, r=20, t=20, b=20),
                showlegend=True,
            )
            st.plotly_chart(fig_pie, width="stretch")

            h2h["date"] = pd.to_datetime(h2h["date"], errors="coerce", utc=True)
            h2h["Date"] = h2h["date"].dt.strftime("%Y-%m-%d")
            h2h["Score"] = h2h["home_goals"].astype(int).astype(str) + "–" + h2h["away_goals"].astype(int).astype(str)
            st.dataframe(
                h2h[["Date", "season", "home_team", "Score", "away_team", "venue"]].rename(
                    columns={"season": "Season", "home_team": "Home", "away_team": "Away", "venue": "Venue"}
                ),
                width="stretch", hide_index=True,
            )
    else:
        # Model-only prediction
        pred = predictor.predict(selected_team, compare_team)
        st.info(f"Historical data not loaded. Model prediction: "
                f"{selected_team} {pred['home_win']*100:.1f}% | "
                f"Draw {pred['draw']*100:.1f}% | "
                f"{compare_team} {pred['away_win']*100:.1f}%")

    st.divider()
    # Model head-to-head prediction
    st.markdown(f'<p class="section-header">Model Prediction: {selected_team} vs {compare_team}</p>', unsafe_allow_html=True)
    pred_h2h = predictor.predict(selected_team, compare_team)
    pc1, pc2, pc3 = st.columns(3)
    pc1.metric(f"{selected_team} Win", f"{pred_h2h['home_win']*100:.1f}%")
    pc2.metric("Draw", f"{pred_h2h['draw']*100:.1f}%")
    pc3.metric(f"{compare_team} Win", f"{pred_h2h['away_win']*100:.1f}%")
    st.caption(
        f"xG: {pred_h2h['home_xg']:.2f} – {pred_h2h['away_xg']:.2f}  ·  "
        f"Elo: {int(pred_h2h['home_elo'])} vs {int(pred_h2h['away_elo'])}"
    )

add_betting_oracle_footer()
