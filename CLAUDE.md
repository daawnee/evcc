# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`evcc` is an **EV TCO (Total Cost of Ownership) Calculator** HTTP API built as an **Azure Functions**
app using the **Python v2 programming model** (decorator-based, defined in `function_app.py`). Given
a set of cars to compare, it projects each car's cumulative cost of ownership month-by-month and
reports where the curves cross — answering *"a cheaper ICE car vs. a more expensive EV break even at
month X; own it longer than that and the EV wins."*

## Domain model

- **Inputs per car** (`CarSelection`): `model_id`, `purchase_price`, `age_at_purchase_months`, an
  optional `financing` block, and optional per-field overrides.
- **Database lookup** (keyed by `model_id`): consumption, depreciation curve, yearly service cost,
  yearly insurance cost, yearly tax — see `CarData`. When a model isn't in the database, a
  **type-level fallback** (`fallback_car_data`) is used, built from the hardcoded Hungarian-market
  defaults at the bottom of `input.py` keyed by `VehicleType` (`bev`/`petrol`/`diesel`/`hybrid`/`phev`).
- **Powertrains & energy model** (`engine._energy_nominal_monthly`): `bev` runs on electricity both
  legs; `petrol`/`diesel`/`hybrid` on a single combustion fuel (`CarData.fuel`, default petrol) both
  legs; **`phev` runs the commute leg on grid electricity (`electric_consumption`, kWh/100km) and the
  travel leg on the combustion fuel** — so the commute/travel mileage split *is* the
  electric-vs-fuel driving share. `consumption` is L/100km for combustion types and kWh/100km for bev.
- **Shared assumptions** (`Assumptions`, all defaulted/overridable): yearly `mileage` split into
  **commute** (cheap energy tariff) vs **travel** (expensive tariff); two energy price sets
  (`energy_cheap` = home charging / local station, `energy_expensive` = fast charging / highway);
  `other_yearly` (parking, vignette); `inflation`; and `horizon_months` (default **60**).
- **Output** (`output.py`): per car a `series` of `MonthlyPoint`s (per-component cost breakdown +
  running `cumulative`), plus pairwise `breakevens`. The shape is **chart-ready** on purpose — a
  small static UI to plot the curves is a planned follow-up (currently API-only).

### Locked design decisions

- **Data source**: Azure **Blob Storage** (container `cars`), with a local `FileStore` fallback for
  dev/tests. Per-model layout is **flat by `model_id`**: `cars/<model_id>/metadata.json` + optional
  blobs (e.g. `photo.jpg`), plus a top-level `cars/index.json` catalog.
- **Depreciation is anchored at the entered purchase price**: the price is treated as the car's
  value at its purchase age, and the retained-value curve carries it forward from there
  (see `engine._retained_pct` / `engine.compute`).
- **Financing contributes only interest** to TCO (principal is already captured via depreciation):
  total interest is spread evenly over the loan term.

## Commands

Local development uses the [Azure Functions Core Tools](https://learn.microsoft.com/azure/azure-functions/functions-run-local) (`func`).

```bash
# Set up env (Python 3.10 per .python-version; .venv is the expected venv path)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt          # runtime deps + pytest

# Run the test suite (engine is pure Python — no Azure/host needed)
python -m pytest -q
python -m pytest tests/test_engine.py::test_bev_vs_ice_breakeven_within_horizon  # single test

# Run the function host locally (serves /calculate and /models on http://localhost:7071)
func host start

# Attach a debugger: VS Code launch config "Attach to Python Functions" (port 9091),
# which runs `func host start` as its preLaunchTask.
```

CI (`.github/workflows/main_evcc.yml`) installs `requirements-dev.txt`, **runs pytest**, builds the
UI (`npm ci && npm run build` in `ui/`), then zips and deploys to the Azure Function App named `evcc`
on every push to `main`. The zip excludes `tests/`, `ev_database_org/`, `.scrape/`, `*.jl`,
`ui/node_modules/`, and `data/cars/` (see `.funcignore` and the `zip -x` list).

### Production data (Blob Storage)

Car data is **not** deployed in the package — production reads it from Blob Storage. For the deployed
app to serve cars, two one-time setup steps are required on the Azure side:

1. **App setting `USE_BLOB=1`** on the Function App (so `get_store()` picks `BlobStore`).
   `AzureWebJobsStorage` is already set by the platform; the `cars` container lives in that account.
2. **Upload the dataset**: `AzureWebJobsStorage="<prod connection string>" python scripts/seed_blob.py`
   (run after each data refresh). Without these, `data/` isn't in the package so the catalog is empty.

## Architecture

Request flow:

1. `function_app.py` — registers the `FunctionApp` (anonymous auth) and routes `GET|POST /calculate`
   → `endpoints.calculate` and `GET /models` → `endpoints.models`. `host.json` sets
   `routePrefix: ""`, so routes are `/calculate` and `/models` (no `/api` prefix).
2. `endpoints/calculate.py` — parses the body into `models.calculate.Input` (Pydantic;
   `ValidationError` → `400` with the error text). For each `CarSelection`: loads `CarData` from the
   store by `model_id`, else falls back to `fallback_car_data(sel.type, …)` (and `400`s if neither a
   DB row nor a `type` override is available), applies `apply_overrides`, then calls
   `engine.compute`. Finally returns `Output(cars=…, breakevens=engine.breakevens(…))` as JSON.
3. `endpoints/models.py` — returns the store's `index.json` catalog.
4. `common/storage.py` — `get_store()` selects a backend: `CARS_DATA_DIR` env → `FileStore(dir)`;
   else if `USE_BLOB` is truthy **and** `AzureWebJobsStorage` is set → `BlobStore` (downloads blobs
   to a temp cache, then reads locally) — **this is the production path**; otherwise a local
   `FileStore` over `data/cars` (a git-ignored working copy, empty on a fresh clone). Backends expose
   `get_index()`, `get_car()`, `get_photo()`. **No car data lives in git** — the dataset lives in Blob
   Storage (container `cars`), uploaded with `scripts/seed_blob.py`; the whole `data/` folder is
   git-ignored. Tests use committed fixtures under `tests/fixtures/cars/`.
5. `models/calculate/engine.py` — **pure** TCO math, no Azure deps (so it's unit-tested directly).
   `compute()` walks `horizon_months`, accumulating monthly depreciation (from the anchored
   retained-value curve), energy (commute×cheap + travel×expensive, inflation-adjusted), service,
   insurance, other (tax+parking+vignette), and financing interest. `breakevens()` finds the first
   month each pair's cumulative curves cross.
6. `common/params.py` — `Params` is a unified accessor over an `HttpRequest`: `params["a.b.c"]`
   checks **headers, then query string, then a dotted path into the JSON body**. `params.body` is
   the parsed JSON (or `{}`).

### Data flow for car data

`CarData` (per-model, from the DB or a type fallback) is the resolved input the engine consumes.
The hardcoded `DEFAULT_*` tables at the bottom of `input.py` (keyed by `VehicleType`, with
source-URL comments) feed `fallback_car_data`; `apply_overrides` then layers any per-request
overrides on top. To add a car to the bundled dataset: create `data/cars/<model_id>/metadata.json`
(matching the `CarData` schema) and add an entry to `data/cars/index.json`. `scripts/seed_blob.py`
uploads `data/cars/` to the Blob `cars` container for production.

## Car data pipeline (ev-database.org scraper)

BEV data is populated by scraping [ev-database.org](https://ev-database.org). The scraper is a
self-contained Scrapy + web-poet project in [ev_database_org/](ev_database_org/) (its own `uv`
environment; not part of the Azure Functions app):

- `ev_database_org/ev_database_org/pages/car.py` — `CarPage` page object extracting 24 fields from a
  `/car/{id}/{slug}` detail page (raw HTML; the site is server-rendered).
- `.../pages/navigation.py` — `NavigationPage`; the homepage raw HTML lists all ~1365 BEVs.
- `.../spiders/ev_database_org.py` — crawls the homepage, follows every car link (does **not** follow
  subcategories, which are duplicate country/cheatsheet listings).
- `fixtures/` — web-poet fixture tests (`uv run pytest fixtures/`). Regenerate expected outputs with
  `Fixture(path).get_output(PageClass)` when a page object changes.

Run the crawl and import into the evcc database:

```bash
# ev-database rate-limits direct crawling (HTTP 429 on /car/ pages after a few dozen requests),
# so the crawl MUST go through Zyte API (the project is pre-wired; needs ZYTE_API_KEY in env).
cd ev_database_org && uv run scrapy crawl ev_database_org -O cars_full.jl \
  -s ZYTE_API_TRANSPARENT_MODE=True -s CONCURRENT_REQUESTS=16 -s DOWNLOAD_DELAY=0   # ~4-5 min, ~1365 cars
python scripts/import_ev_database.py ev_database_org/cars_full.jl                   # -> data/cars/<id>-<slug>/
```

`model_id` is `<ev-database-id>-<slug>` (e.g. `1991-tesla-model-3-rwd`) — the numeric id is required
because model-year/battery variants share name slugs. Hero **photos** are fetched directly from
ev-database (the image host is *not* rate-limited, only the detail pages are).

**ICE / hybrid / PHEV** data comes from **auto-data.net** (EEA's API proved unreliable). The
`auto_data_net` spider (same Scrapy project, via Zyte) crawls allbrands → brand → model →
generation (kept if produced ≥2015) → variant detail, scoped to a mainstream-brand allowlist;
`scripts/import_autodata.py` classifies the powertrain (petrol/diesel/hybrid/phev), maps urban→
`consumption.average` / extra-urban→`consumption.highway`, fills the rest from type fallbacks, and
merges into the catalog. Re-upload with `seed_blob.py --skip-existing` to avoid re-pushing the EV photos.

`scripts/import_ev_database.py` maps each scraped `Car` into a complete `CarData`
(consumption converted Wh/km→kWh/100km; `specs` + `price_new` populated), **fills
depreciation/service/insurance/tax from the BEV type-fallbacks** (ev-database doesn't provide them),
downloads the hero photo to `<model_id>/photo.jpg`, and **merges** `index.json` (preserving non-BEV
seed entries like the ICE comparison cars). The drafted extraction spec lives under `.scrape/`
(git-ignored). ICE/other-powertrain data comes from separate sources (EEA, ADAC, marketplaces) — not
yet wired.

## Web UI

A Vue 3 + Vite single-page app lives in [ui/](ui/) and is **served by the Functions app itself**
(same origin, no CORS). It's a strict A-vs-B TCO comparator laid out as aligned tiles: two car
pickers (search the `/models` catalog, thumbnail + specs), per-car price (EVs prefilled from
`price_new` DE EUR × a fixed `EUR_HUF` rate in `ui/src/api.js`) and an **age-at-purchase dropdown**
("As new", "1 month", … "1 year 2 months"), a collapsible assumptions panel (mileage split + energy
prices), and a Chart.js cumulative-cost chart with the break-even month marked plus a plain-language
summary. Auto light/dark; HUF prices throughout. The UI requests a **120-month horizon** (the
60-month default would hide most EV-vs-ICE break-evens).

**i18n** ([ui/src/i18n.js](ui/src/i18n.js)): **English is the default**; Hungarian (`hu`) is chosen
only when a `hu-XX` locale appears in `navigator.languages` before any `en-XX`. All UI strings,
powertrain labels, the age dropdown, number/locale formatting, and chart labels go through `t`/`locale`.

```bash
cd ui && npm install
npm run dev        # Vite dev server; proxies /calculate /models /car /photo to localhost:7071
npm run build      # -> ui/dist (git-ignored; CI rebuilds it; .funcignore keeps node_modules/src out of deploy)
```

Backend routes added for the UI (all in `function_app.py`, registered as Functions v2 routes):
`GET /car/{model_id}` (full `CarData` for prefill/specs), `GET /photo/{model_id}` (hero JPEG via
`storage.get_photo`), and a `GET /{*path}` catch-all serving `ui/dist` (SPA fallback to index.html).
The literal API routes take precedence over the catch-all. **`dist/` must exist at runtime** — the
deploy either ships it (CI builds it) or the catch-all returns a "UI not built" 404.

## Conventions

- Each package exposes its public surface via `__init__.py` re-exports (e.g. `from common import
  Params, get_store`, `from models.calculate import Input, engine`). Add new endpoints/models the same way.
- `requirements.txt` must **not** include `azure-functions-worker` (managed by the platform).
  `azure-storage-blob` is imported lazily inside `BlobStore`, so the pure engine and `FileStore`
  path work without it installed.
