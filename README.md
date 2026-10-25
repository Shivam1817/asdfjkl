# Wind forecast analysis

A React dashboard and Python API for reviewing GB wind forecasts available at a historical
day-ahead purchasing decision and measuring their accuracy against reported outturn.
The dashboard includes decision controls, a forecast comparison chart, and daily
accuracy metrics. A production entry point serves the built dashboard and API
together, with Docker packaging for the complete application. Public deployment
and the demonstration video are still to be completed.

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

Example request:

```bash
curl 'http://127.0.0.1:8000/api/day-ahead?decision_date=2026-01-10&decision_time=09:00'
```

Run the tests without making external network requests:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Production integration checks run when `frontend/dist/index.html` exists;
otherwise they are skipped. Build the frontend first to include those checks.

## Run the production build locally

From the repository root:

```bash
npm --prefix frontend run build
.venv/bin/python -m uvicorn backend.production:app --host 127.0.0.1 --port 8080
```

Open <http://127.0.0.1:8080>. This uses one Python server, without Vite's dev
server or `--reload`. Port 8080 lets you compare it with the development servers.
Press Ctrl+C to stop it.

- Vite compiles React into HTML, CSS, and JavaScript under `frontend/dist/`.
- `backend/production.py` serves those files at `/` and the API at `/api/day-ahead`.
- The browser's existing `/api` requests go to the same server as the page,
  so no frontend API URL setting or CORS configuration is required.

The production entry point requires the build directory to exist. It resolves
the directory relative to its Python file, rather than the terminal's working
directory. API routes take priority over frontend files. Unknown paths return
404; this dashboard uses section anchors rather than client-side page routes.
Rebuild the frontend after changes to React or CSS. Node.js is needed to build,
but only Python is needed to run the built application.

This is a local verification of the production serving setup; public hosting
is still pending.

## Run with Docker

Start Docker Desktop, then run from the repository root:

```bash
docker build --pull --platform linux/amd64 --provenance=false --output type=docker -t winddesk:local .
docker run --rm --name winddesk --platform linux/amd64 -p 127.0.0.1:8081:8080 winddesk:local
```

Open <http://127.0.0.1:8081>. Port 8081 keeps this separate from the production
preview on port 8080. The container includes the built frontend and API;
you do not need to start the development servers. Stop it with Ctrl+C, or run
`docker stop winddesk` from another terminal. `--rm` removes the stopped container;
the image stays available for the next run. Rebuild the image after code changes.

The Dockerfile has two stages:

1. **Frontend build:** Node.js 24 installs the locked npm dependencies with
   `npm ci`, then builds React. Package files are copied first so Docker can
   reuse the dependency layer when only frontend source changes.
2. **Python runtime:** Python 3.12 installs `requirements.txt`, then receives
   the backend and the generated frontend files. The app runs as the `winddesk`
   user. Node.js and `node_modules` stay in the build stage.

`.dockerignore` keeps local environments, generated builds, caches, `.env`
files, and Git history out of the build context. Docker creates its own build
instead of copying the build from your laptop.

`PORT` defaults to 8080 and can be set by the host. For example:

```bash
docker run --rm --name winddesk --platform linux/amd64 -e PORT=9090 -p 127.0.0.1:8081:9090 winddesk:local
```

The left port is on your computer; the right port is inside the container.
`EXPOSE` documents the default container port; `-p` publishes it. Uvicorn listens
on `0.0.0.0` inside the container so Docker can reach it. The startup command
uses `exec` to pass shutdown signals directly to Python.

The build command targets Linux `amd64`, which [Heroku's container runtime
requires](https://devcenter.heroku.com/articles/container-registry-and-runtime#known-issues-and-limitations).
Docker Desktop can build and run it on an ARM Mac using emulation. The export
flags create a Docker-format image without an attestation manifest, matching
Heroku's registry format requirement. For native local development, omit
`--platform linux/amd64` from both commands.
Base image tags receive updates; `--pull` checks for newer versions when rebuilding.

## Code layout

| Path | Responsibility |
| --- | --- |
| `backend/elexon.py` | Fetch Elexon forecasts and wind actuals. |
| `backend/forecasts.py` | Parse timezone-aware timestamps and select forecasts available at the decision. |
| `backend/analysis.py` | Match delivery timestamps and calculate MAE, RMSE, and bias. |
| `backend/app.py` | Validate HTTP inputs and connect the pipeline. |
| `backend/production.py` | Serve the API and built dashboard from one origin. |
| `Dockerfile`, `.dockerignore` | Build the frontend and package the Python runtime without local generated files. |
| `app.py`, `vercel.json`, `.python-version` | Configure Vercel's application entry point, frontend build, function bundle, and Python version. |
| `frontend/src/App.jsx` | Decision form, request state, results, and metric cards. |
| `frontend/src/WindChart.jsx` | Display hourly series, preserving gaps for missing values. |
| `frontend/src/styles.css` | Responsive dashboard styling. |
| `frontend/src/main.jsx` | Mount the React application in the page. |
| `frontend/vite.config.js` | React build setup and local API proxy. |
| `frontend/package.json`, `frontend/package-lock.json` | Frontend commands and reproducible dependency versions. |
| `tests/` | Test the calculations, request filters, and HTTP behavior. |
| `requirements.txt` | Pinned direct runtime dependencies. |
| `requirements-dev.txt` | Runtime dependencies plus the HTTP test client. |

The interface takes visual cues from [REint](https://reint.ai/): Inter typography,
green accents, square panels, and thin borders. CSS variables share the palette
between the dashboard and its chart. Inter loads from Google Fonts with system
font fallbacks; the styling adds no JavaScript dependencies.

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

Vercel configuration uses the repository root with the **FastAPI** framework.
The root `app.py` imports the existing production application, and
`.python-version` selects Python 3.12. Python dependencies come from
`requirements.txt`. The build command installs the frontend's locked
dependencies and builds React before Vercel loads the app. `vercel.json`
excludes frontend `node_modules` and tests from the Python function bundle.

Vercel serves the generated frontend files through its CDN and API requests
through its Python runtime. The frontend keeps using the same `/api` URL;
no API key or additional environment variables are required.
The Docker image remains available for running the complete app as a container.

A verified public URL will be added after deployment completes.
