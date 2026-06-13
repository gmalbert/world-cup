"""
Load and normalize international match results from martj42/international_results.

This module augments the Elo training dataset with 150+ years of international
football matches (1872-2024), providing richer historical context and more stable
Elo ratings for World Cup prediction.

Schema from international_results repo:
- date: YYYY-MM-DD
- home_team: current team name (normalized)
- away_team: current team name (normalized)
- home_score: full-time score (excl. penalties)
- away_score: full-time score (excl. penalties)
- tournament: tournament name (e.g., "FIFA World Cup", "Friendly", etc.)
- city: match location
- country: country where match was played
- neutral: TRUE/FALSE if neutral venue
"""

import pandas as pd
from pathlib import Path
from typing import Optional


def load_international_results_csv() -> Optional[pd.DataFrame]:
    """
    Load international_results.csv from the submodule at external/international_results/.
    
    Returns:
        DataFrame with columns: date, home_team, away_team, home_score, away_score, tournament, ...
        Returns None if file not found.
    """
    submodule_path = Path(__file__).resolve().parent.parent / "external" / "international_results" / "results.csv"
    
    if not submodule_path.exists():
        return None
    
    try:
        df = pd.read_csv(submodule_path, encoding="utf-8")
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        return df
    except Exception as e:
        print(f"Error loading international_results CSV: {e}")
        return None


def normalize_team_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize team names to match current naming conventions used in BALLDONTLIE/openfootball data.
    
    This handles:
    - "USA" vs "United States"
    - "Côte d'Ivoire" vs "Ivory Coast"
    - Any other legacy names that differ from current team names.
    """
    # Common name mappings from international_results to current names
    name_map = {
        "United States": "USA",
        "Ivory Coast": "Côte d'Ivoire",
        "South Korea": "Korea Republic",
        "Republic of Ireland": "Ireland",
        "Northern Ireland": "Northern Ireland",
        "Czech Republic": "Czechia",
        "Bosnia-Herzegovina": "Bosnia & Herzegovina",
        "Bosnia & Herzegovina": "Bosnia & Herzegovina",
        "Bosnia-And-Herzegovina": "Bosnia & Herzegovina",
    }
    
    df = df.copy()
    df["home_team"] = df["home_team"].replace(name_map)
    df["away_team"] = df["away_team"].replace(name_map)
    
    return df


def filter_to_wc_era(df: pd.DataFrame, start_year: int = 1950) -> pd.DataFrame:
    """
    Filter international results to focus on matches from the World Cup era onwards.
    
    This reduces noise from early football history (1872-1949) and focuses on the
    era where modern football and the World Cup have been established.
    
    Args:
        df: DataFrame with "date" column
        start_year: Cutoff year (default 1950 for first post-WWII WC)
    
    Returns:
        Filtered DataFrame
    """
    df = df.copy()
    df["year"] = pd.to_datetime(df["date"]).dt.year
    return df[df["year"] >= start_year].drop(columns=["year"])


def merge_with_existing(
    international_df: pd.DataFrame,
    existing_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Merge international_results data with existing WC data, deduplicating.
    
    Args:
        international_df: DataFrame from international_results.csv (normalized)
        existing_df: DataFrame from openfootball/BALLDONTLIE (2010-2026 WC only)
    
    Returns:
        Combined DataFrame, with duplicates removed (prefer existing_df if conflict)
    """
    # Normalize column names in international_df
    intl = international_df.copy()
    intl = intl.rename(columns={"home_score": "home_goals", "away_score": "away_goals"})
    
    # Required columns for merging
    required_cols = ["date", "home_team", "away_team", "home_goals", "away_goals"]
    
    # Select only required cols from intl, then add any existing_df columns
    intl_base = intl[required_cols].copy() if all(c in intl.columns for c in required_cols) else intl.copy()
    existing = existing_df[[c for c in required_cols if c in existing_df.columns]].copy() if existing_df is not None else pd.DataFrame(columns=required_cols)
    
    # Add source marker
    intl_base["_source"] = "international_results"
    existing["_source"] = "existing"
    
    # Concatenate
    combined = pd.concat([existing, intl_base], ignore_index=True, sort=False)
    
    # Deduplicate: keep existing_df version if both have the same match
    combined = combined.drop_duplicates(
        subset=["date", "home_team", "away_team"],
        keep="first"  # existing comes first in concat, so "first" = existing
    )
    
    combined = combined.drop(columns=["_source"], errors="ignore")
    
    return combined.sort_values("date").reset_index(drop=True)


def enrich_training_dataset(existing_df: pd.DataFrame) -> pd.DataFrame:
    """
    Main entry point: load international_results and merge with existing WC data.
    
    Args:
        existing_df: Current training data (2010-2026 WC from openfootball/BALLDONTLIE)
    
    Returns:
        Combined DataFrame ready for Elo training (1950-2026, 10k+ matches)
    """
    intl = load_international_results_csv()
    
    if intl is None:
        return existing_df  # Fallback: return existing data if submodule not available
    
    # Normalize names and filter to WC era
    intl = normalize_team_names(intl)
    intl = filter_to_wc_era(intl, start_year=1950)
    
    # Ensure both DataFrames have consistent timezone handling for date column
    if "date" in intl.columns:
        intl["date"] = pd.to_datetime(intl["date"], errors="coerce", utc=True)
    if "date" in existing_df.columns:
        existing_df["date"] = pd.to_datetime(existing_df["date"], errors="coerce", utc=True)
    
    # Merge and return
    return merge_with_existing(intl, existing_df)
