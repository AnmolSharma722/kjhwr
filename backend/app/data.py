from functools import lru_cache
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"   # works locally, in Docker and on Vercel


def _read(name: str, time_cols: list[str]) -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / name)                        # read the compressed CSV
    for c in time_cols:
        df[c] = pd.to_datetime(df[c], utc=True)              # make timestamps timezone-aware (UTC)
    return df


@lru_cache(maxsize=1)                                        # load once, keep in memory: fast API responses
def load_actuals() -> pd.DataFrame:
    return _read("actuals.csv.gz", ["startTime"])


@lru_cache(maxsize=1)
def load_forecasts() -> pd.DataFrame:
    return _read("forecasts.csv.gz", ["startTime", "publishTime"])
