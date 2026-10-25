import { lazy, Suspense, useEffect, useState } from "react";

const WindChart = lazy(() => import("./WindChart.jsx"));

const INITIAL_QUERY = { decision_date: "2026-01-10", decision_time: "09:00" };
const METRICS = [
  { key: "maeMW", label: "Mean absolute error", short: "MAE", note: "Average size of the forecast error." },
  { key: "rmseMW", label: "Root mean squared error", short: "RMSE", note: "Gives larger forecast misses more weight." },
  { key: "biasMW", label: "Forecast bias", short: "BIAS", note: "Positive means wind was overforecast on average." },
];
const number = (value, signed = false) => value == null ? "—" : value.toLocaleString("en-GB", {
  maximumFractionDigits: 0, signDisplay: signed ? "exceptZero" : "auto",
});
const day = (value) => new Date(value).toLocaleDateString("en-GB", {
  day: "numeric", month: "long", year: "numeric", timeZone: "Europe/London",
});
const snapshot = (value) => new Date(value).toLocaleString("en-GB", {
  day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", timeZone: "Europe/London",
});

export default function App() {
  const [query, setQuery] = useState(INITIAL_QUERY);
  const [request, setRequest] = useState({ data: null, error: "", loading: true });

  useEffect(() => {
    const controller = new AbortController();
    setRequest({ data: null, error: "", loading: true });
    async function load() {
      let message = "Wind data couldn't be loaded. Please try again.";
      try {
        const response = await fetch(`/api/day-ahead?${new URLSearchParams(query)}`, {
          signal: controller.signal,
        });
        const data = await response.json();
        if (!response.ok) {
          message = typeof data.detail === "string" ? data.detail : "Choose a January 2026 date and a valid time.";
          throw new Error(message);
        }
        if (!controller.signal.aborted) setRequest({ data, error: "", loading: false });
      } catch {
        if (!controller.signal.aborted) setRequest({ data: null, error: message, loading: false });
      }
    }
    load();
    return () => controller.abort();
  }, [query]);

  const data = request.data;
  const latestPublication = data?.comparison.length
    ? Math.max(...data.comparison.map((row) => Date.parse(row.publishTime))) : null;

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Winddesk home">
          <svg viewBox="0 0 32 32" width="32" height="32" fill="none" aria-hidden="true">
            <path d="M4 11h17a4 4 0 1 0-4-4M4 17h24M4 23h13a4 4 0 1 1-4 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          Winddesk<span>GB WIND INTELLIGENCE</span>
        </a>
        <span className="replay-badge"><span className="status-dot" />Historical replay · January 2026</span>
      </header>

      <main>
        <section className="intro">
          <p className="eyebrow">THE DAY-AHEAD DESK</p>
          <h1>A clearer view of<br />tomorrow’s wind.</h1>
          <p>See the forecast available at your purchasing decision.<br className="desktop-break" /> Understand how it performed when delivery arrived.</p>
        </section>

        <form className="decision-controls" onSubmit={(event) => {
          event.preventDefault();
          if (!request.loading) setQuery(Object.fromEntries(new FormData(event.currentTarget)));
        }}>
          <div className="field">
            <label htmlFor="decision-date">Decision date</label>
            <input id="decision-date" name="decision_date" type="date" required min="2026-01-01" max="2026-01-31"
              defaultValue={INITIAL_QUERY.decision_date} />
          </div>
          <div className="field">
            <label htmlFor="decision-time">Decision time <span>UK / UTC</span></label>
            <input id="decision-time" name="decision_time" type="time" required step="60"
              defaultValue={INITIAL_QUERY.decision_time} />
          </div>
          <button className="primary-button" disabled={request.loading}>
            {request.loading ? "Loading outlook…" : "Load outlook"}<span aria-hidden="true">↗</span>
          </button>
          <p className="control-note">Only forecasts published at or before your decision are included.</p>
        </form>

        {request.loading && <section className="state-panel" role="status">
          <span className="spinner" /><h2>Preparing your decision snapshot</h2>
          <p>Loading Elexon forecasts and matching wind generation.</p>
        </section>}
        {request.error && <section className="state-panel error-panel" role="alert">
          <p className="eyebrow">DATA UNAVAILABLE</p><h2>We couldn’t load this outlook.</h2>
          <p>{request.error}</p>
          <button className="secondary-button" onClick={() => setQuery({ ...query })}>Try again</button>
        </section>}

        {data && <>
          <section className="snapshot-context" aria-label="Applied decision snapshot">
            <div><p className="eyebrow">DELIVERY DAY</p><h2>{day(data.deliveryDate)}</h2></div>
            <div><p>Decision cutoff</p><strong>{snapshot(data.decisionTime)} UK</strong></div>
            <div><p>Latest forecast publication</p><strong>{latestPublication == null ? "—" : `${snapshot(latestPublication)} UK`}</strong></div>
          </section>

          <section className="chart-card" aria-labelledby="chart-title">
            <div className="chart-heading">
              <div><p className="eyebrow">DELIVERY OUTLOOK</p><h2 id="chart-title">Forecast meets reality</h2></div>
              <div className="legend"><span><i className="swatch forecast" />Forecast</span><span><i className="swatch actual" />Actual</span></div>
            </div>
            <div className="chart-meta"><span>Wind generation · GW</span><span>Delivery time · UK / UTC</span></div>
            {data.metrics.forecastCount === 0
              ? <div className="empty-chart"><h3>No forecast samples available</h3><p>No forecasts were found in the 48-hour search window for this delivery day.<br />Try another decision date or time.</p></div>
              : <Suspense fallback={<div className="empty-chart" role="status">Loading chart…</div>}><WindChart data={data} /></Suspense>}
            <div className="coverage">
              <span><span className={`status-dot ${data.metrics.forecastCount < data.expectedForecastCount ? "partial" : ""}`} />
                {data.metrics.forecastCount} of {data.expectedForecastCount} forecast timestamps</span>
              <span>{data.metrics.matchedCount} matched actuals · Missing values are excluded</span>
            </div>
          </section>

          <section className="accuracy-section" aria-labelledby="accuracy-title">
            <div className="section-heading"><h2 id="accuracy-title">How accurate was this outlook?</h2><span>Based on {data.metrics.matchedCount} matching timestamps</span></div>
            <div className="metrics-grid">
              {METRICS.map((metric) => <article className="metric-card" key={metric.key}>
                <div className="metric-heading"><h3>{metric.label}</h3><span>{metric.short}</span></div>
                <p className="metric-value">{number(data.metrics[metric.key], metric.key === "biasMW")} <span>MW</span></p>
                <p className="metric-note">{metric.note}</p>
              </article>)}
            </div>
          </section>

          <details className="methodology">
            <summary>Understand this comparison<span>Methodology +</span></summary>
            <div><p>Hourly forecasts are compared with the 30-minute actual beginning at the same time. For example, the 12:00 forecast is compared with the actual for 12:00–12:30. Metrics describe these matching timestamps. Chart lines stop at missing values.</p>
              <p>Error = forecast − actual. Positive bias means overforecasting. Missing values show as a dash; a measured zero is valid. The default 09:00 decision time is a demo assumption, not an exchange gate closure.</p>
              <p>This view uses only Elexon’s reported GB wind generation. Calculating a utility’s purchase volume would also require its demand and contracted generation.</p></div>
          </details>
        </>}
      </main>

      <footer><span>Source: Elexon WINDFOR + FUELHH · Wind only</span>
        <a href="https://bmrs.elexon.co.uk/wind-generation" target="_blank" rel="noreferrer">About the source <span aria-hidden="true">↗</span></a>
      </footer>
    </div>
  );
}
