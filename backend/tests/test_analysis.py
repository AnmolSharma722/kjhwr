import pandas as pd
from app import analysis as an


def ts(s):
    return pd.Timestamp(s, tz="UTC")


def test_decision_forecast_ignores_late_publishes_and_takes_latest_valid():
    fc = pd.DataFrame({
        "startTime": [ts("2026-01-15 12:00")] * 3,
        "publishTime": [ts("2026-01-14 06:00"), ts("2026-01-14 08:00"), ts("2026-01-14 10:00")],  # 10:00 is after 09:00 cutoff
        "generation": [100, 200, 300],
    })
    out = an.decision_forecast(fc, cutoff_hour=9)
    assert len(out) == 1
    assert out.iloc[0]["forecast"] == 200                    # 08:00 version, not the late 10:00 one


def test_metrics_values():
    df = pd.DataFrame({"forecast": [110, 90], "actual": [100, 100]})
    df["error"] = df["forecast"] - df["actual"]
    df["abs_error"] = df["error"].abs()
    m = an.metrics(df)
    assert m["mae"] == 10.0 and m["bias"] == 0.0 and m["rmse"] == 10.0


def test_procurement_buffer_reduces_shortfall():
    times = pd.date_range("2026-01-01", periods=48 * 5, freq="30min", tz="UTC")
    df = pd.DataFrame({"startTime": times, "forecast": 1000.0, "actual": 800.0})   # always over-forecasts by 200
    df["error"], df["abs_error"] = 200.0, 200.0
    r = an.procurement(df, times[-1].date(), demand_mw=5000)
    assert r["buffer_mw"] == 200.0
    assert r["shortfall_mwh_with_buffer"] < r["shortfall_mwh_no_buffer"]
