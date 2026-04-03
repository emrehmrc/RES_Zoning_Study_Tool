'use client'

import { useState, useEffect, useCallback } from 'react'
import { apiGet, apiPost, apiDownload, apiRunWithProgress } from '@/lib/api'
import type { ProjectConfig, ScoringLevel } from '@/lib/types'
import ProcessingOverlay from './ProcessingOverlay'

interface Props { config: ProjectConfig; onComplete: () => void; activeTab?: number }

interface LayerScoringConfig {
  type: 'distance_coverage' | 'single_mode'
  column: string
  distance_column?: string
  coverage_column?: string
  max_coverage_threshold?: number
  weight: number
  levels: { min: number; max: number; score: number }[]
  distance_levels?: { min: number; max: number; score: number }[]
}

interface LayerConstraintConfig {
  column: string
  threshold: number
  mode: string
}

interface LayerGroup {
  columns: string[]
  modes: Record<string, string> // mode -> column name
}

export default function LevelScoringTab({ config, onComplete, activeTab }: Props) {
  const [columns, setColumns] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [importLoading, setImportLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState('')

  // Per-column configuration (keyed by layer group name)
  const [layerGroups, setLayerGroups] = useState<Record<string, LayerGroup>>({})
  const [scoringConfigs, setScoringConfigs] = useState<Record<string, LayerScoringConfig>>({})
  const [constraintConfigs, setConstraintConfigs] = useState<Record<string, LayerConstraintConfig>>({})
  const [columnModes, setColumnModes] = useState<Record<string, 'scoring' | 'exclusion' | 'skip'>>({})

  const loadColumns = useCallback(async () => {
    try {
      const r = await apiGet<{ total: number; columns: string[] }>('/analysis/results/?page=1&page_size=1')
      const metaCols = ['cell_id', 'wkt', 'geometry', 'centroid_lat', 'centroid_lon']
      const analysisCols = r.columns.filter((c: string) => !metaCols.includes(c))
      setColumns(analysisCols)

      // Group columns by layer name
      const groups: Record<string, LayerGroup> = {}
      for (const col of analysisCols) {
        let layerName = col
        let mode = 'unknown'
        if (col.endsWith('_dist_km')) { layerName = col.replace(/_dist_km$/, ''); mode = 'distance' }
        else if (col.endsWith('_coverage_pct')) { layerName = col.replace(/_coverage_pct$/, ''); mode = 'coverage' }
        else if (col.endsWith('_mean')) { layerName = col.replace(/_mean$/, ''); mode = 'mean' }
        else if (col.endsWith('_max')) { layerName = col.replace(/_max$/, ''); mode = 'max' }
        else if (col.endsWith('_min')) { layerName = col.replace(/_min$/, ''); mode = 'min' }
        else if (col.endsWith('_median')) { layerName = col.replace(/_median$/, ''); mode = 'median' }
        else if (col.endsWith('_std')) { layerName = col.replace(/_std$/, ''); mode = 'std' }

        if (!groups[layerName]) groups[layerName] = { columns: [], modes: {} }
        groups[layerName].columns.push(col)
        groups[layerName].modes[mode] = col
      }
      setLayerGroups(groups)

      // Initialize configs per layer group
      const modes: Record<string, 'scoring' | 'exclusion' | 'skip'> = {}
      const sConfigs: Record<string, LayerScoringConfig> = {}

      for (const [layerName, group] of Object.entries(groups)) {
        modes[layerName] = 'scoring'

        const defaultLevels = config.scoring_configs[layerName]?.levels
          || config.scoring_configs['default']?.levels
          || [
            { max: 99999, min: 75, score: 100 },
            { max: 75, min: 50, score: 70 },
            { max: 50, min: 25, score: 40 },
            { max: 25, min: 0, score: 10 },
          ]

        const hasDistance = 'distance' in group.modes
        const hasCoverage = 'coverage' in group.modes

        if (hasDistance && hasCoverage) {
          const distLevels = config.scoring_configs['distance']?.levels || defaultLevels
          sConfigs[layerName] = {
            type: 'distance_coverage',
            column: group.modes['distance'],
            distance_column: group.modes['distance'],
            coverage_column: group.modes['coverage'],
            max_coverage_threshold: 5,
            weight: 10,
            levels: distLevels.map((l: ScoringLevel) => ({ ...l })),
          }
        } else {
          const firstMode = Object.keys(group.modes)[0]
          sConfigs[layerName] = {
            type: 'single_mode',
            column: group.modes[firstMode],
            weight: 10,
            levels: defaultLevels.map((l: ScoringLevel) => ({ ...l })),
          }
        }
      }

      setColumnModes(modes)
      setScoringConfigs(sConfigs)
    } catch { /* not ready yet */ }
  }, [config.scoring_configs])

  useEffect(() => { loadColumns() }, [loadColumns])

  // Re-fetch data when this tab (index 2) becomes active
  useEffect(() => {
    if (activeTab === 2) loadColumns()
  }, [activeTab, loadColumns])

  function setMode(col: string, mode: 'scoring' | 'exclusion' | 'skip') {
    setColumnModes(prev => ({ ...prev, [col]: mode }))
    if (mode === 'exclusion' && !constraintConfigs[col]) {
      // Determine default threshold based on mode type
      const group = layerGroups[col]
      const firstMode = group ? Object.keys(group.modes)[0] : 'unknown'
      const firstCol = group ? group.modes[firstMode] : col
      const defaultThreshold = firstMode === 'coverage' ? 50 : firstMode === 'distance' ? 10 : 100
      setConstraintConfigs(prev => ({
        ...prev,
        [col]: { column: firstCol, threshold: defaultThreshold, mode: firstMode },
      }))
    }
  }

  function updateLevel(col: string, idx: number, field: 'min' | 'max' | 'score', value: number) {
    setScoringConfigs(prev => {
      const updated = { ...prev }
      const levels = updated[col].levels.map(l => ({ ...l }))
      levels[idx] = { ...levels[idx], [field]: value }

      // Two-way binding: Level N's min == Level N+1's max
      // When Level N's min changes → update Level N+1's max
      if (field === 'min' && idx < levels.length - 1) {
        levels[idx + 1] = { ...levels[idx + 1], max: value }
      }
      // When Level N's max changes → update Level N-1's min
      if (field === 'max' && idx > 0) {
        levels[idx - 1] = { ...levels[idx - 1], min: value }
      }

      updated[col] = { ...updated[col], levels }
      return updated
    })
  }

  function updateWeight(col: string, weight: number) {
    setScoringConfigs(prev => ({ ...prev, [col]: { ...prev[col], weight } }))
  }

  function updateMaxCoverage(col: string, value: number) {
    setScoringConfigs(prev => ({ ...prev, [col]: { ...prev[col], max_coverage_threshold: value } }))
  }

  async function importCSV(file: File) {
    setImportLoading(true); setError('')
    try {
      const fd = new FormData()
      fd.append('csv_file', file)
      await apiPost('/scoring/import-csv/', fd)
      await loadColumns()
      onComplete()
    } catch (e: any) { setError(e.message) } finally { setImportLoading(false) }
  }

  async function runScoring() {
    setLoading(true); setError(''); setResult(null)
    try {
      const scoring: Record<string, any> = {}
      const constraints: Record<string, any> = {}

      // Validate level ranges before submitting
      for (const [layerName, mode] of Object.entries(columnModes)) {
        if (mode === 'scoring' && scoringConfigs[layerName]) {
          const invalidLevels = scoringConfigs[layerName].levels
            .map((l, i) => (l.min >= l.max ? `Level ${i + 1} (min=${l.min} ≥ max=${l.max})` : null))
            .filter(Boolean)
          if (invalidLevels.length > 0) {
            setError(`"⚠️ ${layerName}": ${invalidLevels.join(', ')} — each level must have min < max.`)
            setLoading(false)
            return
          }
        }
      }

      for (const [layerName, mode] of Object.entries(columnModes)) {
        if (mode === 'scoring' && scoringConfigs[layerName]) {
          const cfg = { ...scoringConfigs[layerName], weight: scoringConfigs[layerName].weight / 100 }
          // For distance_coverage type, backend expects `distance_levels`
          if (cfg.type === 'distance_coverage') {
            cfg.distance_levels = cfg.levels
          }
          scoring[layerName] = cfg
        } else if (mode === 'exclusion' && constraintConfigs[layerName]) {
          constraints[layerName] = constraintConfigs[layerName]
        }
      }

      const res = await apiRunWithProgress(
        '/scoring/run-async/',
        { scoring_config: scoring, constraint_config: constraints },
      )
      setResult(res)
      onComplete()
    } catch (e: any) { setError(e.message) } finally { setLoading(false) }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-slate-800">⚖️ Step 3: Level Scoring</h2>
        <div className="flex gap-2">
          <label className="cursor-pointer px-4 py-1.5 bg-blue-50 text-blue-700 rounded-lg text-sm hover:bg-blue-100">
            📤 Import CSV
            <input type="file" accept=".csv" className="hidden" onChange={e => { if (e.target.files?.[0]) importCSV(e.target.files[0]) }} />
          </label>
        </div>
      </div>
      <hr />

      {importLoading && <p className="text-blue-600 text-sm">⏳ Importing CSV...</p>}

      {columns.length === 0 ? (
        <div className="bg-amber-50 text-amber-700 p-6 rounded-xl border border-amber-200 text-center">
          <p className="font-medium">No analysis data available.</p>
          <p className="text-sm mt-1">Complete Step 2 (Layer Calculation) first, or import a scored CSV.</p>
        </div>
      ) : (
        <>
          {/* Layer group configurations */}
          <div className="space-y-4">
            {Object.entries(layerGroups).map(([layerName, group]) => (
              <div key={layerName} className="bg-white rounded-xl p-5 shadow-sm border">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h4 className="font-medium text-slate-700">{layerName}</h4>
                    <p className="text-xs text-slate-400">Modes: {Object.keys(group.modes).join(', ')}</p>
                  </div>
                  <div className="flex gap-2">
                    {(['scoring', 'exclusion', 'skip'] as const).map(m => (
                      <button key={m} onClick={() => setMode(layerName, m)}
                        className={`px-3 py-1 rounded text-xs ${columnModes[layerName] === m
                          ? m === 'scoring' ? 'bg-blue-600 text-white'
                          : m === 'exclusion' ? 'bg-red-600 text-white'
                          : 'bg-slate-400 text-white'
                        : 'bg-slate-100 text-slate-600'}`}>
                        {m === 'scoring' ? '📊 Scoring' : m === 'exclusion' ? '🚫 Exclusion' : '⏭️ Skip'}
                      </button>
                    ))}
                  </div>
                </div>

                {columnModes[layerName] === 'scoring' && scoringConfigs[layerName] && (
                  <div className="space-y-4">
                    {/* Weight & Coverage threshold */}
                    <div className="flex gap-6 items-end">
                      <label className="text-sm text-slate-600">
                        Layer Weight (%):
                        <input type="number" min={0} max={100} step={1}
                          value={scoringConfigs[layerName].weight}
                          onChange={e => updateWeight(layerName, +e.target.value)}
                          className="ml-2 w-20 border rounded p-1.5 text-sm" />
                      </label>
                      {scoringConfigs[layerName].type === 'distance_coverage' && (
                        <label className="text-sm text-slate-600">
                          Max Coverage for Distance Scoring (%):
                          <input type="number" min={0} max={100} step={0.5}
                            value={scoringConfigs[layerName].max_coverage_threshold ?? 5}
                            onChange={e => updateMaxCoverage(layerName, +e.target.value)}
                            className="ml-2 w-20 border rounded p-1.5 text-sm" />
                          <span className="ml-1 text-xs text-slate-400 cursor-help" title="If coverage > this value, distance scoring will be skipped">ⓘ</span>
                        </label>
                      )}
                    </div>

                    {/* Level cards — 4 columns like original Streamlit */}
                    <div>
                      <p className="text-xs font-medium text-slate-500 mb-2">
                        {scoringConfigs[layerName].type === 'distance_coverage' ? '📏 Distance Scoring Levels (used when coverage ≤ max)' : '📈 Scoring Levels'}
                      </p>
                      <div className="grid grid-cols-4 gap-3">
                        {scoringConfigs[layerName].levels.map((lv, i) => {
                          const invalid = lv.min >= lv.max
                          return (
                          <div key={i} className={`rounded-lg p-3 border space-y-2 ${invalid ? 'bg-red-50 border-red-300' : 'bg-slate-50'}`}>
                            <div className="flex items-center justify-between">
                              <p className="text-xs font-semibold text-slate-600">Level {i + 1}</p>
                              {invalid && <span className="text-xs text-red-500 font-medium">min ≥ max</span>}
                            </div>
                            <label className="block text-xs text-slate-500">
                              Max
                              <input type="number" step="any" value={lv.max}
                                onChange={e => updateLevel(layerName, i, 'max', +e.target.value)}
                                className={`w-full border rounded p-1.5 text-sm mt-0.5 ${invalid ? 'border-red-400 bg-red-50' : ''}`} />
                            </label>
                            <label className="block text-xs text-slate-500">
                              Min
                              <input type="number" step="any" value={lv.min}
                                onChange={e => updateLevel(layerName, i, 'min', +e.target.value)}
                                className={`w-full border rounded p-1.5 text-sm mt-0.5 ${invalid ? 'border-red-400 bg-red-50' : ''}`} />
                            </label>
                            <label className="block text-xs text-slate-500">
                              Score
                              <input type="number" step={1} min={0} max={100} value={lv.score}
                                onChange={e => updateLevel(layerName, i, 'score', +e.target.value)}
                                className="w-full border rounded p-1.5 text-sm mt-0.5" />
                            </label>
                          </div>
                        )})}
                      </div>
                    </div>
                  </div>
                )}

                {columnModes[layerName] === 'exclusion' && constraintConfigs[layerName] && (
                  <div className="space-y-3">
                    <p className="text-xs text-red-600">🚫 Cells exceeding the maximum threshold will have final score = 0</p>
                    {Object.keys(group.modes).length > 1 && (
                      <label className="text-sm text-slate-600">
                        Metric:
                        <select value={constraintConfigs[layerName].mode}
                          onChange={e => {
                            const m = e.target.value
                            setConstraintConfigs(prev => ({
                              ...prev,
                              [layerName]: { ...prev[layerName], mode: m, column: group.modes[m] },
                            }))
                          }}
                          className="ml-2 border rounded p-1.5 text-sm">
                          {Object.keys(group.modes).map(m => <option key={m} value={m}>{m}</option>)}
                        </select>
                      </label>
                    )}
                    <label className="flex items-center gap-3 text-sm text-slate-600">
                      Maximum Allowed Value:
                      <input type="number" value={constraintConfigs[layerName].threshold}
                        onChange={e => setConstraintConfigs(prev => ({
                          ...prev,
                          [layerName]: { ...prev[layerName], threshold: +e.target.value },
                        }))}
                        className="w-24 border rounded p-1.5 text-sm" />
                    </label>
                    <p className="text-xs text-slate-400">
                      Constraint: {constraintConfigs[layerName].column} ≤ {constraintConfigs[layerName].threshold}
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>

          <button onClick={runScoring} disabled={loading}
            className="w-full py-3 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 disabled:opacity-50 transition">
            {loading ? '⏳ Calculating Scores...' : '🚀 Run Level Scoring'}
          </button>

          {/* Processing Animation */}
          {loading && (
            <div className="mt-3">
              <ProcessingOverlay message="Calculating level scores..." accentColor="purple" />
            </div>
          )}
        </>
      )}

      {error && <div className="bg-red-50 text-red-700 p-4 rounded-lg border border-red-200">{error}</div>}

      {/* Results */}
      {result && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl p-6 shadow-sm border">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-emerald-700">✅ {result.message}</h3>
              <button onClick={() => apiDownload('/scoring/download/', 'final_scored_analysis.csv')}
                className="text-sm px-4 py-1.5 bg-slate-100 rounded-lg hover:bg-slate-200">📥 Download</button>
            </div>

            {/* Score Distribution */}
            {result.score_distribution && (
              <div className="grid grid-cols-3 md:grid-cols-6 gap-2 mb-4">
                {[
                  { key: 'excellent', label: '🌟 Excellent (≥80)', color: 'bg-emerald-50 text-emerald-700' },
                  { key: 'good', label: '👍 Good (60-80)', color: 'bg-green-50 text-green-700' },
                  { key: 'fair', label: '📊 Fair (40-60)', color: 'bg-yellow-50 text-yellow-700' },
                  { key: 'poor', label: '⚠️ Poor (20-40)', color: 'bg-orange-50 text-orange-700' },
                  { key: 'very_poor', label: '❌ Very Poor (<20)', color: 'bg-red-50 text-red-600' },
                  { key: 'excluded', label: '🚫 Excluded', color: 'bg-slate-100 text-slate-600' },
                ].map(item => (
                  <div key={item.key} className={`${item.color} rounded-lg p-3 text-center`}>
                    <p className="text-lg font-bold">{result.score_distribution[item.key]?.toLocaleString()}</p>
                    <p className="text-xs mt-0.5">{item.label}</p>
                  </div>
                ))}
              </div>
            )}

            <div className="flex gap-4 text-sm text-slate-600">
              <span>Total: <strong>{result.total_cells?.toLocaleString()}</strong></span>
              <span>Excluded: <strong>{result.excluded_cells?.toLocaleString()}</strong></span>
              <span>Avg Score: <strong>{result.avg_score}</strong></span>
            </div>
          </div>

          {/* Exclusion tracking */}
          {result.exclusion_tracking?.length > 0 && (
            <div className="bg-white rounded-xl p-6 shadow-sm border">
              <h4 className="font-medium text-slate-700 mb-2">Exclusion Summary</h4>
              <div className="space-y-1">
                {result.exclusion_tracking.map((t: any, i: number) => (
                  <div key={i} className="flex justify-between text-sm">
                    <span>{t.layer} ({t.column} &gt; {t.threshold})</span>
                    <span className="text-red-600 font-medium">{t.excluded_count.toLocaleString()} excluded</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Preview */}
          {result.preview?.length > 0 && (
            <div className="bg-white rounded-xl p-6 shadow-sm border overflow-x-auto max-h-64">
              <table className="min-w-full text-xs">
                <thead className="bg-slate-100 sticky top-0">
                  <tr>{Object.keys(result.preview[0]).map(c => <th key={c} className="px-2 py-1.5 text-left font-medium text-slate-600 whitespace-nowrap">{c}</th>)}</tr>
                </thead>
                <tbody className="divide-y">
                  {result.preview.map((row: any, i: number) => (
                    <tr key={i} className="hover:bg-slate-50">
                      {Object.values(row).map((v: any, j) => <td key={j} className="px-2 py-1 whitespace-nowrap">{typeof v === 'number' ? Math.round(v * 100) / 100 : v}</td>)}
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
