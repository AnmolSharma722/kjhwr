import {
  ResponsiveContainer, ComposedChart, LineChart, BarChart, Line, Bar, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ReferenceLine,
} from "recharts";

const C = { actual: "#38bdf8", forecast: "#f59e0b", good: "#34d399", bad: "#f87171", grid: "#1e293b", text: "#94a3b8" };
const hhmm = (t) => new Date(t).toISOString().slice(11, 16);     // ISO string -> "HH:mm" (UTC)
const tip = { contentStyle: { background: "#0b1220", border: "1px solid #1e293b", borderRadius: 10 } };

// Small wrapper so every chart shares height, grid and axis styling
function Frame({ children, height = 300 }) {
  return <ResponsiveContainer width="100%" height={height}>{children}</ResponsiveContainer>;
}
const axis = { stroke: C.text, fontSize: 12, tickLine: false };

export function ForecastChart({ points }) {
  return (
    <Frame height={340}>
      <ComposedChart data={points}>
        <defs>
          <linearGradient id="gA" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={C.actual} stopOpacity={0.4} />
            <stop offset="100%" stopColor={C.actual} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={C.grid} vertical={false} />
        <XAxis dataKey="t" tickFormatter={hhmm} {...axis} minTickGap={30} />
        <YAxis {...axis} unit=" MW" width={80} />
        <Tooltip {...tip} labelFormatter={hhmm} formatter={(v) => `${v.toLocaleString()} MW`} />
        <Legend />
        <Area dataKey="actual" name="Actual (FUELHH)" stroke={C.actual} fill="url(#gA)" strokeWidth={2} dot={false} />
        <Line dataKey="forecast" name="Forecast at decision time (WINDFOR)" stroke={C.forecast}
              strokeWidth={2.5} dot={false} />
      </ComposedChart>
    </Frame>
  );
}

export function DailyChart({ data }) {
  return (
    <Frame>
      <BarChart data={data}>
        <CartesianGrid stroke={C.grid} vertical={false} />
        <XAxis dataKey="date" tickFormatter={(d) => d.slice(8)} {...axis} />
        <YAxis {...axis} width={60} />
        <Tooltip {...tip} formatter={(v) => `${v} MW`} />
        <Bar dataKey="mae" name="MAE (MW)" fill={C.forecast} radius={[4, 4, 0, 0]} />
      </BarChart>
    </Frame>
  );
}

export function HourlyChart({ data }) {
  return (
    <Frame>
      <ComposedChart data={data}>
        <CartesianGrid stroke={C.grid} vertical={false} />
        <XAxis dataKey="hour" {...axis} />
        <YAxis {...axis} width={60} />
        <Tooltip {...tip} formatter={(v) => `${v} MW`} />
        <Legend />
        <ReferenceLine y={0} stroke={C.text} />
        <Bar dataKey="mae" name="MAE" fill={C.forecast} radius={[4, 4, 0, 0]} />
        <Line dataKey="bias" name="Bias" stroke={C.actual} strokeWidth={2} dot={false} />
      </ComposedChart>
    </Frame>
  );
}

export function HorizonChart({ data }) {
  return (
    <Frame>
      <LineChart data={data}>
        <CartesianGrid stroke={C.grid} vertical={false} />
        <XAxis dataKey="horizon" {...axis} />
        <YAxis {...axis} width={60} />
        <Tooltip {...tip} formatter={(v) => `${v} MW`} />
        <Legend />
        <Line dataKey="mae" name="MAE" stroke={C.forecast} strokeWidth={2.5} />
        <Line dataKey="bias" name="Bias" stroke={C.actual} strokeWidth={2} />
      </LineChart>
    </Frame>
  );
}

export function HistChart({ data }) {
  return (
    <Frame>
      <BarChart data={data}>
        <CartesianGrid stroke={C.grid} vertical={false} />
        <XAxis dataKey="error" {...axis} />
        <YAxis {...axis} width={50} />
        <Tooltip {...tip} />
        <ReferenceLine x={0} stroke={C.text} />
        <Bar dataKey="count" name="Half-hours" fill={C.actual} radius={[3, 3, 0, 0]} />
      </BarChart>
    </Frame>
  );
}

export function ProcurementChart({ points }) {
  return (
    <Frame height={320}>
      <LineChart data={points}>
        <CartesianGrid stroke={C.grid} vertical={false} />
        <XAxis dataKey="t" tickFormatter={hhmm} {...axis} minTickGap={30} />
        <YAxis {...axis} unit=" MW" width={80} />
        <Tooltip {...tip} labelFormatter={hhmm} formatter={(v) => `${v.toLocaleString()} MW`} />
        <Legend />
        <Line dataKey="plan" name="Buy (no buffer)" stroke={C.forecast} strokeWidth={2} dot={false} />
        <Line dataKey="recommended" name="Buy (with P90 buffer)" stroke={C.good} strokeWidth={2.5} dot={false} />
        <Line dataKey="needed" name="Actually needed" stroke={C.bad} strokeWidth={2} strokeDasharray="5 4" dot={false} />
      </LineChart>
    </Frame>
  );
}
