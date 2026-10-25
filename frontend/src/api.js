// Backend address: set VITE_API_URL at build time; falls back to local dev server
const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function get(path, params = {}) {
  const qs = new URLSearchParams(params).toString();       // {a:1,b:2} -> "a=1&b=2"
  const res = await fetch(`${BASE}${path}?${qs}`);
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`); // surface server errors
  return res.json();
}

export const api = {
  meta: () => get("/api/meta"),
  series: (day, cutoff) => get("/api/series", { day, cutoff_hour: cutoff }),
  metrics: (cutoff) => get("/api/metrics", { cutoff_hour: cutoff }),
  procurement: (day, demand, cutoff) =>
    get("/api/procurement", { day, demand_mw: demand, cutoff_hour: cutoff }),
};
