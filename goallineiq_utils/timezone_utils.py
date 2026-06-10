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
    Add JavaScript component to detect and use browser timezone.
    Call this once in the app initialization.
    """
    st.markdown(
        """
        <script>
        // Detect browser timezone and store in localStorage
        const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        localStorage.setItem('userTimezone', userTimezone);
        
        // Function to convert UTC to local time
        function convertUTCToLocal(utcDateString) {
            const date = new Date(utcDateString);
            return date.toLocaleString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
                hour: 'numeric',
                minute: '2-digit',
                hour12: true,
                timeZoneName: 'short'
            });
        }
        </script>
        """,
        unsafe_allow_html=True
    )


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
