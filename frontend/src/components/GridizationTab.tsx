'use client'

import { useState, useEffect } from 'react'
import dynamic from 'next/dynamic'
import { apiGet, apiPost, apiDownload } from '@/lib/api'
import type { ProjectConfig } from '@/lib/types'
import ProcessingOverlay from './ProcessingOverlay'

const CountryMapPreview = dynamic(() => import('./CountryMapPreview'), { ssr: false })

interface Props { config: ProjectConfig; onComplete: () => void }

export default function GridizationTab({ config, onComplete }: Props) {
  const [mode, setMode] = useState<'generate' | 'upload'>('generate')
  const [boundaryMethod, setBoundaryMethod] = useState<'country' | 'eez' | 'file'>('country')
  const [countries, setCountries] = useState<string[]>([])
  const [eezZones, setEezZones] = useState<string[]>([])
  const [selectedCountry, setSelectedCountry] = useState('')
  const [selectedZone, setSelectedZone] = useState('')
  const [gridSizeX, setGridSizeX] = useState(1000)
  const [gridSizeY, setGridSizeY] = useState(1000)
  const [turbineDiameter, setTurbineDiameter] = useState(200)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState('')

  const isWind = config.project_type === 'OnShore' || config.project_type === 'OffShore'

  // Clamp + snap value to nearest step within [min, max]
  function clampStep(value: number, min: number, max: number, step: number): number {
    const clamped = Math.min(max, Math.max(min, value))
    return Math.round(clamped / step) * step
  }

  const GRID_MIN = 100
  const GRID_MAX = 10000
  const GRID_STEP = 100
  const TURB_MIN = 10
  const TURB_MAX = 500
  const TURB_STEP = 10

  const gridXError = gridSizeX < GRID_MIN || gridSizeX > GRID_MAX
  const gridYError = gridSizeY < GRID_MIN || gridSizeY > GRID_MAX
  const turbError  = turbineDiameter < TURB_MIN || turbineDiameter > TURB_MAX

  useEffect(() => {
    if (config.project_type === 'OffShore') {
      setBoundaryMethod('eez')
      apiGet<{ zones: string[] }>('/eez-zones/').then(r => setEezZones(r.zones)).catch(() => {})
    } else {
      apiGet<{ countries: string[] }>('/countries/').then(r => setCountries(r.countries)).catch(() => {})
    }
  }, [config.project_type])

  const effectiveX = isWind ? turbineDiameter * 3 : gridSizeX
  const effectiveY = isWind ? turbineDiameter * 5 : gridSizeY

  async function createGrid() {
    // Validate grid params before sending
    if (isWind) {
      if (turbineDiameter < TURB_MIN || turbineDiameter > TURB_MAX) {
        setError(`Turbine diameter must be between ${TURB_MIN} m and ${TURB_MAX} m.`)
        return
      }
    } else {
      if (gridSizeX < GRID_MIN || gridSizeX > GRID_MAX) {
        setError(`Grid width must be between ${GRID_MIN} m and ${GRID_MAX} m.`)
        return
      }
      if (gridSizeY < GRID_MIN || gridSizeY > GRID_MAX) {
        setError(`Grid height must be between ${GRID_MIN} m and ${GRID_MAX} m.`)
        return
      }
    }
    setLoading(true); setError(''); setResult(null)
    try {
      const body: any = {
        boundary_method: boundaryMethod,
        grid_size_x: effectiveX,
        grid_size_y: effectiveY,
      }
      if (boundaryMethod === 'country') body.country_name = selectedCountry
      if (boundaryMethod === 'eez') body.zone_name = selectedZone

      const res = await apiPost('/grid/create/', body)
      setResult(res)
      onComplete()
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function uploadGrid(file: File) {
    setLoading(true); setError(''); setResult(null)
    try {
      const fd = new FormData()
      fd.append('grid_file', file)
      const res = await apiPost('/grid/upload/', fd)
      setResult(res)
      onComplete()
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-800">📐 Step 1: Gridization</h2>
      <hr />

      {/* Mode toggle */}
      <div className="flex gap-4">
        {(['generate', 'upload'] as const).map(m => (
          <button key={m} onClick={() => setMode(m)}
            className={`px-5 py-2 rounded-lg text-sm font-medium transition ${mode === m ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 border hover:bg-slate-50'}`}>
            {m === 'generate' ? '🌍 Generate New Grid' : '📤 Upload Existing Grid'}
          </button>
        ))}
      </div>

      {mode === 'generate' ? (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left: Boundary */}
            <div className="bg-white rounded-xl p-6 shadow-sm border space-y-4">
              <h3 className="font-semibold text-slate-700">Boundary Definition</h3>

            {config.project_type !== 'OffShore' && (
              <div className="flex gap-3">
                {(['country', 'file'] as const).map(bm => (
                  <button key={bm} onClick={() => setBoundaryMethod(bm)}
                    className={`px-4 py-1.5 rounded text-sm ${boundaryMethod === bm ? 'bg-blue-100 text-blue-700 font-medium' : 'bg-slate-100 text-slate-600'}`}>
                    {bm === 'country' ? 'Select Country' : 'Upload File'}
                  </button>
                ))}
              </div>
            )}

            {boundaryMethod === 'country' && (
              <select value={selectedCountry} onChange={e => setSelectedCountry(e.target.value)}
                className="w-full border rounded-lg p-2.5 text-sm">
                <option value="">-- Select Country --</option>
                {countries.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            )}

            {boundaryMethod === 'eez' && (
              <select value={selectedZone} onChange={e => setSelectedZone(e.target.value)}
                className="w-full border rounded-lg p-2.5 text-sm">
                <option value="">-- Select EEZ Zone --</option>
                {eezZones.map(z => <option key={z} value={z}>{z}</option>)}
              </select>
            )}

            {boundaryMethod === 'file' && (
              <p className="text-sm text-slate-500 italic">
                File upload for boundaries will use the API endpoint. For now select a country.
              </p>
            )}
          </div>

          {/* Right: Grid Params */}
          <div className="bg-white rounded-xl p-6 shadow-sm border space-y-4">
            <h3 className="font-semibold text-slate-700">Grid Parameters</h3>

            {isWind ? (
              <>
                <label className="block text-sm text-slate-600">Turbine Diameter (m)
                  <input
                    type="number"
                    value={turbineDiameter}
                    min={TURB_MIN} max={TURB_MAX} step={TURB_STEP}
                    onChange={e => setTurbineDiameter(+e.target.value)}
                    onBlur={e => setTurbineDiameter(clampStep(+e.target.value, TURB_MIN, TURB_MAX, TURB_STEP))}
                    className={`mt-1 w-full border rounded-lg p-2.5 ${turbError ? 'border-red-400 bg-red-50' : ''}`}
                  />
                  {turbError && (
                    <span className="text-xs text-red-500">
                      Must be {TURB_MIN}–{TURB_MAX} m (step {TURB_STEP} m)
                    </span>
                  )}
                </label>
                <div className="text-sm bg-blue-50 text-blue-700 p-3 rounded-lg">
                  Calculated Grid: <strong>{effectiveX}m</strong> width × <strong>{effectiveY}m</strong> height
                </div>
              </>
            ) : (
              <>
                <label className="block text-sm text-slate-600">Grid Width (m)
                  <input
                    type="number"
                    value={gridSizeX}
                    min={GRID_MIN} max={GRID_MAX} step={GRID_STEP}
                    onChange={e => setGridSizeX(+e.target.value)}
                    onBlur={e => setGridSizeX(clampStep(+e.target.value, GRID_MIN, GRID_MAX, GRID_STEP))}
                    className={`mt-1 w-full border rounded-lg p-2.5 ${gridXError ? 'border-red-400 bg-red-50' : ''}`}
                  />
                  {gridXError && (
                    <span className="text-xs text-red-500">
                      Must be {GRID_MIN}–{GRID_MAX} m (step {GRID_STEP} m)
                    </span>
                  )}
                </label>
                <label className="block text-sm text-slate-600">Grid Height (m)
                  <input
                    type="number"
                    value={gridSizeY}
                    min={GRID_MIN} max={GRID_MAX} step={GRID_STEP}
                    onChange={e => setGridSizeY(+e.target.value)}
                    onBlur={e => setGridSizeY(clampStep(+e.target.value, GRID_MIN, GRID_MAX, GRID_STEP))}
                    className={`mt-1 w-full border rounded-lg p-2.5 ${gridYError ? 'border-red-400 bg-red-50' : ''}`}
                  />
                  {gridYError && (
                    <span className="text-xs text-red-500">
                      Must be {GRID_MIN}–{GRID_MAX} m (step {GRID_STEP} m)
                    </span>
                  )}
                </label>
              </>
            )}

            <button onClick={createGrid} disabled={loading}
              className="w-full py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50 transition">
              {loading ? '⏳ Creating Grid...' : '🚀 Create Grid'}
            </button>
            {loading && (
              <div className="mt-3">
                <ProcessingOverlay message="Creating grid cells..." accentColor="blue" />
              </div>
            )}
          </div>
        </div>

          {/* Map Preview */}
          {(selectedCountry || selectedZone) && (
            <div className="bg-white rounded-xl p-4 shadow-sm border">
              <h3 className="font-semibold text-slate-700 mb-3">🗺️ Preview</h3>
              <CountryMapPreview
                country={boundaryMethod === 'country' ? selectedCountry : undefined}
                zone={boundaryMethod === 'eez' ? selectedZone : undefined}
                gridSizeX={effectiveX}
                gridSizeY={effectiveY}
              />
            </div>
          )}
        </div>
      ) : (
        /* Upload */
        <div className="bg-white rounded-xl p-6 shadow-sm border max-w-lg">
          <h3 className="font-semibold text-slate-700 mb-4">📤 Upload Grid CSV</h3>
          <input type="file" accept=".csv"
            onChange={e => { if (e.target.files?.[0]) uploadGrid(e.target.files[0]) }}
            className="block w-full text-sm file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100" />
          <p className="text-xs text-slate-400 mt-2">Required columns: cell_id, wkt</p>
        </div>
      )}

      {error && <div className="bg-red-50 text-red-700 p-4 rounded-lg border border-red-200">{error}</div>}

      {result && (
        <div className="bg-white rounded-xl p-6 shadow-sm border space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-emerald-700">✅ {result.message}</h3>
            <button onClick={() => apiDownload('/grid/download/', 'grid.csv')}
              className="text-sm px-4 py-1.5 bg-slate-100 rounded-lg hover:bg-slate-200 transition">
              📥 Download CSV
            </button>
          </div>
          {/* Preview Table */}
          {result.preview?.length > 0 && (
            <div className="overflow-x-auto max-h-72">
              <table className="min-w-full text-xs">
                <thead className="bg-slate-100 sticky top-0">
                  <tr>{result.columns?.map((c: string) => <th key={c} className="px-3 py-2 text-left font-medium text-slate-600">{c}</th>)}</tr>
                </thead>
                <tbody className="divide-y">
                  {result.preview.slice(0, 20).map((row: any, i: number) => (
                    <tr key={i} className="hover:bg-slate-50">
                      {result.columns?.map((c: string) => <td key={c} className="px-3 py-1.5 text-slate-700">{row[c]}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
