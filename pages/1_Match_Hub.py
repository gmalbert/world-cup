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

from goallineiq_utils.api_client import (
    get_all_wc_matches, get_upcoming_matches, get_current_standings,
    bdl_client, apf_client, espn_client,
)
from goallineiq_utils.models import WC2026_GROUPS
from goallineiq_utils.timezone_utils import (
    assign_realistic_match_times, format_match_time_friendly
)
from goallineiq_utils.weather import add_weather_to_matches, get_weather_for_match

st.title("🏟️ Match Hub")
st.caption("Live scores · Group standings · Schedule · Knockout bracket")
st.divider()

tab_schedule, tab_standings, tab_bracket, tab_groups = st.tabs([
    "🗓️ Schedule", "📊 Group Standings", "🏆 Knockout Bracket", "📋 Group Draw"
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — SCHEDULE
# ══════════════════════════════════════════════════════════════════════════════
with tab_schedule:
    # ── Live scoreboard (ESPN) ───────────────────────────────────────────────
    live_df = espn_client.get_scoreboard()
    live_active = live_df is not None and not live_df.empty and \
                  live_df["completed"].dtype == bool and \
                  (~live_df["completed"]).any() if live_df is not None and not live_df.empty else False

    if live_df is not None and not live_df.empty:
        live_now = live_df[~live_df["completed"].astype(bool)] if "completed" in live_df.columns else pd.DataFrame()
        if not live_now.empty:
            st.markdown('<p class="section-header" style="color:#f44336;">🔴 LIVE NOW</p>', unsafe_allow_html=True)
            for _, lrow in live_now.iterrows():
                hg = lrow.get("home_goals", "—")
                ag = lrow.get("away_goals", "—")
                score_str = f"{hg} – {ag}" if (hg not in (None, "", "None") and ag not in (None, "", "None")) else "v"
                st.markdown(
                    f"**{lrow.get('home_team','')}** `{score_str}` **{lrow.get('away_team','')}**"
                    f"  ·  {lrow.get('status','')}"
                )
            st.divider()

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
        
        # Assign realistic match times for 2026 fixtures
        if season_filter == 2026:
            season_df = assign_realistic_match_times(season_df)
        
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
                    city = str(row.get("city", ""))
                    rnd = str(row.get("round", row.get("group", "")))
                    
                    # Format match time
                    match_time = ""
                    if pd.notna(row.get("date")):
                        match_dt = pd.to_datetime(row["date"], utc=True)
                        match_time = format_match_time_friendly(match_dt)
                    
                    # Determine match status
                    completed = (
                        pd.notna(hg) and pd.notna(ag)
                        or "FT" in status or "COMPLETED" in status
                    )
                    live = "LIVE" in status or "1H" in status or "2H" in status
                    
                    # Get weather forecast for upcoming matches
                    weather_info = ""
                    match_city = city if city else venue
                    if not completed and not live and match_city and pd.notna(row.get("date")):
                        weather = get_weather_for_match(match_city, str(row["date"]))
                        if weather:
                            temp_emoji = "🔥" if weather["temperature_c"] > 30 else "🥶" if weather["temperature_c"] < 10 else "🌡️"
                            weather_emoji = "☔" if weather["precipitation_mm"] > 1 else "☀️"
                            weather_info = f"{weather_emoji} {weather['temperature_f']}°F"

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
                            mc2.markdown(f"<div style='text-align:center;color:#00c853;font-size:0.85rem;'>{match_time}</div>", unsafe_allow_html=True)
                        mc3.markdown(f"**{away}**")
                        venue_weather = f"{rnd}  \n📍 {venue[:30]}"
                        if weather_info:
                            venue_weather += f"  \n{weather_info}"
                        mc4.caption(venue_weather)
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

    # Load simulation advancement probs for qualification indicator
    from pathlib import Path
    import json as _json
    _sim_file = Path(__file__).parent.parent / "data_files" / "tournament_simulation.json"
    _sim_adv: dict[str, float] = {}
    try:
        _sim_data = _json.loads(_sim_file.read_text(encoding="utf-8"))
        for row in _sim_data.get("results", []):
            _sim_adv[row["team"]] = row.get("Group Stage", 100.0)
    except Exception:
        pass

    def _qual_badge(rank: int, pts: int, played: int, gd: int) -> str:
        """Return a qualification status label given current rank and stats.
        2026 format: top 2 per group qualify, 8 best 3rd-place teams also qualify.
        3 group matches per team (max 9 pts).
        """
        remaining = max(0, 3 - played)
        max_pts = pts + remaining * 3
        if rank <= 2 and remaining == 0:
            return "🟢 Qualified"
        if rank <= 2 and pts >= 6:
            return "🟢 Likely Qualified"
        if rank == 3:
            return "🟡 3rd Place"
        if max_pts < 3 and played > 0:
            return "🔴 Eliminated"
        return "⏳ TBD"

    if standings is not None and not standings.empty and "group" in standings.columns:
        all_groups = sorted(standings["group"].unique())
        st.caption(f"**{len(all_groups)} groups · Last updated: {datetime.now(timezone.utc).strftime('%H:%M UTC')}**")

        for row_start in range(0, len(all_groups), 2):
            row_groups = all_groups[row_start:row_start + 2]
            cols = st.columns(len(row_groups))
            for ci, grp in enumerate(row_groups):
                grp_df = standings[standings["group"] == grp].copy()

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

                # Sort by Pts desc, then GD
                if "Pts" in grp_df.columns:
                    sort_cols = [c for c in ["Pts", "GD"] if c in grp_df.columns]
                    grp_df = grp_df.sort_values(sort_cols, ascending=False).reset_index(drop=True)
                    grp_df.insert(0, "#", range(1, len(grp_df) + 1))

                # Add qualification status
                status_list = []
                for i, row_s in grp_df.iterrows():
                    rank = i + 1 if "#" not in grp_df.columns else int(row_s.get("#", i + 1))
                    pts   = int(row_s.get("Pts", 0))
                    played = int(row_s.get("P", 0))
                    gd    = int(row_s.get("GD", 0))
                    status_list.append(_qual_badge(rank, pts, played, gd))
                grp_df["Status"] = status_list

                keep = [c for c in ["#", "Team", "P", "W", "D", "L", "GD", "Pts", "Status"]
                        if c in grp_df.columns]
                grp_display = grp_df[keep].head(4)

                with cols[ci]:
                    _grp_label = str(grp).replace("Group ", "").replace("group ", "")
                    st.markdown(f"**Group {_grp_label}**")
                    st.dataframe(grp_display, hide_index=True, width="stretch", height=235)
        from goallineiq_utils.models import build_predictor, FALLBACK_ELO
        from goallineiq_utils.api_client import get_all_wc_matches as _get_all
        _all = _get_all()
        _pred = build_predictor(_all)

        st.info(
            "Live standings appear once results are available.  "
            "Showing pre-tournament Elo rankings per group with model advancement probability."
        )

        grp_rows_all: list[dict] = []
        for grp_letter, teams in WC2026_GROUPS.items():
            team_elos_g = []
            for t in teams:
                try:
                    ep = _pred.predict(t, t, neutral=True)
                    elo = int(ep["home_elo"])
                except Exception:
                    elo = FALLBACK_ELO.get(t, 1500)
                adv_pct = _sim_adv.get(t, None)
                team_elos_g.append((t, elo, adv_pct))
            team_elos_g.sort(key=lambda x: x[1], reverse=True)
            for rank_i, (t, elo, adv_pct) in enumerate(team_elos_g, 1):
                qual_tag = "🟢 Likely" if rank_i <= 2 else "🟡 3rd" if rank_i == 3 else "⚪"
                grp_rows_all.append({
                    "Group": grp_letter, "Team": t,
                    "Elo": elo,
                    "Adv %": f"{adv_pct:.0f}%" if adv_pct is not None else "—",
                    "Expected": qual_tag,
                })

        draw_df = pd.DataFrame(grp_rows_all)
        all_groups = sorted(draw_df["Group"].unique())

        for row_start in range(0, len(all_groups), 2):
            row_groups = all_groups[row_start:row_start + 2]
            cols = st.columns(len(row_groups))
            for ci, grp in enumerate(row_groups):
                grp_df = draw_df[draw_df["Group"] == grp][
                    ["Team", "Elo", "Adv %", "Expected"]
                ].copy()
                with cols[ci]:
                    _grp_label2 = str(grp).replace("Group ", "").replace("group ", "")
                    st.markdown(f"**Group {_grp_label2}**")
                    st.dataframe(grp_df, hide_index=True, width="stretch", height=235)

        st.caption("🟢 Likely top 2 · 🟡 Potential 3rd qualifier · ⚪ Unlikely  |  Adv % = simulation group-stage advancement")

    # ── Group Stage Permutations Tool ─────────────────────────────────────────
    st.divider()
    with st.expander("🔀 Group Stage Permutations — What-If Tool", expanded=False):
        st.caption(
            "Pick results for remaining group matches and instantly see how the standings change. "
            "Helps identify qualification scenarios on the final matchday."
        )

        perm_group = st.selectbox(
            "Select group", sorted(WC2026_GROUPS.keys()), key="perm_group_sel"
        )
        perm_teams = WC2026_GROUPS[perm_group]

        # Build all possible pairings for a group of 4 (round-robin = 6 matches)
        from itertools import combinations as _comb
        all_pairs = list(_comb(perm_teams, 2))

        # Get actual results from match data so we can pre-fill played matches
        _played_results: dict[tuple, tuple] = {}
        try:
            _all_wc = get_all_wc_matches()
            if _all_wc is not None and not _all_wc.empty:
                _wc26 = _all_wc[_all_wc["season"] == 2026].dropna(subset=["home_goals", "away_goals"])
                for _, _mr in _wc26.iterrows():
                    _ht, _at = str(_mr["home_team"]), str(_mr["away_team"])
                    _hg, _ag = int(_mr["home_goals"]), int(_mr["away_goals"])
                    if (_ht in perm_teams) and (_at in perm_teams):
                        _played_results[(_ht, _at)] = (_hg, _ag)
        except Exception:
            pass

        st.markdown("**Pick a result for each match:**")
        perm_goals: dict[tuple, tuple] = {}
        RESULT_OPTIONS = ["Home Win", "Draw", "Away Win"]

        for pair in all_pairs:
            home_t, away_t = pair
            already_played = (home_t, away_t) in _played_results or (away_t, home_t) in _played_results
            if already_played:
                if (home_t, away_t) in _played_results:
                    hg, ag = _played_results[(home_t, away_t)]
                else:
                    ag, hg = _played_results[(away_t, home_t)]
                st.write(f"✅ **{home_t} {hg}–{ag} {away_t}** *(result locked)*")
                perm_goals[(home_t, away_t)] = (hg, ag)
            else:
                res = st.radio(
                    f"{home_t} vs {away_t}",
                    RESULT_OPTIONS,
                    horizontal=True,
                    index=0,
                    key=f"perm_{home_t}_{away_t}",
                )
                if res == "Home Win":
                    perm_goals[(home_t, away_t)] = (1, 0)
                elif res == "Draw":
                    perm_goals[(home_t, away_t)] = (1, 1)
                else:
                    perm_goals[(home_t, away_t)] = (0, 1)

        # Compute standings from selected results
        pts_map: dict[str, int]  = {t: 0 for t in perm_teams}
        gd_map:  dict[str, int]  = {t: 0 for t in perm_teams}
        gf_map:  dict[str, int]  = {t: 0 for t in perm_teams}
        for (ht, at), (hg, ag) in perm_goals.items():
            gf_map[ht]  += hg; gf_map[at]  += ag
            gd_map[ht]  += hg - ag; gd_map[at]  += ag - hg
            if hg > ag:
                pts_map[ht] += 3
            elif ag > hg:
                pts_map[at] += 3
            else:
                pts_map[ht] += 1; pts_map[at] += 1

        perm_rows = sorted(perm_teams,
                           key=lambda t: (pts_map[t], gd_map[t], gf_map[t]),
                           reverse=True)
        perm_df = pd.DataFrame([{
            "Rank": i + 1,
            "Team": t,
            "Pts": pts_map[t],
            "GD": gd_map[t],
            "GF": gf_map[t],
            "Status": ("🟢 Qualified" if i < 2 else "🟡 3rd Place" if i == 2 else "🔴 Eliminated"),
        } for i, t in enumerate(perm_rows)])

        st.divider()
        st.markdown(f"**Projected Standings — Group {perm_group}**")

        def _color_status_perm(val):
            if "Qualified" in str(val):
                return "color:#00c853;font-weight:700;"
            if "3rd" in str(val):
                return "color:#ffd600;"
            if "Eliminated" in str(val):
                return "color:#f44336;"
            return ""

        s_perm = perm_df.style
        styled_perm = s_perm.map(_color_status_perm, subset=["Status"]) \
                     if hasattr(s_perm, "map") \
                     else s_perm.applymap(_color_status_perm, subset=["Status"])
        st.dataframe(styled_perm, width="stretch", hide_index=True)
        st.caption("Tiebreaker (simplified): Pts → GD → GF. FIFA applies H2H record next.")
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


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — GROUP DRAW STRENGTH ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
with tab_groups:
    st.markdown('<p class="section-header">📋 2026 Group Draw · Strength Analysis</p>', unsafe_allow_html=True)
    st.caption(
        "Each group shows team Elo ratings and predicted qualification probability.  "
        "Elo is trained on WC matches 2010–2026."
    )

    from goallineiq_utils.models import build_predictor, WC2026_GROUPS, FALLBACK_ELO
    from goallineiq_utils.api_client import get_all_wc_matches as _gd_get_all
    from pathlib import Path as _Path
    import json as _json

    _gd_all = _gd_get_all()
    _gd_pred = build_predictor(_gd_all)

    # Load simulation advancement % for each team
    _gd_adv: dict[str, float] = {}
    try:
        _sim_path = _Path(__file__).parent.parent / "data_files" / "tournament_simulation.json"
        _sim_data = _json.loads(_sim_path.read_text(encoding="utf-8"))
        for _r in _sim_data.get("results", []):
            _gd_adv[_r["team"]] = _r.get("Round of 32", _r.get("Group Stage", 100.0))
    except Exception:
        pass

    group_data_hub = []
    for _gname, _gteams in sorted(WC2026_GROUPS.items()):
        _gelos = []
        for _gt in _gteams:
            try:
                _gp = _gd_pred.predict(_gt, _gt, neutral=True)
                _gelo = int(_gp["home_elo"])
            except Exception:
                _gelo = FALLBACK_ELO.get(_gt, 1500)
            _gelos.append((_gt, _gelo))
        _gelos.sort(key=lambda x: x[1], reverse=True)
        _avg_elo = sum(e for _, e in _gelos) / len(_gelos)
        group_data_hub.append({
            "group": _gname,
            "teams": _gelos,
            "avg_elo": _avg_elo,
            "strength": "🔥" * min(5, max(1, int((_avg_elo - 1700) / 50))),
        })

    for _row_start in range(0, 12, 4):
        _row_groups = group_data_hub[_row_start:_row_start + 4]
        _gcols = st.columns(4)
        for _ci, _gdata in enumerate(_row_groups):
            with _gcols[_ci]:
                    st.markdown(
                        f"**Group {_gdata['group']}** {_gdata['strength']}<br>"
                        f"<small style='color:#9e9e9e;'>Avg Elo: {int(_gdata['avg_elo'])}</small>",
                        unsafe_allow_html=True,
                    )
                    for _rank, (_team, _elo) in enumerate(_gdata["teams"], 1):
                        _qual = "🟢" if _rank <= 2 else ("🟡" if _rank == 3 else "⚪")
                        _adv = _gd_adv.get(_team)
                        _adv_str = f" · {_adv:.0f}% adv" if _adv else ""
                        st.caption(f"{_qual} {_team} · `{_elo}`{_adv_str}")

    st.caption("🟢 Top 2 qualify · 🟡 Potential 3rd-place qualifier (8 best) · ⚪ Unlikely · Adv % = simulation advancement")

    # Group strength comparison chart
    st.divider()
    st.markdown('<p class="section-header">📊 Group Strength Comparison</p>', unsafe_allow_html=True)
    import plotly.express as _px_gd
    _strength_rows = []
    for _gdata in group_data_hub:
        for _rank, (_team, _elo) in enumerate(_gdata["teams"], 1):
            _strength_rows.append({"Group": _gdata["group"], "Team": _team, "Elo": _elo, "Rank": _rank})
    _strength_df = pd.DataFrame(_strength_rows)
    _fig_gs = _px_gd.bar(
        _strength_df.groupby("Group")["Elo"].mean().reset_index(),
        x="Group", y="Elo",
        color="Elo",
        color_continuous_scale=["#1a237e", "#00c853"],
        title="Average Group Elo (higher = stronger group)",
        height=320,
    )
    _BG_HUB = "#e3f2fd" if _is_day else "#071528"
    _FC_HUB = "#0d1b2a" if _is_day else "#e0f7fa"
    _fig_gs.update_layout(
        paper_bgcolor=_BG_HUB, plot_bgcolor=_BG_HUB,
        font_color=_FC_HUB, coloraxis_showscale=False,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    _fig_gs.update_traces(marker_line_width=0)
    st.plotly_chart(_fig_gs, width="stretch")


add_betting_oracle_footer()
