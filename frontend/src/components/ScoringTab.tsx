'use client'

import { useState, useEffect, useCallback } from 'react'
import { apiGet, apiPost, apiDelete, apiDownload, apiRunWithProgress } from '@/lib/api'
import type { ProjectConfig, LayerConfig } from '@/lib/types'
import ProcessingOverlay from './ProcessingOverlay'
import FileBrowserModal from './FileBrowserModal'

interface Props { config: ProjectConfig; onComplete: () => void }

/* ────────── Main Component ────────── */
export default function ScoringTab({ config, onComplete }: Props) {
  const [layers, setLayers] = useState<LayerConfig[]>([])
  const [loading, setLoading] = useState(false)
  const [analysisResult, setAnalysisResult] = useState<any>(null)
  const [error, setError] = useState('')

  // File browser
  const [showFileBrowser, setShowFileBrowser] = useState(false)

  // New layer form
  const [layerMode, setLayerMode] = useState<'predefined' | 'custom'>('predefined')
  const [selectedLayer, setSelectedLayer] = useState('')
  const [customName, setCustomName] = useState('')
  const [rasterPath, setRasterPath] = useState('')
  const [selectedModes, setSelectedModes] = useState<string[]>(['mean'])
  const [targetValue, setTargetValue] = useState(1)

  const refreshLayers = useCallback(async () => {
    try {
      const r = await apiGet<{ layers: LayerConfig[] }>('/layers/')
      setLayers(r.layers)
    } catch { /* ignore */ }
  }, [])

  useEffect(() => { refreshLayers() }, [refreshLayers])

  async function addLayer() {
    setError('')
    const name = layerMode === 'predefined' ? selectedLayer : customName
    const modes = layerMode === 'predefined'
      ? (config.predefined_layer_modes[selectedLayer] || ['mean'])
      : selectedModes

    if (!name || !rasterPath) { setError('Layer name and raster path are required.'); return }

    try {
      await apiPost('/layers/add/', {
        layer_name: name,
        raster_path: rasterPath,
        analysis_modes: modes,
        target_value: targetValue,
        is_predefined: layerMode === 'predefined',
      })
      await refreshLayers()
      setSelectedLayer(''); setCustomName(''); setRasterPath('')
      onComplete()
    } catch (e: any) { setError(e.message) }
  }

  async function removeLayer(idx: number) {
    try {
      await apiDelete(`/layers/${idx}/remove/`)
      await refreshLayers()
      onComplete()
    } catch (e: any) { setError(e.message) }
  }

  async function runAnalysis() {
    setLoading(true); setError(''); setAnalysisResult(null)
    try {
      const res = await apiRunWithProgress(
        '/analysis/run-async/',
        {},
      )
      setAnalysisResult(res)
      onComplete()
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  function toggleMode(m: string) {
    setSelectedModes(prev => prev.includes(m) ? prev.filter(x => x !== m) : [...prev, m])
  }

  const usedNames = layers.map(l => l.prefix)
  const availableLayers = config.all_layer_names.filter(n => !usedNames.includes(n))

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-800">🎯 Step 2: Layer Calculation</h2>
      <hr />

      {/* Add Layer Form */}
      <div className="bg-white rounded-xl p-6 shadow-sm border space-y-4">
        <h3 className="font-semibold text-slate-700">➕ Add New Layer</h3>

        <div className="flex gap-3">
          {(['predefined', 'custom'] as const).map(m => (
            <button key={m} onClick={() => setLayerMode(m)}
              className={`px-4 py-1.5 rounded text-sm ${layerMode === m ? 'bg-blue-100 text-blue-700 font-medium' : 'bg-slate-100 text-slate-600'}`}>
              {m === 'predefined' ? 'Predefined List' : 'Custom Layer'}
            </button>
          ))}
        </div>

        {/* Raster file picker — browse server filesystem, no upload */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-slate-600">Raster File (.tif)</label>
          <div className="flex gap-2 items-center">
            <button
              onClick={() => setShowFileBrowser(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 whitespace-nowrap"
            >
              📂 Choose File
            </button>
            {rasterPath && (
              <span className="text-sm text-emerald-700 truncate">✓ {rasterPath.split(/[\\/]/).pop()}</span>
            )}
          </div>
          <input
            placeholder="Or paste full path manually, e.g. C:\data\layer.tif"
            value={rasterPath}
            onChange={e => setRasterPath(e.target.value)}
            className="w-full border rounded-lg p-2 text-sm"
          />
        </div>
        {showFileBrowser && (
          <FileBrowserModal
            onSelect={(path) => setRasterPath(path)}
            onClose={() => setShowFileBrowser(false)}
          />
        )}

        {/* Layer name */}
        {layerMode === 'predefined' ? (
          <div>
            <label className="text-sm font-medium text-slate-600">Layer Name</label>
            <select value={selectedLayer} onChange={e => setSelectedLayer(e.target.value)}
              className="w-full border rounded-lg p-2.5 text-sm mt-1">
              <option value="">-- Select layer --</option>
              {availableLayers.map(l => <option key={l} value={l}>{l}</option>)}
            </select>
            {selectedLayer && (
              <p className="text-xs text-blue-600 mt-1">
                Modes: {(config.predefined_layer_modes[selectedLayer] || []).join(', ')}
              </p>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            <label className="text-sm font-medium text-slate-600">Custom Layer Name
              <input value={customName} onChange={e => setCustomName(e.target.value)}
                className="mt-1 w-full border rounded-lg p-2 text-sm" placeholder="e.g. My Custom Layer" />
            </label>
            <div>
              <label className="text-sm font-medium text-slate-600">Analysis Modes</label>
              <div className="flex flex-wrap gap-2 mt-1">
                {['distance', 'coverage', 'mean', 'max', 'min', 'median', 'std'].map(m => (
                  <button key={m} onClick={() => toggleMode(m)}
                    className={`px-3 py-1 rounded-full text-xs ${selectedModes.includes(m) ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600'}`}>
                    {m}
                  </button>
                ))}
              </div>
            </div>
            {(selectedModes.includes('distance') || selectedModes.includes('coverage')) && (
              <label className="text-sm text-slate-600">Target Pixel Value
                <input type="number" value={targetValue} onChange={e => setTargetValue(+e.target.value)}
                  className="mt-1 w-full border rounded-lg p-2 text-sm" min={0} max={255} />
              </label>
            )}
          </div>
        )}

        <button onClick={addLayer}
          className="w-full py-2.5 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition text-sm">
          ➕ Add Layer
        </button>
      </div>

      {/* Configured Layers */}
      {layers.length > 0 && (
        <div className="bg-white rounded-xl p-6 shadow-sm border space-y-3">
          <h3 className="font-semibold text-slate-700">🗂️ Configured Layers ({layers.length})</h3>
          {layers.map((l, i) => (
            <div key={i} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border">
              <div>
                <span className="text-sm font-medium">{l.is_predefined ? '🏷️' : '🔧'} {l.prefix}</span>
                <p className="text-xs text-slate-500">{l.analysis_modes.join(', ')} — {l.path.split(/[\\/]/).pop()}</p>
              </div>
              <button onClick={() => removeLayer(i)} className="text-red-500 hover:text-red-700 text-lg">×</button>
            </div>
          ))}

          <button onClick={runAnalysis} disabled={loading}
            className="w-full py-3 bg-emerald-600 text-white rounded-lg font-semibold hover:bg-emerald-700 disabled:opacity-50 transition mt-2">
            {loading ? '⏳ Running Analysis...' : '🚀 Run Analysis'}
          </button>

          {/* Processing Animation */}
          {loading && (
            <div className="mt-3">
              <ProcessingOverlay message="Running layer analysis..." accentColor="emerald" />
            </div>
          )}
        </div>
      )}

      {error && <div className="bg-red-50 text-red-700 p-4 rounded-lg border border-red-200">{error}</div>}

      {/* Results */}
      {analysisResult && (
        <div className="bg-white rounded-xl p-6 shadow-sm border space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-emerald-700">✅ {analysisResult.message}</h3>
            <button onClick={() => apiDownload('/analysis/download/', 'raster_analysis_results.csv')}
              className="text-sm px-4 py-1.5 bg-slate-100 rounded-lg hover:bg-slate-200">📥 Download</button>
          </div>

          {/* Statistics */}
          {analysisResult.statistics && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {Object.entries(analysisResult.statistics as Record<string, any>).map(([col, stats]: [string, any]) => (
                <div key={col} className="bg-slate-50 rounded-lg p-3 border">
                  <p className="text-xs text-slate-500 truncate">{col}</p>
                  <p className="text-sm font-semibold">avg: {stats.mean}</p>
                  <p className="text-xs text-slate-400">{stats.min} – {stats.max}</p>
                </div>
              ))}
            </div>
          )}

          {/* Preview */}
          {analysisResult.preview?.length > 0 && (
            <div className="overflow-x-auto max-h-64">
              <table className="min-w-full text-xs">
                <thead className="bg-slate-100 sticky top-0">
                  <tr>{analysisResult.columns?.map((c: string) => <th key={c} className="px-2 py-1.5 text-left font-medium text-slate-600 whitespace-nowrap">{c}</th>)}</tr>
                </thead>
                <tbody className="divide-y">
                  {analysisResult.preview.slice(0, 15).map((row: any, i: number) => (
                    <tr key={i} className="hover:bg-slate-50">
                      {analysisResult.columns?.map((c: string) => <td key={c} className="px-2 py-1 text-slate-700 whitespace-nowrap">{typeof row[c] === 'number' ? Math.round(row[c] * 1000) / 1000 : row[c]}</td>)}
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
