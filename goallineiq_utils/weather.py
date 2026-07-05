"""
Weather data integration for GoallineIQ using Open-Meteo API.
Free API (no key required) for historical and forecast weather data.
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict
import streamlit as st

# Open-Meteo API endpoints (free, no API key required)
HISTORICAL_WEATHER_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

# Venue coordinates for World Cup 2026 cities
VENUE_COORDINATES = {
    # USA venues
    "New York": (40.7128, -74.0060),
    "New York City": (40.7128, -74.0060),
    "Miami": (25.7617, -80.1918),
    "Miami Gardens": (25.7617, -80.1918),
    "Los Angeles": (34.0522, -118.2437),
    "Inglewood": (34.0522, -118.2437),
    "Dallas": (32.7767, -96.7970),
    "Arlington": (32.7767, -96.7970),
    "Kansas City": (39.0997, -94.5786),
    "Houston": (29.7604, -95.3698),
    "Atlanta": (33.7490, -84.3880),
    "Philadelphia": (39.9526, -75.1652),
    "Seattle": (47.6062, -122.3321),
    "San Francisco": (37.7749, -122.4194),
    "Santa Clara": (37.7749, -122.4194),
    "Boston": (42.3601, -71.0589),
    "Foxborough": (42.3601, -71.0589),
    
    # Mexico venues
    "Mexico City": (19.4326, -99.1332),
    "Guadalajara": (20.6597, -103.3496),
    "Guadalajara (Zapopan)": (20.6597, -103.3496),
    "Monterrey": (25.6866, -100.3161),
    
    # Canada venues
    "Toronto": (43.6532, -79.3832),
    "Vancouver": (49.2827, -123.1207),
    
    # Historical World Cup venues (for past data)
    "Doha": (25.2854, 51.5310),
    "Al Rayyan": (25.2919, 51.4244),
    "Al Wakrah": (25.1714, 51.6078),
    "Lusail": (25.4285, 51.5265),
    "Moscow": (55.7558, 37.6173),
    "Saint Petersburg": (59.9343, 30.3351),
    "Kazan": (55.8304, 49.0661),
    "Sochi": (43.6028, 39.7342),
    "Rio de Janeiro": (-22.9068, -43.1729),
    "São Paulo": (-23.5505, -46.6333),
    "Brasilia": (-15.8267, -47.9218),
    "Johannesburg": (-26.2041, 28.0473),
    "Cape Town": (-33.9249, 18.4241),
    "Durban": (-29.8587, 31.0218),
    "Pretoria": (-25.7479, 28.2293),
}

@st.cache_data(ttl=86400)  # Cache for 24 hours
def get_weather_for_match(city: str, date: str, hours_before: int = 3) -> Optional[Dict]:
    """
    Fetch weather data for a match location and time.
    
    Args:
        city: City name (must be in VENUE_COORDINATES)
        date: Match date/time string (e.g., "2026-06-11 15:00:00+00:00")
        hours_before: Hours before match to get weather (default 3h)
    
    Returns:
        Dict with weather data or None if unavailable
    """
    if not city:
        return None
        
    # Standardize city lookup
    lat, lon = None, None
    if city in VENUE_COORDINATES:
        lat, lon = VENUE_COORDINATES[city]
    else:
        # Try fuzzy match (if city name is inside a larger venue string)
        for v_city, coords in VENUE_COORDINATES.items():
            if v_city.lower() in city.lower() or city.lower() in v_city.lower():
                lat, lon = coords
                break
    
    if lat is None:
        return None
    
    try:
        # Parse match date
        match_dt = pd.to_datetime(date)
        if match_dt.tzinfo is None:
            # Make naive datetime UTC-aware
            match_dt = match_dt.tz_localize('UTC')
        
        weather_dt = match_dt - timedelta(hours=hours_before)
        date_str = weather_dt.strftime("%Y-%m-%d")
        
        # Determine if we need historical or forecast data
        today = datetime.now()
        match_naive = match_dt.tz_localize(None) if match_dt.tzinfo else match_dt
        days_from_now = (match_naive - today).days
        
        if days_from_now < -5:
            # Historical data (more than 5 days in the past)
            url = HISTORICAL_WEATHER_URL
            params = {
                "latitude": lat,
                "longitude": lon,
                "start_date": date_str,
                "end_date": date_str,
                "hourly": "temperature_2m,precipitation,windspeed_10m,weathercode",
                "timezone": "UTC"
            }
        elif days_from_now <= 7:
            # Forecast data (up to 7 days in the future)
            url = FORECAST_WEATHER_URL
            params = {
                "latitude": lat,
                "longitude": lon,
                "hourly": "temperature_2m,precipitation,windspeed_10m,weathercode",
                "timezone": "UTC",
                "past_days": 5 if days_from_now < 0 else 0,
                "forecast_days": max(1, days_from_now + 1)
            }
        else:
            # Too far in the future for forecast
            return None
        
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        if "hourly" not in data:
            return None
        
        hourly = data["hourly"]
        times = pd.to_datetime(hourly["time"], utc=True)
        
        # Find closest hour to match time
        target_time = weather_dt
        if target_time.tzinfo is None:
            target_time = target_time.tz_localize('UTC')
        target_time = target_time.replace(minute=0, second=0, microsecond=0)
        time_diffs = abs(times - target_time)
        closest_idx = time_diffs.argmin()
        
        # Weather code descriptions (WMO standard)
        weather_codes = {
            0: "Clear", 1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast",
            45: "Foggy", 48: "Foggy", 51: "Light Drizzle", 53: "Drizzle",
            55: "Heavy Drizzle", 61: "Light Rain", 63: "Rain", 65: "Heavy Rain",
            71: "Light Snow", 73: "Snow", 75: "Heavy Snow", 95: "Thunderstorm"
        }
        
        weather_code = hourly["weathercode"][closest_idx]
        temp_c = hourly["temperature_2m"][closest_idx]
        temp_f = (temp_c * 9/5) + 32

        return {
            "temperature_c": round(temp_c, 1),
            "temperature_f": round(temp_f, 1),
            "precipitation_mm": round(hourly["precipitation"][closest_idx], 1),
            "windspeed_kmh": round(hourly["windspeed_10m"][closest_idx], 1),
            "weather_code": weather_code,
            "weather_desc": weather_codes.get(weather_code, "Unknown"),
            "conditions": "Rainy" if weather_code >= 51 else "Clear"
        }
        
    except Exception as e:
        # Silently fail for weather data (non-critical)
        return None


@st.cache_data(ttl=3600)
def add_weather_to_matches(matches_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add weather data columns to matches dataframe.
    
    Args:
        matches_df: DataFrame with 'city' and 'date' columns
    
    Returns:
        DataFrame with added weather columns
    """
    if matches_df is None or matches_df.empty:
        return matches_df
    
    # Initialize weather columns
    matches_df["temperature_c"] = None
    matches_df["temperature_f"] = None
    matches_df["precipitation_mm"] = None
    matches_df["windspeed_kmh"] = None
    matches_df["weather_conditions"] = None
    
    # Fetch weather for each match (limit to avoid API overload)
    for idx, row in matches_df.head(50).iterrows():
        city = row.get("city", "")
        date = row.get("date")
        
        if not city or pd.isna(date):
            continue
        
        weather = get_weather_for_match(city, str(date))
        
        if weather:
            matches_df.at[idx, "temperature_c"] = weather["temperature_c"]
            matches_df.at[idx, "temperature_f"] = weather["temperature_f"]
            matches_df.at[idx, "precipitation_mm"] = weather["precipitation_mm"]
            matches_df.at[idx, "windspeed_kmh"] = weather["windspeed_kmh"]
            matches_df.at[idx, "weather_conditions"] = weather["weather_desc"]
    
    return matches_df


def analyze_weather_impact(matches_df: pd.DataFrame) -> Dict:
    """
    Analyze correlation between weather conditions and match outcomes.
    
    Args:
        matches_df: DataFrame with match results and weather data
    
    Returns:
        Dict with analysis results
    """
    if matches_df is None or matches_df.empty:
        return {}
    
    # Filter to completed matches with weather data
    completed = matches_df[
        (matches_df["home_goals"].notna()) &
        (matches_df["away_goals"].notna()) &
        (matches_df["temperature_c"].notna())
    ].copy()
    
    if completed.empty:
        return {"sample_size": 0}
    
    # Calculate match outcomes
    completed["total_goals"] = completed["home_goals"] + completed["away_goals"]
    completed["home_win"] = (completed["home_goals"] > completed["away_goals"]).astype(int)
    completed["draw"] = (completed["home_goals"] == completed["away_goals"]).astype(int)
    
    # Categorize weather
    completed["is_cold"] = completed["temperature_c"] < 10
    completed["is_hot"] = completed["temperature_c"] > 30
    completed["is_rainy"] = completed["precipitation_mm"] > 1.0
    completed["is_windy"] = completed["windspeed_kmh"] > 30
    
    analysis = {
        "sample_size": len(completed),
        "avg_goals_all": completed["total_goals"].mean(),
        "avg_goals_rainy": completed[completed["is_rainy"]]["total_goals"].mean() if completed["is_rainy"].any() else None,
        "avg_goals_clear": completed[~completed["is_rainy"]]["total_goals"].mean() if (~completed["is_rainy"]).any() else None,
        "avg_goals_cold": completed[completed["is_cold"]]["total_goals"].mean() if completed["is_cold"].any() else None,
        "avg_goals_hot": completed[completed["is_hot"]]["total_goals"].mean() if completed["is_hot"].any() else None,
        "home_win_rate_all": completed["home_win"].mean(),
        "home_win_rate_rainy": completed[completed["is_rainy"]]["home_win"].mean() if completed["is_rainy"].any() else None,
        "rainy_match_count": completed["is_rainy"].sum(),
        "cold_match_count": completed["is_cold"].sum(),
        "hot_match_count": completed["is_hot"].sum(),
    }
    
    return analysis
