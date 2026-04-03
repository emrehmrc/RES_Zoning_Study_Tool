'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { apiPost, setSessionId } from '@/lib/api'

/* ─── About Modal ─── */
function AboutModal({ onClose }: { onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={onClose}>
      <div
        className="relative bg-white rounded-2xl shadow-2xl max-w-3xl w-full mx-4 max-h-[85vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-gradient-to-r from-slate-800 to-slate-700 rounded-t-2xl px-8 py-5 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-white">📖 About This Dashboard</h2>
          <button onClick={onClose} className="text-white/70 hover:text-white text-2xl font-bold transition-colors">✕</button>
        </div>

        {/* Body */}
        <div className="px-8 py-6 text-slate-700 text-[15px] leading-relaxed space-y-5">

          <section>
            <h3 className="text-lg font-bold text-slate-800 mb-2">🌍 Overview</h3>
            <p>
              The <strong>Renewable Energy Zoning Dashboard</strong> is a comprehensive GIS-based analysis platform
              developed for <strong>OST (Operatori i Sistemit të Transmetimit)</strong> — the Transmission System Operator.
              It enables energy planners and engineers to identify, evaluate, and rank optimal zones for renewable
              energy project deployment across a given territory.
            </p>
            <p className="mt-2">
              The platform supports three distinct project modes: <strong>Solar PV</strong>, <strong>On-Shore Wind</strong>,
              and <strong>Off-Shore Wind</strong>. Each mode provides a customized analysis pipeline tailored to the
              specific technical, environmental, and economic requirements of that technology.
            </p>
          </section>

          <hr className="border-slate-200" />

          <section>
            <h3 className="text-lg font-bold text-slate-800 mb-2">⚙️ How It Works — The 5-Step Pipeline</h3>
            <p>Every analysis follows a structured, step-by-step pipeline:</p>
            <ol className="list-decimal list-inside space-y-2 mt-3 ml-2">
              <li>
                <strong>Grid Creation</strong> — The selected geographic region is divided into a rectangular grid of
                analysis cells. Cell size is configurable (e.g. 1×1 km). The engine clips the grid to the country or
                EEZ boundary and assigns each cell a unique identifier.
              </li>
              <li>
                <strong>Layer Analysis</strong> — Multiple geospatial raster layers (solar irradiance, wind speed, slope,
                land cover, protected areas, transmission line proximity, etc.) are evaluated for each grid cell.
                Analysis methods include distance calculation, area coverage, mean value extraction, and categorical classification.
              </li>
              <li>
                <strong>Scoring</strong> — Each analyzed metric is converted to a normalized score (1–5) based on
                configurable threshold rules. Weights are assigned to each criterion, and a weighted <strong>Final Grid Score</strong>
                is computed for every cell, reflecting its overall suitability.
              </li>
              <li>
                <strong>Clustering</strong> — Neighboring high-scoring cells are grouped into contiguous clusters
                using graph-based algorithms. Large clusters can be split by capacity limits. Each cluster receives
                a composite score based on its constituent cells, proximity to transmission infrastructure,
                and estimated financial performance (CAPEX, LCOE, payback period).
              </li>
              <li>
                <strong>Visualization</strong> — Results are displayed on an interactive Leaflet map with
                color-coded layers, popup details for each cell and cluster, and data export options
                (CSV, GeoJSON, Shapefile).
              </li>
            </ol>
          </section>

          <hr className="border-slate-200" />

          <section>
            <h3 className="text-lg font-bold text-slate-800 mb-2 flex items-center gap-2"><img src="/Solar.png" alt="Solar" className="h-8 w-8 rounded object-cover" /> Solar PV Mode</h3>
            <p>
              Evaluates solar photovoltaic potential using Global Horizontal Irradiance (GHI) data, terrain slope
              analysis, land use / land cover constraints, and distance to existing transmission lines.
              Steep slopes, protected areas, water bodies, and urban zones are automatically excluded or penalized.
            </p>
          </section>

          <section>
            <h3 className="text-lg font-bold text-slate-800 mb-2 flex items-center gap-2"><img src="/Onshore.jpeg" alt="On-Shore" className="h-8 w-8 rounded object-cover" /> On-Shore Wind Mode</h3>
            <p>
              Assesses onshore wind farm suitability using wind speed data at hub height, terrain roughness,
              environmental and social constraints (protected habitats, residential buffers), and turbine-specific
              parameters. Power coefficient (Cp) lookup tables convert wind speeds to estimated capacity factors.
            </p>
          </section>

          <section>
            <h3 className="text-lg font-bold text-slate-800 mb-2 flex items-center gap-2"><img src="/Offshore.png" alt="Off-Shore" className="h-8 w-8 rounded object-cover" /> Off-Shore Wind Mode</h3>
            <p>
              Analyzes offshore wind zones within the Exclusive Economic Zone (EEZ). Considers bathymetry
              (water depth), distance from shore, shipping lane exclusions, marine protected areas,
              and subsea cable routing to the nearest grid connection point. Foundation type feasibility
              (monopile, jacket, floating) is inferred from depth ranges.
            </p>
          </section>

          <hr className="border-slate-200" />

          <section>
            <h3 className="text-lg font-bold text-slate-800 mb-2">💰 Financial Analysis</h3>
            <p>
              Each identified cluster receives a financial assessment including estimated <strong>CAPEX</strong> (capital
              expenditure per MW), <strong>LCOE</strong> (levelized cost of energy in €/MWh), and <strong>payback period</strong>.
              Transmission connection costs are calculated based on distance to the nearest line and voltage level (L1–L4).
              These metrics help prioritize zones by economic viability alongside technical suitability.
            </p>
          </section>

          <hr className="border-slate-200" />

          <section>
            <h3 className="text-lg font-bold text-slate-800 mb-2">🏗️ Technical Architecture</h3>
            <p>
              The platform is built with a modern, containerized stack:
            </p>
            <ul className="list-disc list-inside space-y-1 mt-2 ml-2">
              <li><strong>Frontend</strong> — Next.js 14, React 18, Tailwind CSS, Leaflet for interactive maps</li>
              <li><strong>Backend</strong> — Django 4.2, Django REST Framework, Gunicorn</li>
              <li><strong>GIS Libraries</strong> — GeoPandas, Rasterio, GDAL 3.11, Shapely, NetworkX</li>
              <li><strong>Deployment</strong> — Docker Compose (frontend:3000 + backend:8000)</li>
              <li><strong>Session Management</strong> — Each user session stores intermediate results as pickle files, enabling long-running analyses without data loss</li>
              <li><strong>Async Processing</strong> — Heavy computations run on background threads with real-time progress polling</li>
            </ul>
          </section>

          <hr className="border-slate-200" />

          <section>
            <h3 className="text-lg font-bold text-slate-800 mb-2">📊 Data & Outputs</h3>
            <p>
              Input data includes GeoTIFF raster files (irradiance, wind speed, elevation, slope, land cover, etc.)
              and shapefiles (country boundaries, NUTS regions, EEZ, transmission lines). Analysis outputs are
              available as interactive map layers, downloadable CSV tables, GeoJSON, and Shapefile bundles —
              ready for integration into further planning workflows or GIS tools like QGIS.
            </p>
          </section>

          <section className="bg-slate-50 rounded-xl p-4 border border-slate-200">
            <p className="text-sm text-slate-500 text-center">
              Renewable Energy Zoning Dashboard — Developed for OST (Operatori i Sistemit të Transmetimit)
            </p>
          </section>
        </div>
      </div>
    </div>
  )
}

const modes = [
  {
    key: 'Solar',
    icon: '/Solar.png',
    title: 'Solar PV Zoning',
    bullets: ['Solar PV Potential Analysis', 'Slope & Terrain & Other Constraints', 'Proximity to Transmission Lines'],
    gradient: 'from-orange-400 to-amber-500',
    border: 'border-orange-300',
    btn: 'bg-orange-500 hover:bg-orange-600',
  },
  {
    key: 'OnShore',
    icon: '/Onshore.jpeg',
    title: 'On-Shore Wind Zoning',
    bullets: ['Wind Resource & Potential Assessment', 'Turbine Specific Suitability', 'Environmental & Social Constraints'],
    gradient: 'from-blue-900 to-indigo-800',
    border: 'border-blue-400',
    btn: 'bg-blue-900 hover:bg-blue-950',
  },
  {
    key: 'OffShore',
    icon: '/Offshore.png',
    title: 'Off-Shore Wind Zoning',
    bullets: ['Wind Resource & Potential Assessment', 'Turbine Specific Suitability', 'Marine Constraints'],
    gradient: 'from-blue-400 to-cyan-500',
    border: 'border-cyan-300',
    btn: 'bg-blue-500 hover:bg-blue-600',
  },
]

export default function LandingPage() {
  const router = useRouter()
  const [loading, setLoading] = useState<string | null>(null)
  const [showAbout, setShowAbout] = useState(false)

  async function selectMode(projectType: string) {
    setLoading(projectType)
    try {
      const res = await apiPost('/project/select/', { project_type: projectType })
      if (res.session_id) setSessionId(res.session_id)
      router.push('/dashboard')
    } catch (err: any) {
      alert(err.message)
    } finally {
      setLoading(null)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex flex-col items-center justify-center px-4 relative">
      {/* Logo */}
      <img src="/OST.png" alt="OST Logo" className="absolute top-6 right-8 h-42 object-contain" />

      {/* About Button */}
      <button
        onClick={() => setShowAbout(true)}
        className="absolute top-6 left-8 px-8 py-3 text-base font-medium text-white/80 hover:text-white border border-white/30 hover:border-white/60 rounded-lg transition-all hover:bg-white/10"
      >
        ℹ️ About
      </button>

      {/* About Modal */}
      {showAbout && <AboutModal onClose={() => setShowAbout(false)} />}

      {/* Header */}
      <div className="text-center mb-12">
        <h1 className="text-5xl font-bold text-white mb-3">🌍 Renewable Energy Zoning Dashboard</h1>
        <p className="text-xl text-slate-300">Select a project mode to begin analysis</p>
      </div>

      {/* Project Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl w-full">
        {modes.map((m) => (
          <div
            key={m.key}
            className={`relative bg-white rounded-2xl shadow-xl overflow-hidden transition-all duration-300 hover:scale-[1.03] hover:shadow-2xl border-2 ${m.border}`}
          >
            {/* Gradient header */}
            <div className={`bg-gradient-to-r ${m.gradient} px-6 py-8 text-center`}>
              <img src={m.icon} alt={m.title} className="h-48 w-48 object-cover mx-auto rounded-lg" />
              <h2 className="text-2xl font-bold text-white mt-3">{m.title}</h2>
            </div>
            {/* Bullets */}
            <div className="px-6 py-6 space-y-2">
              {m.bullets.map((b) => (
                <div key={b} className="flex items-start gap-2 text-slate-600 text-sm">
                  <span className="text-green-500 mt-0.5">✓</span>
                  <span>{b}</span>
                </div>
              ))}
            </div>
            {/* Button */}
            <div className="px-6 pb-6">
              <button
                onClick={() => selectMode(m.key)}
                disabled={loading !== null}
                className={`w-full py-3 rounded-xl text-white font-semibold transition-colors ${m.btn} disabled:opacity-50`}
              >
                {loading === m.key ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Loading...
                  </span>
                ) : (
                  `Select ${m.title}`
                )}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
