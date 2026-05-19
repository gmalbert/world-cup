"""
Match Hub — Live scores, group standings, schedule & knockout bracket.
"""
import os
import sys
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import timezone, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv()
from footer import add_betting_oracle_footer

_is_day = st.session_state.get("_is_day", False)
_fg = "#0d1b2a" if _is_day else "#e0f7fa"
_soft = "#546e7a" if _is_day else "#9e9e9e"


st.markdown(f"""
<style>
    .section-header {{font-size:1.2rem;font-weight:700;color:#00c853;
        border-bottom:1px solid #2c2f4a;padding-bottom:0.4rem;margin-bottom:1rem;}}
    .live-badge {{background:#f44336;color:#fff;padding:2px 7px;border-radius:4px;
        font-size:0.75rem;font-weight:700;}}
    .completed-badge {{background:#424242;color:#ccc;padding:2px 7px;border-radius:4px;
        font-size:0.75rem;}}
    .upcoming-badge {{background:#1565c0;color:#fff;padding:2px 7px;border-radius:4px;
        font-size:0.75rem;}}
    .score-display {{font-size:1.6rem;font-weight:800;color:{_fg};text-align:center;}}
</style>
""", unsafe_allow_html=True)

from utils.api_client import (
    get_all_wc_matches, get_upcoming_matches, get_current_standings,
    bdl_client, apf_client,
)
from utils.models import WC2026_GROUPS

st.title("🏟️ Match Hub")
st.caption("Live scores · Group standings · Schedule · Knockout bracket")
st.divider()

tab_schedule, tab_standings, tab_bracket = st.tabs([
    "🗓️ Schedule", "📊 Group Standings", "🏆 Knockout Bracket"
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — SCHEDULE
# ══════════════════════════════════════════════════════════════════════════════
with tab_schedule:
    all_matches = get_all_wc_matches()

    season_filter = st.selectbox(
        "Tournament",
        options=[2026, 2022, 2018, 2014, 2010],
        format_func=lambda y: {
            2026: "2026 — USA/Canada/Mexico",
            2022: "2022 — Qatar",
            2018: "2018 — Russia",
            2014: "2014 — Brazil",
            2010: "2010 — South Africa",
        }.get(y, str(y)),
        index=0,
    )

    if all_matches is not None and not all_matches.empty:
        season_df = all_matches[all_matches["season"] == season_filter].copy()
        season_df["date"] = pd.to_datetime(season_df["date"], errors="coerce", utc=True)
        season_df = season_df.sort_values("date")

        if season_df.empty:
            st.info(f"No data loaded for the {season_filter} World Cup yet.")
        else:
            # Group by date
            season_df["date_only"] = season_df["date"].dt.date
            unique_dates = sorted(season_df["date_only"].dropna().unique())

            if not unique_dates:
                st.dataframe(season_df, width="stretch")
            else:
                selected_date = st.select_slider(
                    "Jump to date",
                    options=unique_dates,
                    value=unique_dates[0],
                )
                day_df = season_df[season_df["date_only"] == selected_date]

                st.markdown(f"**Matches on {selected_date}**")
                for _, row in day_df.iterrows():
                    home = str(row.get("home_team", "?"))
                    away = str(row.get("away_team", "?"))
                    hg = row.get("home_goals")
                    ag = row.get("away_goals")
                    status = str(row.get("status", "")).upper()
                    venue = str(row.get("venue", ""))
                    rnd = str(row.get("round", row.get("group", "")))

                    completed = (
                        pd.notna(hg) and pd.notna(ag)
                        or "FT" in status or "COMPLETED" in status
                    )
                    live = "LIVE" in status or "1H" in status or "2H" in status

                    with st.container(border=True):
                        mc1, mc2, mc3, mc4 = st.columns([3, 2, 3, 2])
                        mc1.markdown(f"**{home}**")
                        if completed and pd.notna(hg) and pd.notna(ag):
                            mc2.markdown(
                                f"<div class='score-display'>{int(hg)} — {int(ag)}</div>",
                                unsafe_allow_html=True,
                            )
                        elif live:
                            mc2.markdown("<div style='text-align:center;color:#f44336;font-weight:700;'>LIVE</div>", unsafe_allow_html=True)
                        else:
                            mc2.markdown("<div style='text-align:center;color:#9e9e9e;'>vs</div>", unsafe_allow_html=True)
                        mc3.markdown(f"**{away}**")
                        mc4.caption(f"{rnd}  \n📍 {venue[:30]}")
    else:
        st.warning("Could not load match data. Check API connectivity.")

    # Show all seasons data summary
    st.divider()
    st.markdown('<p class="section-header">All-Time World Cup Data Coverage</p>', unsafe_allow_html=True)

    if all_matches is not None and not all_matches.empty:
        summary = (
            all_matches.groupby("season")
            .agg(
                Matches=("home_team", "count"),
                Completed=("home_goals", lambda x: x.notna().sum()),
                Source=("source", "first"),
            )
            .reset_index()
        )
        summary.columns = ["Season", "Total Matches", "With Results", "Source"]
        st.dataframe(summary, width="stretch", hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — GROUP STANDINGS
# ══════════════════════════════════════════════════════════════════════════════
with tab_standings:
    standings = get_current_standings()

    if standings is not None and not standings.empty and "group" in standings.columns:
        all_groups = sorted(standings["group"].unique())
        st.caption(f"**{len(all_groups)} groups · Last updated: {datetime.now(timezone.utc).strftime('%H:%M UTC')}**")

        # Render in rows of 2 groups so each table stays readable at half-screen width
        for row_start in range(0, len(all_groups), 2):
            row_groups = all_groups[row_start:row_start + 2]
            cols = st.columns(len(row_groups))
            for ci, grp in enumerate(row_groups):
                grp_df = standings[standings["group"] == grp].copy()

                # Normalise column names
                col_map = {}
                for c in grp_df.columns:
                    cl = c.lower()
                    if "team" in cl and "name" not in cl:
                        col_map[c] = "Team"
                    elif c == "played":
                        col_map[c] = "P"
                    elif c == "won":
                        col_map[c] = "W"
                    elif c == "drawn":
                        col_map[c] = "D"
                    elif c == "lost":
                        col_map[c] = "L"
                    elif "goal_diff" in cl or c == "gd":
                        col_map[c] = "GD"
                    elif c == "points":
                        col_map[c] = "Pts"
                grp_df = grp_df.rename(columns=col_map)

                keep = [c for c in ["Team", "P", "Pts"] if c in grp_df.columns]
                grp_display = grp_df[keep].head(4)

                with cols[ci]:
                    st.markdown(f"**Group {grp}**")
                    st.dataframe(grp_display, hide_index=True, width="stretch", height=235)
    else:
        # Pre-tournament: show expected groups from fallback
        st.info(
            "Live standings will appear here once the tournament begins (June 11, 2026).  \n"
            "Showing the confirmed 2026 World Cup group draw:"
        )
        grp_rows = []
        for grp_letter, teams in WC2026_GROUPS.items():
            for t in teams:
                grp_rows.append({"Group": grp_letter, "Team": t})
        draw_df = pd.DataFrame(grp_rows)
        all_groups = sorted(draw_df["Group"].unique())

        for row_start in range(0, len(all_groups), 2):
            row_groups = all_groups[row_start:row_start + 2]
            cols = st.columns(len(row_groups))
            for ci, grp in enumerate(row_groups):
                grp_df = draw_df[draw_df["Group"] == grp][["Team"]].copy()
                grp_df.insert(1, "P", 0)
                grp_df.insert(2, "Pts", 0)
                with cols[ci]:
                    st.markdown(f"**Group {grp}**")
                    st.dataframe(grp_df, hide_index=True, width="stretch", height=235)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — KNOCKOUT BRACKET
# ══════════════════════════════════════════════════════════════════════════════
with tab_bracket:
    st.markdown('<p class="section-header">2026 Knockout Bracket</p>', unsafe_allow_html=True)

    # Pull any completed bracket data
    all_matches_data = get_all_wc_matches()
    bracket_df = pd.DataFrame()
    if all_matches_data is not None and not all_matches_data.empty:
        wc26 = all_matches_data[all_matches_data["season"] == 2026].copy()
        knockout_keywords = ["round of", "r16", "quarterfinal", "semifinal", "final", "knockout"]
        mask = wc26["round"].str.lower().apply(
            lambda x: any(kw in str(x) for kw in knockout_keywords)
        )
        bracket_df = wc26[mask]

    if not bracket_df.empty:
        st.caption("Knockout matches pulled from live data:")
        for stage in ["Round of 32", "Round of 16", "Quarterfinals", "Semifinals", "Final"]:
            stage_df = bracket_df[
                bracket_df["round"].str.lower().str.contains(
                    stage.lower().replace("s", "").replace(" ", ""), na=False
                )
            ]
            if not stage_df.empty:
                st.markdown(f"**{stage}**")
                display = stage_df[["home_team", "home_goals", "away_goals", "away_team", "date", "venue"]].copy()
                display.columns = ["Home", "HG", "AG", "Away", "Date", "Venue"]
                st.dataframe(display, hide_index=True, width="stretch")
    else:
        st.info(
            "The 2026 World Cup bracket will populate here once the group stage completes (est. ~July 1, 2026).\n\n"
            "**Format:**\n"
            "- 12 groups × 4 teams = 48 teams\n"
            "- Top 2 per group + 8 best 3rd-placed teams → **Round of 32** (32 teams)\n"
            "- → Round of 16 → Quarterfinals → Semifinals → **Final (July 19, 2026)**\n"
        )

        # Show a simple text bracket based on group letters
        st.markdown("""
        ```
        Round of 32 → Round of 16 → Quarterfinals → Semifinals → FINAL
        ───────────────────────────────────────────────────────────────────
        1A vs 3(BCDE)       ↘
        1C vs 3(ABCD)       → R16 → QF → SF ↘
        1B vs 3(AFGH)       ↗                  FINAL
        1D vs 3(EFGHI)      → R16 → QF → SF ↗
        1E vs 3(JKLEF)      ↘
        1G vs 3(GHIJK)      → R16 → QF → SF ↘
        1F vs 3(ABCL)       ↗                  WINNER
        1H vs 3(remaining)  → R16 → QF → SF ↗
        ... (same pattern for 1I–1L groups)
        ```
        """)

add_betting_oracle_footer()
