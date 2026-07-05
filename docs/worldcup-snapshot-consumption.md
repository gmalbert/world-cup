# World Cup Snapshot Consumption

This note describes how the Streamlit app can consume the nightly snapshot files in `data_files/nightly_snapshots/` instead of calling live APIs on every page load.

---

## Goal

Use the nightly GitHub Actions export as a stable read layer for the app when you want:

- fewer live API calls during user sessions
- predictable page performance
- a fallback when API quotas are exhausted
- reproducible data for demos, QA, and debugging

---

## Recommended Read Order

For each dataset the app should read in this order:

1. Latest local snapshot for the relevant dataset
2. Live API fetch if no snapshot exists or if a manual "refresh live" mode is enabled
3. Existing hard-coded or open-data fallback already present in the app

That gives you stable default behavior without removing the current live integrations.

---

## Suggested Helper Pattern

Add a small snapshot utility layer, for example in `utils/snapshots.py`, with helpers like:

- `get_latest_snapshot_dir()`
- `read_snapshot_csv(name: str)`
- `snapshot_exists(name: str)`

The implementation should:

- scan `data_files/nightly_snapshots/`
- pick the newest `YYYY-MM-DD` folder
- return an empty DataFrame if the file is missing

---

## Best Integration Points

These functions in `utils/api_client.py` are the cleanest places to add snapshot-first reads:

- `get_all_wc_matches()` → read `matches_all.csv`
- `get_upcoming_matches()` → read `upcoming_matches.csv`
- `get_current_standings()` → read `standings.csv`
- `get_historical_top_scorers()` → read `top_scorers.csv`

The practical pattern is:

1. Try snapshot data first
2. If snapshot is empty, fall back to the current live API logic
3. Keep the current `st.cache_data` decorators so repeated reads stay cheap

---

## Minimal Integration Example

```python
from pathlib import Path
import pandas as pd

SNAPSHOT_ROOT = Path("data_files/nightly_snapshots")


def read_latest_snapshot_csv(filename: str) -> pd.DataFrame:
    if not SNAPSHOT_ROOT.exists():
        return pd.DataFrame()

    dated_dirs = sorted(
        [path for path in SNAPSHOT_ROOT.iterdir() if path.is_dir()],
        reverse=True,
    )
    if not dated_dirs:
        return pd.DataFrame()

    target = dated_dirs[0] / filename
    if not target.exists():
        return pd.DataFrame()

    return pd.read_csv(target)
```

Then inside an existing accessor:

```python
snapshot_df = read_latest_snapshot_csv("standings.csv")
if not snapshot_df.empty:
    return snapshot_df
```

---

## Operational Modes

There are three sensible modes for the app:

### 1. Snapshot-first
- Best default for production
- Minimizes rate-limit exposure
- Keeps data fresh enough for daily analytics pages

### 2. Live-first
- Best for match-day or admin use
- Useful when you need current in-day standings or odds
- More fragile under quota pressure

### 3. Snapshot-only
- Best for demos, testing, and reproducible bug reports
- Avoids all external dependencies during a session

---

## Recommended Next Step

Do not rewrite every page separately. Add snapshot reads only in the shared data-access functions in `utils/api_client.py`, because all pages already depend on those helpers. That keeps the rollout small and reduces regression risk.