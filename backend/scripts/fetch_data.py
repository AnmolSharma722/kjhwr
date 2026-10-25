"""Download January-2026 wind actuals + forecasts from Elexon into compressed CSVs."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pandas as pd

BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets"   # Elexon's public API root
OUT = Path(__file__).resolve().parent.parent / "data"      # backend/data folder
OUT.mkdir(exist_ok=True)                                   # create it if missing

START = datetime(2026, 1, 1, tzinfo=timezone.utc)          # first delivery day we care about
END = datetime(2026, 2, 1, tzinfo=timezone.utc)            # exclusive end (1 Feb 00:00)
MAX_HORIZON_H = 60                                         # keep forecasts at most 60h ahead (enough for D-1 decisions)


def get_json(client: httpx.Client, dataset: str, params: dict) -> list[dict]:
    """Call <dataset>/stream and return the JSON list."""
    r = client.get(f"{BASE}/{dataset}/stream", params=params, timeout=120)
    r.raise_for_status()                                   # stop loudly on HTTP errors
    return r.json()


def fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%MZ")                  # format Elexon accepts, e.g. 2026-01-01T00:00Z


def fetch_actuals(client) -> pd.DataFrame:
    rows, day = [], START
    while day < END:                                       # walk through January in 5-day windows
        nxt = min(day + timedelta(days=5), END)            # APIs limit the date range, so we chunk
        rows += get_json(client, "FUELHH", {
            "settlementDateFrom": day.strftime("%Y-%m-%d"),
            "settlementDateTo": (nxt - timedelta(days=1)).strftime("%Y-%m-%d"),
            "fuelType": "WIND",                            # only wind, as the task says
        })
        day = nxt
    df = pd.DataFrame(rows)
    print("ACTUALS sample row:", rows[0] if rows else "NO DATA")   # check field names here!
    df = df[df["fuelType"] == "WIND"]                      # double-check the filter
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df = df[["startTime", "generation"]].drop_duplicates("startTime").sort_values("startTime")
    return df[(df["startTime"] >= START) & (df["startTime"] < END)]


def fetch_forecasts(client) -> pd.DataFrame:
    rows, day = [], START - timedelta(days=2)              # forecasts for 1 Jan were published on 30/31 Dec
    while day < END:
        nxt = min(day + timedelta(days=2), END)            # small windows: lots of rows per day
        rows += get_json(client, "WINDFOR", {
            "publishDateTimeFrom": fmt(day),
            "publishDateTimeTo": fmt(nxt),
        })
        day = nxt
    df = pd.DataFrame(rows)
    print("FORECAST sample row:", rows[0] if rows else "NO DATA")
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)
    df = df[["startTime", "publishTime", "generation"]]
    horizon = (df["startTime"] - df["publishTime"]).dt.total_seconds() / 3600   # hours between publishing and target
    df = df[(horizon > 0) & (horizon <= MAX_HORIZON_H)]    # only genuine forecasts, not too far ahead
    df = df[(df["startTime"] >= START) & (df["startTime"] < END)]   # targets in January only
    return df.drop_duplicates(["startTime", "publishTime"]).sort_values(["startTime", "publishTime"])


if __name__ == "__main__":
    with httpx.Client() as c:
        a, f = fetch_actuals(c), fetch_forecasts(c)
    a.to_csv(OUT / "actuals.csv.gz", index=False)          # gzip keeps files small enough for git
    f.to_csv(OUT / "forecasts.csv.gz", index=False)
    print(f"actuals: {len(a)} rows | forecasts: {len(f)} rows")
