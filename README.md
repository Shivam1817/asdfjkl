# Wind forecast analysis

A React dashboard and Python API for reviewing GB wind forecasts available at a historical
day-ahead purchasing decision and measuring their accuracy against reported outturn.
The dashboard includes decision controls, a forecast comparison chart, and daily
accuracy metrics. Docker packaging, deployment, and the demonstration video are
still to be completed.

## Run locally

Requires Python 3.12 or newer, [uv](https://docs.astral.sh/uv/), and Node.js 22.12 or newer.

Start the API from the repository root:

```bash
uv venv --python python3.12 .venv
uv pip install --python .venv/bin/python -r requirements-dev.txt
.venv/bin/python -m uvicorn backend.app:app --reload
```

Open the interactive API documentation at <http://127.0.0.1:8000/docs>.

In a second terminal, start the React interface:

```bash
cd frontend
npm ci
npm run dev
```

Open <http://127.0.0.1:5173>. Vite forwards `/api` requests to the Python server
on port 8000 during development. Form edits are applied when you press
**Load outlook**. Loading, unavailable-data, and empty-data states are explicit;
missing chart values remain gaps. The chart uses GW on its axis and MW in its
tooltip; the accuracy cards use MW.

Create the frontend production files with `npm run build` from `frontend/`.
The output is written to `frontend/dist/`. Deployment will need to route `/api`
to the Python backend; the development proxy is not a production deployment.

Example request:

```bash
curl 'http://127.0.0.1:8000/api/day-ahead?decision_date=2026-01-10&decision_time=09:00'
```

Run the tests without making external network requests:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

## Code layout

| Path | Responsibility |
| --- | --- |
| `backend/elexon.py` | Fetch Elexon forecasts and wind actuals. |
| `backend/forecasts.py` | Parse timezone-aware timestamps and select forecasts available at the decision. |
| `backend/analysis.py` | Match delivery timestamps and calculate MAE, RMSE, and bias. |
| `backend/app.py` | Validate HTTP inputs and connect the pipeline. |
| `frontend/src/App.jsx` | Decision form, request state, results, and metric cards. |
| `frontend/src/WindChart.jsx` | Display hourly series, preserving gaps for missing values. |
| `frontend/src/styles.css` | Responsive dashboard styling. |
| `frontend/src/main.jsx` | Mount the React application in the page. |
| `frontend/vite.config.js` | React build setup and local API proxy. |
| `frontend/package.json`, `frontend/package-lock.json` | Frontend commands and reproducible dependency versions. |
| `tests/` | Test the calculations, request filters, and HTTP behavior. |
| `requirements.txt` | Pinned direct runtime dependencies. |
| `requirements-dev.txt` | Runtime dependencies plus the HTTP test client. |

## Analysis assumptions

- Decision dates are restricted to January 2026. Decision times are UK time,
  which is UTC in January. The default 09:00 is a demo assumption, not an
  exchange-specific gate closure.
- Delivery means the next calendar day, from midnight inclusive to the next
  midnight exclusive. A 31 January decision therefore evaluates 1 February.
- Search the preceding 48 hours of forecast publications. For each delivery
  timestamp, select the latest publication at or before the decision cutoff.
  A forecast outside this history window will not be selected.
- WINDFOR forecasts are hourly; FUELHH actuals are 30-minute average MW values.
  Match identical start times without interpolation or averaging. A forecast at
  12:00 is compared with the actual for 12:00–12:30. The resulting metrics describe
  these matching timestamps, rather than all 48 half-hour periods.
- Use the latest actual revision received for a delivery timestamp. Missing
  values remain null and are excluded from metrics; a measured zero is valid.
  Return forecast and matched counts alongside the expected 24 hourly forecasts.
- Error is forecast minus actual. MAE is mean absolute error; RMSE is the square
  root of mean squared error; bias is mean signed error. All are reported in MW.
  Positive bias means overforecasting. With no valid matches, metrics are null.

The data sources are Elexon's [WINDFOR forecast stream](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream)
and [FUELHH outturn stream](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream),
with FUELHH restricted to `fuelType=WIND`. No additional datasets are used.
The API does not calculate a utility's purchase volume because customer demand
and contracted generation are outside the supplied data.

## AI assistance

OpenAI Codex was used to assist with implementation, tests, debugging, and
documentation.

## Deployment

Not deployed yet. A hosted application URL will be added when deployment is complete.
