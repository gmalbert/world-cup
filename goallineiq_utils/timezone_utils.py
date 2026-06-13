"""
Timezone utilities for displaying match times in user's local timezone.
Also assigns realistic World Cup match times (12:00, 15:00, 18:00, 21:00 local).
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Optional

# World Cup 2026 typical match start times (local venue time)
# Early matches at 12:00, afternoon at 15:00 & 18:00, evening at 21:00
WC_MATCH_TIMES_LOCAL = [
    (12, 0),  # Noon
    (15, 0),  # 3 PM
    (18, 0),  # 6 PM
    (21, 0),  # 9 PM
]

# Timezone offsets for host cities (hours from UTC during June/July - DST active)
VENUE_TIMEZONES = {
    # USA - Eastern Time
    "Boston": -4, "New York": -4, "Philadelphia": -4, "Miami": -4, "Atlanta": -4,
    "New York/New Jersey": -4, "Boston (Foxborough)": -4, "Miami (Miami Gardens)": -4,
    
    # USA - Central Time
    "Dallas": -5, "Houston": -5, "Kansas City": -5,
    "Dallas (Arlington)": -5,
    
    # USA - Mountain Time
    
    # USA - Pacific Time
    "Los Angeles": -7, "San Francisco": -7, "Seattle": -7, "Las Vegas": -7,
    "Los Angeles (Inglewood)": -7, "San Francisco Bay Area (Santa Clara)": -7,
    "Vancouver": -7,  # Pacific Time
    
    # Mexico - Central Time (no DST in some states)
    "Mexico City": -5, "Guadalajara": -5, "Monterrey": -5,
    "Guadalajara (Zapopan)": -5, "Monterrey (Guadalupe)": -5,
    
    # Canada
    "Toronto": -4,  # Eastern
}


def assign_realistic_match_times(df: pd.DataFrame) -> pd.DataFrame:
    """
    Assign realistic World Cup match times to fixtures based on date and venue.
    
    World Cup matches typically start at:
    - 12:00 (noon) local time
    - 15:00 (3 PM) local time  
    - 18:00 (6 PM) local time
    - 21:00 (9 PM) local time
    
    Multiple matches on the same day get different time slots.
    """
    if df is None or df.empty:
        return df
    
    df = df.copy()
    
    # Ensure date column exists and is datetime
    if "date" not in df.columns:
        return df
    
    df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
    
    # Group by date to assign different times to matches on the same day
    for date_val, group_indices in df.groupby(df["date"].dt.date).groups.items():
        for idx, (match_idx, time_slot) in enumerate(zip(group_indices, WC_MATCH_TIMES_LOCAL * 10)):
            # Get venue timezone offset
            venue = df.loc[match_idx, "venue"] if "venue" in df.columns else None
            tz_offset = VENUE_TIMEZONES.get(str(venue), -5)  # Default to Central Time
            
            # Create datetime with realistic local time, then convert to UTC
            hour_local, minute_local = time_slot
            
            # Get the base date
            base_date = df.loc[match_idx, "date"]
            if pd.isna(base_date):
                continue
                
            # Set time in local venue timezone, then convert to UTC
            local_hour_utc = hour_local - tz_offset  # Convert to UTC
            
            new_datetime = base_date.replace(hour=local_hour_utc % 24, minute=minute_local, second=0)
            
            # Adjust date if we wrapped around midnight
            if local_hour_utc < 0:
                new_datetime = new_datetime + timedelta(days=1)
            elif local_hour_utc >= 24:
                new_datetime = new_datetime - timedelta(days=1)
            
            df.loc[match_idx, "date"] = new_datetime
    
    return df


def format_datetime_local(dt: pd.Timestamp, include_timezone: bool = True) -> str:
    """
    Format a UTC datetime for display in user's local timezone.
    Uses browser timezone via Streamlit's component API.
    
    Args:
        dt: Pandas Timestamp in UTC
        include_timezone: Whether to show timezone abbreviation
    
    Returns:
        Formatted string like "Jun 11, 2026 3:00 PM" or "Jun 11, 2026 3:00 PM EDT"
    """
    if pd.isna(dt):
        return "TBD"
    
    try:
        # Convert to Python datetime
        if hasattr(dt, 'to_pydatetime'):
            dt = dt.to_pydatetime()
        
        # For now, display in UTC with clear label
        # In production, use JavaScript to convert to browser timezone
        formatted = dt.strftime("%b %d, %Y %I:%M %p")
        
        if include_timezone:
            # Get user's timezone offset from browser using streamlit
            # This is a placeholder - actual implementation would use JS
            return f"{formatted} UTC"
        else:
            return formatted
            
    except Exception:
        return str(dt)[:16]


def add_browser_timezone_js():
    """
    No-op stub kept for backward compatibility.
    Timezone is now selected via the sidebar selector (get_user_timezone).
    """
    pass


def get_user_timezone() -> str:
    """
    Return the user-selected IANA timezone from the sidebar selector.
    Renders a compact dropdown in st.sidebar the first time it is called.
    Defaults to 'UTC'.
    """
    _key = "_user_tz"
    # Common zones covering WC host countries + popular viewer zones
    _zones = [
        "UTC",
        "America/New_York",       # ET  (NYC, Boston, Miami, Atlanta)
        "America/Chicago",        # CT  (Dallas, Houston, KC)
        "America/Denver",         # MT
        "America/Los_Angeles",    # PT  (LA, SF, Seattle)
        "America/Vancouver",      # PT  (Vancouver host city)
        "America/Mexico_City",    # CT  (Guadalajara, Monterrey host cities)
        "America/Toronto",        # ET  (Toronto host city)
        "America/Sao_Paulo",      # BRT (Brazil fans)
        "America/Buenos_Aires",   # ART (Argentina fans)
        "Europe/London",          # BST
        "Europe/Paris",           # CEST
        "Africa/Casablanca",      # WET (Morocco fans)
        "Asia/Tokyo",             # JST
        "Asia/Seoul",             # KST
        "Australia/Sydney",       # AEST
    ]
    _labels = {
        "UTC": "🌐 UTC",
        "America/New_York": "🗽 Eastern (ET)",
        "America/Chicago": "🤠 Central (CT)",
        "America/Denver": "⛰️ Mountain (MT)",
        "America/Los_Angeles": "🌴 Pacific (PT)",
        "America/Vancouver": "🍁 Vancouver (PT)",
        "America/Mexico_City": "🇲🇽 Mexico City (CT)",
        "America/Toronto": "🇨🇦 Toronto (ET)",
        "America/Sao_Paulo": "🇧🇷 São Paulo (BRT)",
        "America/Buenos_Aires": "🇦🇷 Buenos Aires (ART)",
        "Europe/London": "🇬🇧 London (BST)",
        "Europe/Paris": "🇪🇺 Paris (CEST)",
        "Africa/Casablanca": "🇲🇦 Casablanca (WET)",
        "Asia/Tokyo": "🇯🇵 Tokyo (JST)",
        "Asia/Seoul": "🇰🇷 Seoul (KST)",
        "Australia/Sydney": "🇦🇺 Sydney (AEST)",
    }
    current = st.session_state.get(_key, "UTC")
    with st.sidebar:
        selected = st.selectbox(
            "🕒 Your Timezone",
            options=_zones,
            index=_zones.index(current) if current in _zones else 0,
            format_func=lambda z: _labels.get(z, z),
            key=_key,
        )
    return selected


def get_browser_timezone() -> Optional[str]:
    """Return the user-selected timezone from session state, or None for UTC."""
    tz = st.session_state.get("_user_tz")
    if tz and tz != "UTC":
        return tz
    # Also check the selectbox widget key directly
    tz2 = st.session_state.get("_user_tz")
    return tz2 if tz2 and tz2 != "UTC" else None


def format_match_time_local(dt: pd.Timestamp) -> str:
    """
    Format a UTC timestamp in the browser's local timezone when available,
    falling back to UTC.  Returns e.g. "06/14 3:00 PM EDT" or "06/14 7:00 PM UTC".
    """
    if pd.isna(dt):
        return "TBD"
    try:
        if hasattr(dt, "to_pydatetime"):
            dt = dt.to_pydatetime()
        tz_name = get_browser_timezone()
        if tz_name:
            import zoneinfo
            local_tz = zoneinfo.ZoneInfo(tz_name)
            local_dt = dt.astimezone(local_tz)
            tz_abbr = local_dt.strftime("%Z")
            time_str = local_dt.strftime("%m/%d %I:%M %p ").lstrip("0") + tz_abbr
            return time_str
        # Fallback: UTC
        return dt.strftime("%m/%d %I:%M %p UTC").lstrip("0")
    except Exception:
        try:
            return dt.strftime("%m/%d %I:%M %p UTC")
        except Exception:
            return "TBD"


def format_match_time_friendly(dt: pd.Timestamp) -> str:
    """
    Format match time in a friendly, compact format for cards/tables.
    
    Examples:
        "Today 3:00 PM"
        "Tomorrow 7:00 PM"
        "Jun 11, 3:00 PM"
    """
    if pd.isna(dt):
        return "Time TBD"
    
    try:
        if hasattr(dt, 'to_pydatetime'):
            dt = dt.to_pydatetime()
        
        now = datetime.now(timezone.utc)
        diff_days = (dt.date() - now.date()).days
        
        time_str = dt.strftime("%I:%M %p").lstrip("0")  # Remove leading zero
        
        if diff_days == 0:
            return f"Today {time_str}"
        elif diff_days == 1:
            return f"Tomorrow {time_str}"
        elif diff_days < 7:
            weekday = dt.strftime("%A")
            return f"{weekday} {time_str}"
        else:
            date_str = dt.strftime("%b %d")
            return f"{date_str}, {time_str}"
    except Exception:
        return format_datetime_local(dt, include_timezone=False)
