# Wind forecast analysis

A small Python API for reviewing GB wind forecasts available at a historical
day-ahead purchasing decision and measuring their accuracy against reported outturn.
This checkpoint contains the backend. The React interface, Docker packaging,
deployment, and demonstration video are still to be completed.

## Run locally

Requires Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).

```bash
uv venv --python python3.12 .venv
uv pip install --python .venv/bin/python -r requirements-dev.txt
.venv/bin/python -m uvicorn backend.app:app --reload
```

Open the interactive API documentation at <http://127.0.0.1:8000/docs>.

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
