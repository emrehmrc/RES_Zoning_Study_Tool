# Dashboard_v4 — Yenilenebilir Enerji Santral Sahaları Analiz Platformu

## Genel Bakış

**Solar PV, On-Shore Wind ve Off-Shore Wind** projelerini destekleyen bir GIS analiz platformu. Next.js frontend + Django REST backend, Docker Compose ile çalışır.

```
docker compose up  →  frontend:3000 + backend:8000
```

**Teknoloji**: Next.js 14, React 18, Tailwind CSS, Leaflet | Django 4.2, DRF, GeoPandas, Rasterio, GDAL 3.11, NetworkX

---

## Mimari & İstek Akışı

```
Frontend (Next.js)                Backend (Django REST)              Engines (Python)
─────────────────                 ────────────────────               ────────────────
React Component                   API View                           Engine Class
    │                                 │                                  │
    ├─ POST /api/grid/create ────────→ grid_views.py ──────────────────→ FastGridEngine
    ├─ POST /api/analysis/run-async ─→ layer_views.py ─────────────────→ UniversalRasterScorer
    ├─ POST /api/scoring/run-async ──→ scoring_views.py                  (inline hesaplama)
    ├─ POST /api/cluster/run-async ──→ cluster_views.py ───────────────→ ClusterEngine
    │                                                    ───────────────→ ClusterScorer
    │                                                    ───────────────→ FinancialScorer
    │
    └─ X-Session-ID header ile session takibi
```

**Backend, engine'leri doğrudan Python import ile çağırır.** Django settings.py proje kökünü `sys.path`'e ekler → `from engines.grid_engine import FastGridEngine` şeklinde erişir. Docker build sırasında `engines/`, `utils/`, `config.py`, `config/` klasörleri backend container'ına COPY edilir.

**Session yönetimi**: Her istek `X-Session-ID` header taşır. Backend ara sonuçları `temp/sessions/<uuid>/` altında pickle olarak saklar (grid_df.pkl, scoring_results.pkl, vb.). RAM'de de session state tutulur (project_type, layer_configs, scoring_rules).

**Uzun işlemler**: `task_manager.py` daemon thread başlatır. Frontend polling ile progress takip eder (`GET /api/task/<id>/progress`).

---

## Klasör Yapısı

```
Dashboard_v4/
├── docker-compose.yml          # Orchestration: backend:8000 + frontend:3000
├── config.py                   # Global path sabitleri (DATA_DIR, TEMP_DIR, NUTS/EEZ yolları)
│
├── backend/                    # Django REST API
│   ├── Dockerfile              # Python 3.12 + GDAL, Gunicorn
│   ├── requirements.txt        # Django, DRF, GeoPandas, Rasterio, NetworkX
│   ├── core/                   # Django settings, URL routing, WSGI/ASGI
│   └── api/
│       ├── middleware.py        # X-Session-ID header çıkarma
│       ├── session_manager.py   # Pickle bazlı DataFrame saklama
│       ├── task_manager.py      # Async task + progress polling
│       └── views/
│           ├── project_views.py # Proje seçimi, status, reset
│           ├── grid_views.py    # Grid oluşturma → FastGridEngine
│           ├── layer_views.py   # Raster analiz → UniversalRasterScorer
│           ├── scoring_views.py # Ağırlıklı puanlama (inline)
│           └── cluster_views.py # Kümeleme → ClusterEngine + ClusterScorer + FinancialScorer
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
├── engines/                    # İş mantığı motorları (backend import eder)
│   ├── grid_engine.py          # FastGridEngine — sınır içinde dikdörtgen grid üretimi
│   ├── raster_scorer.py        # UniversalRasterScorer — distance, coverage, mean, categorical
│   ├── cluster_engine.py       # ClusterEngine — NetworkX ile kümeleme + kapasite bölme
│   ├── cluster_scorer.py       # ClusterScorer — iletim hattı mesafe skorlama (L1-L4)
│   └── financial_scorer.py     # FinancialScorer — CAPEX, LCOE, geri ödeme süresi
│
├── utils/                      # Konfigürasyon sistemi
│   ├── config_manager.py       # Factory: ConfigManager.get_config("Solar"|"OnShore"|"OffShore")
│   ├── config_solar.py         # Solar PV katman/puanlama/iletim kuralları
│   ├── config_onshore.py       # Kara rüzgarı katman/puanlama kuralları
│   ├── config_offshore.py      # Deniz rüzgarı katman/puanlama kuralları
│   └── config_wind.py          # Eski genel rüzgar config (legacy)
│
├── config/                     # Referans veri
│   ├── cp_values.json          # Rüzgar hızı → Cp lookup tablosu
│   └── financial_constants.json # CAPEX sabitleri, iletim maliyetleri, iskonto oranları
│
├── data/                       # Kullanıcı raster/shapefile girdi dosyaları
├── outputs/                    # Analiz çıktıları (CSV, GeoJSON, SHP)
├── temp/sessions/              # Session bazlı pickle dosyaları
├── NUTS_RG_01M_2021_4326.geojson  # AB NUTS bölge sınırları
├── Off_shore_shapes/           # EEZ (Münhasır Ekonomik Bölge) shapefile
└── tests/                      # Unit testler
```

---

## 5 Adımlı Pipeline

| Adım | Frontend Tab | Backend Endpoint | Engine | Çıktı |
|------|-------------|-----------------|--------|-------|
| 1. Grid | GridizationTab | `POST /api/grid/create` | `FastGridEngine` | Dikdörtgen hücre grid'i |
| 2. Analiz | ScoringTab | `POST /api/analysis/run-async` | `UniversalRasterScorer` | Hücre bazında metrikler (distance_km, coverage_pct, mean...) |
| 3. Puanlama | LevelScoringTab | `POST /api/scoring/run-async` | Inline | FINAL_GRID_SCORE |
| 4. Kümeleme | ClusterTab | `POST /api/cluster/run-async` | `ClusterEngine` → `ClusterScorer` → `FinancialScorer` | Küme GeoDataFrame + CAPEX + LCOE |
| 5. Görselleştirme | (Leaflet harita) | `GET /api/.../results` | — | İnteraktif katmanlı harita |

---

## Docker Compose

```yaml
backend:8000   ← Gunicorn + Django REST
frontend:3000  ← Next.js standalone

Paylaşımlı Volume'lar:
  ./data     → /app/data       (raster girdi)
  ./outputs  → /app/outputs    (analiz çıktı)
  ./temp     → /app/temp       (session pickle)
```

Backend Dockerfile `engines/`, `utils/`, `config.py`, `config/`, coğrafi referans dosyalarını container'a kopyalar.
