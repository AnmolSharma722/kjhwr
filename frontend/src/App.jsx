import { useEffect, useState } from "react";
import { api } from "./api";
import {
  ForecastChart, DailyChart, HourlyChart, HorizonChart, HistChart, ProcurementChart,
} from "./components/Charts";

const fmt = (n) => Number(n).toLocaleString(undefined, { maximumFractionDigits: 1 });

function Kpi({ label, value, unit, hint }) {            // one metric card
  return (
    <div className="card kpi">
      <span className="kpi-label">{label}</span>
      <span className="kpi-value">{value}<small> {unit}</small></span>
      <span className="kpi-hint">{hint}</span>
    </div>
  );
}

const Section = ({ title, sub, children }) => (        // titled card wrapper
  <section className="card">
    <h3>{title}</h3>
    <p className="sub">{sub}</p>
    {children}
  </section>
);

export default function App() {
  const [day, setDay] = useState("2026-01-15");        // delivery day being analysed
  const [cutoff, setCutoff] = useState(9);             // decision hour on D-1
  const [demand, setDemand] = useState(25000);         // flat demand scenario (MW)
  const [series, setSeries] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [proc, setProc] = useState(null);
  const [error, setError] = useState("");

  // Month-level metrics: refetch only when the cutoff hour changes
  useEffect(() => {
    api.metrics(cutoff).then(setMetrics).catch((e) => setError(e.message));
  }, [cutoff]);

  // Day-level data: refetch when day or cutoff changes
  useEffect(() => {
    setError("");
    api.series(day, cutoff).then(setSeries).catch((e) => setError(e.message));
  }, [day, cutoff]);

  // Procurement scenario: also reacts to the demand slider
  useEffect(() => {
    api.procurement(day, demand, cutoff).then(setProc).catch((e) => setError(e.message));
  }, [day, demand, cutoff]);

  const o = metrics?.overall;

  return (
    <div className="page">
      <header className="hero">
        <div>
          <span className="badge">UK Day-Ahead Market · January 2026</span>
          <h1>Wind Desk</h1>
          <p>What wind forecast did you have when you had to buy, and how far could it be off?</p>
        </div>
        <div className="controls card">
          <label>Delivery day
            <input type="date" min="2026-01-01" max="2026-01-31" value={day}
                   onChange={(e) => e.target.value && setDay(e.target.value)} />
          </label>
          <label>Decision time (D-1, UK)
            <select value={cutoff} onChange={(e) => setCutoff(Number(e.target.value))}>
              {[8, 9, 10, 11].map((h) => <option key={h} value={h}>{String(h).padStart(2, "0")}:00</option>)}
            </select>
          </label>
        </div>
      </header>

      {error && <div className="error">⚠ {error}</div>}
      {!metrics || !series ? <div className="loading">Loading data…</div> : (
        <>
          <div className="kpis">
            <Kpi label="Mean abs error" value={fmt(o.mae)} unit="MW" hint="average miss" />
            <Kpi label="Error vs wind" value={fmt(o.wmape)} unit="%" hint="weighted MAPE" />
            <Kpi label="Bias" value={fmt(o.bias)} unit="MW"
                 hint={o.bias > 0 ? "over-forecasts wind" : "under-forecasts wind"} />
            <Kpi label="P90 abs error" value={fmt(o.p90_abs)} unit="MW" hint="9 in 10 misses below" />
            <Kpi label="RMSE" value={fmt(o.rmse)} unit="MW" hint="penalises big misses" />
          </div>

          <Section title={`Forecast vs actual · ${day}`}
                   sub={`Decision made ${series.decision_time.slice(0, 16).replace("T", " ")} UTC. Latest forecast used was published ${series.latest_publish_used.slice(0, 16).replace("T", " ")} UTC. Day MAE: ${fmt(series.summary.mae)} MW.`}>
            <ForecastChart points={series.points} />
          </Section>

          <Section title="Procurement what-if"
                   sub="Buy = demand − forecast wind. The buffer is the P90 over-forecast error from earlier days only (no look-ahead).">
            <div className="slider">
              <label>Average demand: <b>{fmt(demand)} MW</b></label>
              <input type="range" min="15000" max="40000" step="500" value={demand}
                     onChange={(e) => setDemand(Number(e.target.value))} />
            </div>
            {proc && (
              <>
                <div className="kpis small">
                  <Kpi label="Buffer" value={fmt(proc.buffer_mw)} unit="MW" hint="extra to buy" />
                  <Kpi label="Plan" value={fmt(proc.plan_mwh)} unit="MWh" hint="no buffer" />
                  <Kpi label="Recommended" value={fmt(proc.recommended_mwh)} unit="MWh" hint="with buffer" />
                  <Kpi label="Uncovered (no buffer)" value={fmt(proc.shortfall_mwh_no_buffer)} unit="MWh" hint="risk if you buy plan" />
                  <Kpi label="Uncovered (buffer)" value={fmt(proc.shortfall_mwh_with_buffer)} unit="MWh" hint="risk with buffer" />
                </div>
                <ProcurementChart points={proc.points} />
              </>
            )}
          </Section>

          <div className="grid2">
            <Section title="Daily accuracy" sub="MAE per day of January (MW)"><DailyChart data={metrics.daily} /></Section>
            <Section title="Accuracy by hour of day" sub="MAE (bars) and bias (line)"><HourlyChart data={metrics.hourly} /></Section>
            <Section title="Error vs forecast horizon" sub="Does a fresher forecast help? (all published versions)"><HorizonChart data={metrics.horizon} /></Section>
            <Section title="Error distribution" sub="Forecast − actual, in MW. Right of 0 = over-forecast"><HistChart data={metrics.histogram} /></Section>
          </div>
        </>
      )}
      <footer>Data: Elexon BMRS (FUELHH actuals, WINDFOR forecasts). National level wind only.</footer>
    </div>
  );
}
