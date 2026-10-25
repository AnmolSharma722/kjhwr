import numpy as np
import pandas as pd


def decision_forecast(fc: pd.DataFrame, cutoff_hour: int = 9) -> pd.DataFrame:
    """For each target half-hour, return the LATEST forecast the client could see at decision time.
    Decision time for delivery day D = (D-1) at cutoff_hour:00 UTC (= UK time in January)."""
    df = fc.copy()
    cutoff = (df["startTime"].dt.normalize()                 # midnight of the target's day (D)
              - pd.Timedelta(days=1)                         # go back to D-1
              + pd.Timedelta(hours=cutoff_hour))             # e.g. D-1 09:00
    df = df[df["publishTime"] <= cutoff]                     # drop forecasts published AFTER the deadline (no cheating!)
    df = df.sort_values("publishTime")                       # oldest -> newest
    df = df.groupby("startTime", as_index=False).last()      # per target time keep the newest one
    return df.rename(columns={"generation": "forecast"})[["startTime", "publishTime", "forecast"]]


def join_actuals(fc: pd.DataFrame, actuals: pd.DataFrame) -> pd.DataFrame:
    """Attach real generation. error = forecast - actual (positive = forecast too optimistic)."""
    a = actuals.rename(columns={"generation": "actual"})[["startTime", "actual"]]
    out = fc.merge(a, on="startTime", how="inner")           # keep only times where both exist
    out["error"] = out["forecast"] - out["actual"]
    out["abs_error"] = out["error"].abs()
    return out


def metrics(df: pd.DataFrame) -> dict:
    """Headline accuracy numbers."""
    if df.empty:
        return {"n": 0}
    e, ae = df["error"], df["abs_error"]
    return {
        "n": int(len(df)),
        "mae": round(float(ae.mean()), 1),                              # average miss in MW
        "rmse": round(float(np.sqrt((e ** 2).mean())), 1),              # punishes big misses more
        "bias": round(float(e.mean()), 1),                              # >0 = systematically over-forecasts
        "wmape": round(float(ae.sum() / df["actual"].sum() * 100), 2),  # error as % of total wind
        "p50_abs": round(float(ae.quantile(0.5)), 1),
        "p90_abs": round(float(ae.quantile(0.9)), 1),                   # "9 times out of 10 the miss is below this"
        "max_abs": round(float(ae.max()), 1),
        "mean_actual": round(float(df["actual"].mean()), 1),
    }


def by_hour(df: pd.DataFrame) -> list[dict]:
    g = df.groupby(df["startTime"].dt.hour).agg(mae=("abs_error", "mean"), bias=("error", "mean"))
    return [{"hour": int(h), "mae": round(r.mae, 1), "bias": round(r.bias, 1)} for h, r in g.iterrows()]


def daily(df: pd.DataFrame) -> list[dict]:
    g = df.groupby(df["startTime"].dt.strftime("%Y-%m-%d")).agg(
        mae=("abs_error", "mean"), bias=("error", "mean"), actual=("actual", "mean"))
    return [{"date": d, "mae": round(r.mae, 1), "bias": round(r.bias, 1), "actual": round(r.actual, 1)}
            for d, r in g.iterrows()]


def histogram(df: pd.DataFrame, bins: int = 24) -> list[dict]:
    counts, edges = np.histogram(df["error"], bins=bins)     # how often each size of error happened
    return [{"error": int((edges[i] + edges[i + 1]) / 2), "count": int(c)} for i, c in enumerate(counts)]


def horizon_profile(fc: pd.DataFrame, actuals: pd.DataFrame, start, end) -> list[dict]:
    """Does accuracy improve as the forecast gets closer to delivery? Uses ALL forecasts, not only decision-time ones."""
    df = join_actuals(fc.rename(columns={"generation": "forecast"}), actuals)
    d = df["startTime"].dt.date
    df = df[(d >= start) & (d <= end)].copy()
    df["horizon"] = (df["startTime"] - df["publishTime"]).dt.total_seconds() / 3600   # hours ahead
    df["bucket"] = (df["horizon"] // 6 * 6).astype(int)                                # 0-6h, 6-12h, ...
    g = df.groupby("bucket").agg(mae=("abs_error", "mean"), bias=("error", "mean"), n=("error", "size"))
    return [{"horizon": f"{b}-{b + 6}h", "mae": round(r.mae, 1), "bias": round(r.bias, 1)} for b, r in g.iterrows()]


def procurement(df: pd.DataFrame, day, demand_mw: float, q: float = 0.9) -> dict:
    """Backtest of the buying decision for one delivery day with a flat demand.
    The safety buffer uses only errors from EARLIER days (no look-ahead), like a real client would."""
    d = df["startTime"].dt.date
    today, prior = df[d == day], df[d < day]
    hist = prior if prior["startTime"].dt.date.nunique() >= 3 else df      # need some history; else fall back
    buffer = max(float(hist["error"].quantile(q)), 0.0)                    # "wind could be this much lower than forecast"
    step_h = today["startTime"].diff().dt.total_seconds().median() / 3600  # period length in hours (0.5)

    t = today.copy()
    t["plan"] = (demand_mw - t["forecast"]).clip(lower=0)                  # buy = demand - forecast wind
    t["recommended"] = (demand_mw - t["forecast"] + buffer).clip(lower=0)  # same, plus safety buffer
    t["needed"] = (demand_mw - t["actual"]).clip(lower=0)                  # what they REALLY needed
    short_plain = (t["needed"] - t["plan"]).clip(lower=0).sum() * step_h   # MWh left uncovered, no buffer
    short_buf = (t["needed"] - t["recommended"]).clip(lower=0).sum() * step_h
    return {
        "buffer_mw": round(buffer, 1),
        "plan_mwh": round(float(t["plan"].sum() * step_h), 1),
        "recommended_mwh": round(float(t["recommended"].sum() * step_h), 1),
        "needed_mwh": round(float(t["needed"].sum() * step_h), 1),
        "shortfall_mwh_no_buffer": round(float(short_plain), 1),
        "shortfall_mwh_with_buffer": round(float(short_buf), 1),
        "points": [{"t": r.startTime.isoformat(), "plan": round(r.plan), "recommended": round(r.recommended),
                    "needed": round(r.needed)} for r in t.itertuples()],
    }
