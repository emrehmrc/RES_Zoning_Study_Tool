# OST RES Zoning Tool — Renewable Energy Site Analysis Platform

## Overview

A GIS analysis platform supporting **Solar PV, On-Shore Wind, and Off-Shore Wind** projects. Next.js frontend + Django REST backend, running via Docker Compose.

```
docker compose up  →  frontend:3000 + backend:8000
```

**Tech Stack**: Next.js 14, React 18, Tailwind CSS, Leaflet | Django 4.2, DRF, GeoPandas, Rasterio, GDAL 3.11, NetworkX

---

## Architecture & Request Flow

```
Frontend (Next.js)                Backend (Django REST)              Engines (Python)
─────────────────                 ────────────────────               ────────────────
React Component                   API View                           Engine Class
    │                                 │                                  │
    ├─ POST /api/grid/create ────────→ grid_views.py ──────────────────→ FastGridEngine
    ├─ POST /api/analysis/run-async ─→ layer_views.py ─────────────────→ UniversalRasterScorer
    ├─ POST /api/scoring/run-async ──→ scoring_views.py                  (inline calculation)
    ├─ POST /api/cluster/run-async ──→ cluster_views.py ───────────────→ ClusterEngine
    │                                                    ───────────────→ ClusterScorer
    │                                                    ───────────────→ FinancialScorer
    │
    └─ Session tracking via X-Session-ID header
```

**The backend calls engines directly via Python imports.** Django settings.py adds the project root to `sys.path` → accessed as `from engines.grid_engine import FastGridEngine`. During Docker build, the `engines/`, `utils/`, `config.py`, and `config/` directories are COPYed into the backend container.

**Session management**: Every request carries an `X-Session-ID` header. The backend stores intermediate results as pickles under `temp/sessions/<uuid>/` (grid_df.pkl, scoring_results.pkl, etc.). Session state (project_type, layer_configs, scoring_rules) is also kept in RAM.

**Long-running operations**: `task_manager.py` starts a daemon thread. The frontend tracks progress via polling (`GET /api/task/<id>/progress`).

---

## Folder Structure

```
OST RES Zoning Tool/
├── docker-compose.yml          # Orchestration: backend:8000 + frontend:3000
├── config.py                   # Global path constants (DATA_DIR, TEMP_DIR, NUTS/EEZ paths)
│
├── backend/                    # Django REST API
│   ├── Dockerfile              # Python 3.12 + GDAL, Gunicorn
│   ├── requirements.txt        # Django, DRF, GeoPandas, Rasterio, NetworkX
│   ├── core/                   # Django settings, URL routing, WSGI/ASGI
│   └── api/
│       ├── middleware.py        # X-Session-ID header extraction
│       ├── session_manager.py   # Pickle-based DataFrame storage
│       ├── task_manager.py      # Async task + progress polling
│       └── views/
│           ├── project_views.py # Project selection, status, reset
│           ├── grid_views.py    # Grid creation → FastGridEngine
│           ├── layer_views.py   # Raster analysis → UniversalRasterScorer
│           ├── scoring_views.py # Weighted scoring (inline)
│           └── cluster_views.py # Clustering → ClusterEngine + ClusterScorer + FinancialScorer
│
├── frontend/                   # Next.js 14 + React 18
│   ├── Dockerfile              # Multi-stage Node.js build, port 3000
│   ├── src/
│   │   ├── app/                # Next.js app router (layout, page, dashboard/)
│   │   ├── components/         # LandingPage, Dashboard, Sidebar, GridizationTab,
│   │   │                       # ScoringTab, LevelScoringTab, ClusterTab,
│   │   │                       # CountryMapPreview, FileBrowserModal, ProcessingOverlay
│   │   └── lib/                # API client (apiGet, apiPost, apiRunWithProgress)
│   └── public/                 # Static assets
│
├── engines/                    # Business logic engines (imported by backend)
│   ├── grid_engine.py          # FastGridEngine — rectangular grid generation within boundaries
│   ├── raster_scorer.py        # UniversalRasterScorer — distance, coverage, mean, categorical
│   ├── cluster_engine.py       # ClusterEngine — NetworkX-based clustering + capacity splitting
│   ├── cluster_scorer.py       # ClusterScorer — transmission line distance scoring (L1-L4)
│   └── financial_scorer.py     # FinancialScorer — CAPEX, LCOE, payback period
│
├── utils/                      # Configuration system
│   ├── config_manager.py       # Factory: ConfigManager.get_config("Solar"|"OnShore"|"OffShore")
│   ├── config_solar.py         # Solar PV layer/scoring/transmission rules
│   ├── config_onshore.py       # On-shore wind layer/scoring rules
│   ├── config_offshore.py      # Off-shore wind layer/scoring rules
│   └── config_wind.py          # Legacy general wind config
│
├── config/                     # Reference data
│   ├── cp_values.json          # Wind speed → Cp lookup table
│   └── financial_constants.json # CAPEX constants, transmission costs, discount rates
│
├── data/                       # User raster/shapefile input files
├── outputs/                    # Analysis outputs (CSV, GeoJSON, SHP)
├── temp/sessions/              # Session-based pickle files
├── Off_shore_shapes/           # EEZ (Exclusive Economic Zone) shapefile
└── tests/                      # Unit tests
```

---

## 5-Step Pipeline

| Step | Frontend Tab | Backend Endpoint | Engine | Output |
|------|-------------|-----------------|--------|--------|
| 1. Grid | GridizationTab | `POST /api/grid/create` | `FastGridEngine` | Rectangular cell grid |
| 2. Analysis | ScoringTab | `POST /api/analysis/run-async` | `UniversalRasterScorer` | Per-cell metrics (distance_km, coverage_pct, mean...) |
| 3. Scoring | LevelScoringTab | `POST /api/scoring/run-async` | Inline | FINAL_GRID_SCORE |
| 4. Clustering | ClusterTab | `POST /api/cluster/run-async` | `ClusterEngine` → `ClusterScorer` → `FinancialScorer` | Cluster GeoDataFrame + CAPEX + LCOE |
| 5. Visualization | (Leaflet map) | `GET /api/.../results` | — | Interactive layered map |

---

## Docker Compose

```yaml
backend:8000   ← Gunicorn + Django REST
frontend:3000  ← Next.js standalone

Shared Volumes:
  ./data     → /app/data       (raster input)
  ./outputs  → /app/outputs    (analysis output)
  ./temp     → /app/temp       (session pickles)
```

The backend Dockerfile copies `engines/`, `utils/`, `config.py`, `config/`, and geographic reference files into the container.
