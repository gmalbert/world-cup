"""
Statistics Dashboard — Top scorers, team stats, xG analysis,
and historical World Cup comparison (2010–2026).
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


st.markdown("""
<style>
    .section-header {font-size:1.2rem;font-weight:700;color:#00c853;
        border-bottom:1px solid #2c2f4a;padding-bottom:0.4rem;margin-bottom:1rem;}
    .disclaimer {background:#1a1c2e;border-radius:8px;padding:0.8rem 1rem;
        border:1px solid #ff1744;font-size:0.78rem;color:#ef9a9a;margin-top:2rem;}
    div[data-testid="stMetricValue"] {color:#00c853;}
</style>
""", unsafe_allow_html=True)

from goallineiq_utils.api_client import (
    get_all_wc_matches, get_historical_top_scorers,
    bdl_client, apf_client,
)

# ── Load ──────────────────────────────────────────────────────────────────────
all_matches     = get_all_wc_matches()
top_scorers_raw = get_historical_top_scorers()

st.title("📊 Statistics Dashboard")
st.caption("Tournament stats, historical comparisons, xG analysis — 2010 to 2026")
st.divider()

tab_scoring, tab_team, tab_xg, tab_history = st.tabs([
    "🥅 Scoring", "📋 Team Stats", "📈 xG Analysis", "📜 Historical WC"
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — SCORING
# ══════════════════════════════════════════════════════════════════════════════
with tab_scoring:
    st.markdown('<p class="section-header">Top Scorers — 2026 World Cup</p>', unsafe_allow_html=True)

    season_sel = st.selectbox("Season", [2026, 2022, 2018], key="scorer_season")

    # Try BALLDONTLIE player stats
    player_stats = bdl_client.get_player_stats(season_sel)

    if player_stats is not None and not player_stats.empty and "goals" in player_stats.columns:
        top_goal = player_stats.nlargest(15, "goals")[
            ["player", "team", "goals", "assists", "shots", "xg", "minutes", "appearances"]
        ].copy()
        top_goal.columns = ["Player", "Team", "Goals", "Assists", "Shots", "xG", "Min", "Apps"]

        fig_g = px.bar(
            top_goal.head(10),
            x="Goals", y="Player", orientation="h",
            color="Goals",
            color_continuous_scale=["#1a237e", "#00c853"],
            text="Goals",
            title=f"Top Goal Scorers — {season_sel}",
            height=380,
        )
        fig_g.update_layout(
            paper_bgcolor=_BG, plot_bgcolor=_BG,
            font_color=_FC, coloraxis_showscale=False,
            yaxis={"categoryorder": "total ascending"},
            margin=dict(l=10, r=40, t=40, b=10),
        )
        fig_g.update_traces(texttemplate="%{text}", textposition="outside")
        st.plotly_chart(fig_g, width="stretch")
        st.dataframe(top_goal, width="stretch", hide_index=True)
    else:
        # Fall back to API-Football
        apf_scorers = apf_client.get_top_scorers(season_sel)
        if apf_scorers is not None and not apf_scorers.empty:
            top_goal = apf_scorers.nlargest(15, "goals")[
                ["name", "team", "goals", "assists", "shots_total", "shots_on", "minutes", "appearances"]
            ].copy()
            top_goal.columns = ["Player", "Team", "Goals", "Assists", "Shots", "SoT", "Min", "Apps"]

            fig_g = px.bar(
                top_goal.head(10),
                x="Goals", y="Player", orientation="h",
                color="Goals",
                color_continuous_scale=["#1a237e", "#00c853"],
                text="Goals",
                title=f"Top Goal Scorers — {season_sel} (API-Football)",
                height=380,
            )
            fig_g.update_layout(
                paper_bgcolor=_BG, plot_bgcolor=_BG,
                font_color=_FC, coloraxis_showscale=False,
                yaxis={"categoryorder": "total ascending"},
                margin=dict(l=10, r=40, t=40, b=10),
            )
            fig_g.update_traces(texttemplate="%{text}", textposition="outside")
            st.plotly_chart(fig_g, width="stretch")
            st.dataframe(top_goal, width="stretch", hide_index=True)
        else:
            # Derive from match data
            st.info(f"Live player stats not available for {season_sel}. Computing from match-level data…")
            if all_matches is not None and not all_matches.empty:
                season_df = all_matches[all_matches["season"] == season_sel]
                st.caption(
                    f"Showing team-level goals from {len(season_df)} matches loaded for {season_sel}."
                )
                team_goals = (
                    pd.concat([
                        season_df[["home_team", "home_goals"]].rename(columns={"home_team": "team", "home_goals": "goals"}),
                        season_df[["away_team", "away_goals"]].rename(columns={"away_team": "team", "away_goals": "goals"}),
                    ])
                    .dropna()
                    .groupby("team")["goals"]
                    .sum()
                    .reset_index()
                    .nlargest(15, "goals")
                )
                fig_tg = px.bar(
                    team_goals,
                    x="goals", y="team", orientation="h",
                    color="goals", color_continuous_scale=["#1a237e", "#00c853"],
                    text="goals",
                    title=f"Team Goals Scored — {season_sel}", height=400,
                )
                fig_tg.update_layout(
                    paper_bgcolor=_BG, plot_bgcolor=_BG,
                    font_color=_FC, coloraxis_showscale=False,
                    yaxis={"categoryorder": "total ascending"},
                    margin=dict(l=10, r=40, t=40, b=10),
                )
                fig_tg.update_traces(texttemplate="%{text:.0f}", textposition="outside")
                st.plotly_chart(fig_tg, width="stretch")
            else:
                st.warning("No match data available.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — TEAM STATS
# ══════════════════════════════════════════════════════════════════════════════
with tab_team:
    st.markdown('<p class="section-header">Team Statistics — 2026 World Cup</p>', unsafe_allow_html=True)

    season_t = st.selectbox("Season", [2026, 2022, 2018], key="team_stat_season")

    team_stats = bdl_client.get_team_stats(season_t)

    if team_stats is not None and not team_stats.empty:
        display_ts = team_stats.sort_values("goals_for", ascending=False)
        col_rename = {
            "team": "Team", "goals_for": "GF", "goals_against": "GA",
            "shots": "Shots", "shots_on_target": "SoT",
            "xg_for": "xG For", "xg_against": "xG Against",
            "possession": "Possession %", "pass_accuracy": "Pass Acc %",
            "appearances": "Matches",
        }
        display_ts = display_ts.rename(columns=col_rename)
        keep = [c for c in col_rename.values() if c in display_ts.columns]
        st.dataframe(display_ts[keep], width="stretch", hide_index=True)

        # Shots vs Goals chart
        if "Shots" in display_ts.columns and "GF" in display_ts.columns:
            fig_sg = px.scatter(
                display_ts,
                x="Shots", y="GF",
                hover_name="Team",
                color="GF",
                size="GF",
                color_continuous_scale=["#1a237e", "#00c853"],
                title=f"Shots vs Goals Scored — {season_t}",
                height=380,
            )
            fig_sg.update_layout(
                paper_bgcolor=_BG, plot_bgcolor=_BG,
                font_color=_FC, coloraxis_showscale=False,
                margin=dict(l=10, r=10, t=40, b=10),
            )
            st.plotly_chart(fig_sg, width="stretch")
    else:
        # Derive from match data
        st.info(f"Live team stats not available — computing from loaded match data for {season_t}.")
        if all_matches is not None and not all_matches.empty:
            sm = all_matches[all_matches["season"] == season_t].dropna(subset=["home_goals", "away_goals"])
            if not sm.empty:
                home_agg = sm.groupby("home_team").agg(
                    GF=("home_goals", "sum"), GA=("away_goals", "sum"), M=("home_team", "count")
                ).reset_index().rename(columns={"home_team": "team"})
                away_agg = sm.groupby("away_team").agg(
                    GF=("away_goals", "sum"), GA=("home_goals", "sum"), M=("away_team", "count")
                ).reset_index().rename(columns={"away_team": "team"})
                combined = pd.concat([home_agg, away_agg]).groupby("team").sum().reset_index()
                combined["GD"] = combined["GF"] - combined["GA"]
                combined = combined.sort_values("GF", ascending=False)
                st.dataframe(combined, width="stretch", hide_index=True)

                fig_td = px.bar(
                    combined.head(16),
                    x="team", y=["GF", "GA"],
                    barmode="group",
                    color_discrete_map={"GF": "#00c853", "GA": "#f44336"},
                    title=f"Goals For vs Against — {season_t}",
                    height=380,
                )
                fig_td.update_layout(
                    paper_bgcolor=_BG, plot_bgcolor=_BG,
                    font_color=_FC,
                    margin=dict(l=10, r=10, t=40, b=40),
                    xaxis=dict(tickangle=-45),
                )
                st.plotly_chart(fig_td, width="stretch")
            else:
                st.warning("No completed match data for this season.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — xG ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
with tab_xg:
    st.markdown('<p class="section-header">Expected Goals (xG) Analysis</p>', unsafe_allow_html=True)
    st.caption(
        "xG data available via BALLDONTLIE for 2022 and 2026 World Cups. "
        "Teams above the diagonal are 'underperforming' their xG; teams below are overperforming."
    )

    for season_xg in [2026, 2022]:
        team_stats_xg = bdl_client.get_team_stats(season_xg)
        if team_stats_xg is not None and not team_stats_xg.empty \
                and "xg_for" in team_stats_xg.columns \
                and team_stats_xg["xg_for"].notna().any():

            xg_df = team_stats_xg.dropna(subset=["xg_for", "goals_for"]).copy()
            xg_df["xg_for"] = pd.to_numeric(xg_df["xg_for"], errors="coerce")

            if not xg_df.empty:
                fig_xg = px.scatter(
                    xg_df,
                    x="xg_for", y="goals_for",
                    hover_name="team",
                    color="goals_for",
                    size=xg_df["xg_for"].abs(),
                    color_continuous_scale=["#1a237e", "#00c853"],
                    labels={"xg_for": "Expected Goals (xG)", "goals_for": "Actual Goals"},
                    title=f"xG vs Actual Goals — {season_xg}",
                    height=420,
                )
                # Diagonal reference line
                max_val = max(xg_df["xg_for"].max(), xg_df["goals_for"].max()) + 1
                fig_xg.add_trace(go.Scatter(
                    x=[0, max_val], y=[0, max_val],
                    mode="lines",
                    name="xG = Goals (fair)",
                    line=dict(color="#9e9e9e", dash="dash", width=1),
                ))
                fig_xg.update_layout(
                    paper_bgcolor=_BG, plot_bgcolor=_BG,
                    font_color=_FC, coloraxis_showscale=False,
                    margin=dict(l=10, r=10, t=40, b=10),
                )
                st.plotly_chart(fig_xg, width="stretch")
                break
    else:
        # Use historical match data with model xg columns
        if all_matches is not None and not all_matches.empty:
            xg_data = all_matches[
                all_matches["home_xg"].notna() & all_matches["season"].isin([2022, 2026])
            ].copy()
            if not xg_data.empty:
                home_xg = xg_data.groupby("home_team").agg(
                    xg=("home_xg", "sum"), goals=("home_goals", "sum")
                ).reset_index().rename(columns={"home_team": "team"})
                away_xg = xg_data.groupby("away_team").agg(
                    xg=("away_xg", "sum"), goals=("away_goals", "sum")
                ).reset_index().rename(columns={"away_team": "team"})
                combined_xg = pd.concat([home_xg, away_xg]).groupby("team").sum().reset_index()

                fig_xgm = px.scatter(
                    combined_xg,
                    x="xg", y="goals",
                    hover_name="team",
                    color="goals",
                    color_continuous_scale=["#1a237e", "#00c853"],
                    labels={"xg": "Expected Goals (xG)", "goals": "Actual Goals"},
                    title="xG vs Actual Goals (from API data)",
                    height=420,
                )
                max_val = max(combined_xg["xg"].max(), combined_xg["goals"].max()) + 1
                fig_xgm.add_trace(go.Scatter(
                    x=[0, max_val], y=[0, max_val], mode="lines",
                    name="Fair value", line=dict(color="#9e9e9e", dash="dash"),
                ))
                fig_xgm.update_layout(
                    paper_bgcolor=_BG, plot_bgcolor=_BG,
                    font_color=_FC, coloraxis_showscale=False,
                    margin=dict(l=10, r=10, t=40, b=10),
                )
                st.plotly_chart(fig_xgm, width="stretch")
            else:
                st.info("xG data is available via BALLDONTLIE API for 2022 and 2026 seasons. Check API connectivity.")
        else:
            st.info("xG data will appear here once connected to the BALLDONTLIE API.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — HISTORICAL WC COMPARISON
# ══════════════════════════════════════════════════════════════════════════════
with tab_history:
    st.markdown('<p class="section-header">Historical World Cup Comparison (2010–2026)</p>', unsafe_allow_html=True)

    if all_matches is None or all_matches.empty:
        st.warning("Historical data could not be loaded. Check internet connectivity.")
    else:
        completed = all_matches.dropna(subset=["home_goals", "away_goals"]).copy()
        completed["total_goals"] = completed["home_goals"] + completed["away_goals"]
        completed["home_win"] = completed["home_goals"] > completed["away_goals"]
        completed["draw"]     = completed["home_goals"] == completed["away_goals"]
        completed["away_win"] = completed["home_goals"] < completed["away_goals"]

        by_season = completed.groupby("season").agg(
            Matches=("total_goals", "count"),
            Total_Goals=("total_goals", "sum"),
            Home_Wins=("home_win", "sum"),
            Draws=("draw", "sum"),
            Away_Wins=("away_win", "sum"),
        ).reset_index()
        by_season["Goals_per_Match"] = (by_season["Total_Goals"] / by_season["Matches"]).round(2)
        by_season["Home_Win_%"]      = (by_season["Home_Wins"] / by_season["Matches"] * 100).round(1)
        by_season["Draw_%"]          = (by_season["Draws"] / by_season["Matches"] * 100).round(1)
        by_season["Away_Win_%"]      = (by_season["Away_Wins"] / by_season["Matches"] * 100).round(1)

        # Summary metrics
        st.markdown(f"**Data coverage:** {len(by_season)} tournaments · {completed.shape[0]} completed matches")
        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("Total Matches",    f"{completed.shape[0]}")
        mc2.metric("Avg Goals/Match",  f"{completed['total_goals'].mean():.2f}")
        mc3.metric("Home Win Rate",    f"{completed['home_win'].mean()*100:.1f}%")
        mc4.metric("Draw Rate",        f"{completed['draw'].mean()*100:.1f}%")

        st.divider()

        # Goals per match trend
        fig_gpm = px.line(
            by_season,
            x="season", y="Goals_per_Match",
            markers=True,
            title="Average Goals per Match by Tournament",
            labels={"season": "Year", "Goals_per_Match": "Goals / Match"},
            height=300,
        )
        fig_gpm.update_traces(line_color="#00c853", marker_size=8)
        fig_gpm.update_layout(
            paper_bgcolor=_BG, plot_bgcolor=_BG,
            font_color=_FC, margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(fig_gpm, width="stretch")

        # Result distribution stacked bar
        fig_res = go.Figure()
        fig_res.add_trace(go.Bar(
            name="Home Win", x=by_season["season"], y=by_season["Home_Win_%"],
            marker_color="#00c853", text=by_season["Home_Win_%"].apply(lambda x: f"{x:.0f}%"),
            textposition="inside",
        ))
        fig_res.add_trace(go.Bar(
            name="Draw", x=by_season["season"], y=by_season["Draw_%"],
            marker_color="#ffd600", text=by_season["Draw_%"].apply(lambda x: f"{x:.0f}%"),
            textposition="inside",
        ))
        fig_res.add_trace(go.Bar(
            name="Away Win", x=by_season["season"], y=by_season["Away_Win_%"],
            marker_color="#2196f3", text=by_season["Away_Win_%"].apply(lambda x: f"{x:.0f}%"),
            textposition="inside",
        ))
        fig_res.update_layout(
            barmode="stack", title="Match Result Distribution by Tournament (%)",
            height=320, paper_bgcolor=_BG, plot_bgcolor=_BG,
            font_color=_FC, margin=dict(l=10, r=10, t=40, b=10),
            xaxis=dict(tickvals=by_season["season"].tolist(), title="Year"),
            yaxis=dict(ticksuffix="%", range=[0, 100]),
        )
        st.plotly_chart(fig_res, width="stretch")

        # Summary table
        disp = by_season.rename(columns={
            "season": "Year", "Matches": "Matches",
            "Total_Goals": "Goals", "Goals_per_Match": "Goals/M",
            "Home_Win_%": "H Win%", "Draw_%": "Draw%", "Away_Win_%": "A Win%"
        })
        st.dataframe(
            disp[["Year", "Matches", "Goals", "Goals/M", "H Win%", "Draw%", "A Win%"]],
            width="stretch", hide_index=True,
        )

        st.divider()

        # Most successful teams all-time in dataset
        st.markdown('<p class="section-header">Most Successful Teams (All-Time in Dataset)</p>', unsafe_allow_html=True)
        completed["winner"] = np.where(
            completed["home_goals"] > completed["away_goals"], completed["home_team"],
            np.where(completed["home_goals"] < completed["away_goals"], completed["away_team"], "Draw")
        )
        wins_by_team = (
            completed[completed["winner"] != "Draw"]["winner"]
            .value_counts()
            .head(20)
            .reset_index()
        )
        wins_by_team.columns = ["Team", "Wins"]

        fig_wbt = px.bar(
            wins_by_team,
            x="Wins", y="Team", orientation="h",
            color="Wins", color_continuous_scale=["#1a237e", "#00c853"],
            text="Wins",
            title="Most Match Wins — All World Cups in Dataset",
            height=460,
        )
        fig_wbt.update_layout(
            paper_bgcolor=_BG, plot_bgcolor=_BG,
            font_color=_FC, coloraxis_showscale=False,
            yaxis={"categoryorder": "total ascending"},
            margin=dict(l=10, r=40, t=40, b=10),
        )
        fig_wbt.update_traces(texttemplate="%{text}", textposition="outside")
        st.plotly_chart(fig_wbt, width="stretch")

add_betting_oracle_footer()
