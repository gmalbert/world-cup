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
from goallineiq_utils.models import build_predictor

# ── Load ──────────────────────────────────────────────────────────────────────
all_matches     = get_all_wc_matches()
top_scorers_raw = get_historical_top_scorers()

# Build predictor for xG calculations
try:
    predictor = build_predictor(all_matches)
except Exception:
    predictor = None

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
                ).reset_index().rename(columns={"home_team": "Team"})
                away_agg = sm.groupby("away_team").agg(
                    GF=("away_goals", "sum"), GA=("home_goals", "sum"), M=("away_team", "count")
                ).reset_index().rename(columns={"away_team": "Team"})
                combined = pd.concat([home_agg, away_agg]).groupby("Team").sum().reset_index()
                combined["GD"] = combined["GF"] - combined["GA"]
                combined = combined.sort_values("GF", ascending=False)
                st.dataframe(combined, width="stretch", hide_index=True)

                fig_td = px.bar(
                    combined.head(16),
                    x="Team", y=["GF", "GA"],
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
        "xG values are MODEL-GENERATED using our Dixon-Coles Poisson model based on Elo ratings. "
        "Teams above the diagonal are 'overperforming' their expected goals; teams below are underperforming."
    )

    # Generate model-based xG for completed matches
    if all_matches is not None and not all_matches.empty:
        # Get completed matches for 2022 and 2026 with actual scores
        completed_matches = all_matches[
            (all_matches["season"].isin([2022, 2026])) &
            (all_matches["home_goals"].notna()) &
            (all_matches["away_goals"].notna()) &
            (all_matches["status"].str.contains("completed|FT", case=False, na=False))
        ].copy()

        if not completed_matches.empty and predictor is not None:
            st.info(
                f"📊 Analyzing {len(completed_matches)} completed matches from 2022 and 2026 tournaments. "
                "Model xG calculated retroactively using current Elo ratings."
            )
            
            # Calculate model xG for each match
            xg_results = []
            for _, match in completed_matches.iterrows():
                home_team = match["home_team"]
                away_team = match["away_team"]
                
                try:
                    pred = predictor.predict(home_team, away_team, neutral=True)
                    xg_results.append({
                        "home_team": home_team,
                        "away_team": away_team,
                        "home_goals": match["home_goals"],
                        "away_goals": match["away_goals"],
                        "home_xg": pred["home_xg"],
                        "away_xg": pred["away_xg"],
                        "season": match["season"]
                    })
                except Exception:
                    continue  # Skip if team not in model
            
            if xg_results:
                xg_df = pd.DataFrame(xg_results)
                
                # Aggregate by team
                home_agg = xg_df.groupby("home_team").agg({
                    "home_xg": "sum",
                    "home_goals": "sum"
                }).rename(columns={"home_team": "team", "home_xg": "xg", "home_goals": "goals"})
                
                away_agg = xg_df.groupby("away_team").agg({
                    "away_xg": "sum",
                    "away_goals": "sum"
                }).rename(columns={"away_team": "team", "away_xg": "xg", "away_goals": "goals"})
                
                # Combine home and away stats
                home_agg = home_agg.reset_index().rename(columns={"home_team": "team"})
                away_agg = away_agg.reset_index().rename(columns={"away_team": "team"})
                combined_xg = pd.concat([home_agg, away_agg]).groupby("team").sum().reset_index()
                
                # Calculate xG difference
                combined_xg["xg_diff"] = combined_xg["goals"] - combined_xg["xg"]
                combined_xg = combined_xg.sort_values("xg_diff", ascending=False)
                
                # Plot
                fig_xg = px.scatter(
                    combined_xg,
                    x="xg",
                    y="goals",
                    hover_name="team",
                    hover_data={
                        "xg": ":.2f",
                        "goals": ":.0f",
                        "xg_diff": ":.2f"
                    },
                    color="xg_diff",
                    color_continuous_scale="RdYlGn",
                    color_continuous_midpoint=0,
                    labels={
                        "xg": "Model Expected Goals (xG)",
                        "goals": "Actual Goals Scored",
                        "xg_diff": "Goal Diff vs xG"
                    },
                    title="Model xG vs Actual Goals — 2022 & 2026 World Cups",
                    height=500,
                )
                
                # Add diagonal reference line
                max_val = max(combined_xg["xg"].max(), combined_xg["goals"].max()) + 2
                fig_xg.add_trace(go.Scatter(
                    x=[0, max_val],
                    y=[0, max_val],
                    mode="lines",
                    name="xG = Goals (expected)",
                    line=dict(color="#9e9e9e", dash="dash", width=2),
                    showlegend=True
                ))
                
                fig_xg.update_layout(
                    paper_bgcolor=_BG,
                    plot_bgcolor=_BG,
                    font_color=_FC,
                    margin=dict(l=10, r=10, t=40, b=10),
                    coloraxis_colorbar=dict(
                        title="Goal Diff",
                        tickmode="linear",
                        tick0=-5,
                        dtick=2.5
                    )
                )
                
                st.plotly_chart(fig_xg, width="stretch")
                
                # Top performers table
                col_over, col_under = st.columns(2)
                
                with col_over:
                    st.markdown("**🔥 Top Overperformers** (Goals > xG)")
                    top_over = combined_xg.nlargest(5, "xg_diff")[["team", "goals", "xg", "xg_diff"]].copy()
                    top_over.columns = ["Team", "Goals", "xG", "xG Diff"]
                    top_over["xG"] = top_over["xG"].round(2)
                    top_over["xG Diff"] = top_over["xG Diff"].apply(lambda x: f"+{x:.2f}")
                    st.dataframe(top_over, width="stretch", hide_index=True)
                
                with col_under:
                    st.markdown("**❄️ Top Underperformers** (Goals < xG)")
                    top_under = combined_xg.nsmallest(5, "xg_diff")[["team", "goals", "xg", "xg_diff"]].copy()
                    top_under.columns = ["Team", "Goals", "xG", "xG Diff"]
                    top_under["xG"] = top_under["xG"].round(2)
                    top_under["xG Diff"] = top_under["xG Diff"].round(2)
                    st.dataframe(top_under, width="stretch", hide_index=True)
            else:
                st.warning("Unable to calculate model xG — teams not found in prediction model.")
        else:
            st.info(
                "📊 xG analysis will populate once matches are completed. "
                "Our Dixon-Coles model will retroactively calculate expected goals for all finished games."
            )
    else:
        st.warning("No match data available. Check data connectivity.")


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
