from datetime import date
from functools import lru_cache

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import analysis as an
from .data import load_actuals, load_forecasts

app = FastAPI(title="Wind Forecast Decision Support API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])  # lets the React site call us

MIN_DAY, MAX_DAY = date(2026, 1, 1), date(2026, 1, 31)       # scope required by the task


@lru_cache(maxsize=8)
def decision_frame(cutoff_hour: int) -> pd.DataFrame:
    """decision-time forecast + actuals + errors, cached per cutoff hour."""
    return an.join_actuals(an.decision_forecast(load_forecasts(), cutoff_hour), load_actuals())


def check_day(d: date) -> None:
    if not MIN_DAY <= d <= MAX_DAY:                          # reject dates outside January 2026
        raise HTTPException(404, "Delivery day must be within January 2026")


@app.get("/api/health")
def health():
    return {"status": "ok"}                                  # used by deploy platforms / monitoring


@app.get("/api/meta")
def meta():
    return {"min_day": MIN_DAY.isoformat(), "max_day": MAX_DAY.isoformat(), "default_cutoff_hour": 9,
            "actual_rows": len(load_actuals()), "forecast_rows": len(load_forecasts())}


@app.get("/api/series")
def series(day: date, cutoff_hour: int = Query(9, ge=0, le=23)):
    """Q1: what forecast did the client have at decision time for this delivery day?"""
    check_day(day)
    df = decision_frame(cutoff_hour)
    d = df[df["startTime"].dt.date == day]
    if d.empty:
        raise HTTPException(404, "No data for that day")
    decision_time = pd.Timestamp(day, tz="UTC") - pd.Timedelta(days=1) + pd.Timedelta(hours=cutoff_hour)
    return {
        "day": day.isoformat(),
        "decision_time": decision_time.isoformat(),
        "latest_publish_used": d["publishTime"].max().isoformat(),
        "summary": an.metrics(d),
        "points": [{"t": r.startTime.isoformat(), "forecast": round(r.forecast), "actual": round(r.actual),
                    "published": r.publishTime.isoformat()} for r in d.itertuples()],
    }


@app.get("/api/metrics")
def get_metrics(start: date = MIN_DAY, end: date = MAX_DAY, cutoff_hour: int = Query(9, ge=0, le=23)):
    """Q2: how accurate were the decision-time forecasts?"""
    check_day(start); check_day(end)
    df = decision_frame(cutoff_hour)
    d = df["startTime"].dt.date
    sel = df[(d >= start) & (d <= end)]
    if sel.empty:
        raise HTTPException(404, "No data in range")
    return {"overall": an.metrics(sel), "daily": an.daily(sel), "hourly": an.by_hour(sel),
            "histogram": an.histogram(sel),
            "horizon": an.horizon_profile(load_forecasts(), load_actuals(), start, end)}


@app.get("/api/procurement")
def get_procurement(day: date, demand_mw: float = Query(25000, gt=0, le=60000),
                    cutoff_hour: int = Query(9, ge=0, le=23)):
    check_day(day)
    return an.procurement(decision_frame(cutoff_hour), day, demand_mw)
