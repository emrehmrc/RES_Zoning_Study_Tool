'use client'

import { useState, useEffect, useCallback } from 'react'
import { apiGet, apiPost, apiDownload, apiRunWithProgress } from '@/lib/api'
import type { ProjectConfig, ScoringLevel } from '@/lib/types'
import ProcessingOverlay from './ProcessingOverlay'
import AnalysisResultsTable from './AnalysisResultsTable'

interface Props { config: ProjectConfig; onComplete: () => void; activeTab?: number }

// Detects layers that belong to kV transmission infrastructure (used for Tab 4 connection scoring)
function isKvConnectionLayer(name: string): boolean {
  return /\b(110|220|400)\s*kv/i.test(name) && /line|substation/i.test(name)
}

interface LayerScoringConfig {
  type: 'distance_coverage' | 'single_mode' | 'bathymetry_dual' | 'seabed_categorical'
  column: string
  distance_column?: string
  coverage_column?: string
  max_coverage_threshold?: number
  weight: number
  levels: { min: number; max: number; score: number }[]
  distance_levels?: { min: number; max: number; score: number }[]
  normalize_by_max?: boolean
  // bathymetry_dual specific
  depth_threshold?: number
  depth_column?: string           // which column holds depth values (for wind/slope it's Bathymetry _max)
  bottom_fixed_levels?: { min: number; max: number; score: number }[]
  floating_levels?: { min: number; max: number; score: number }[]
  // seabed_categorical specific
  category_scores?: Record<string, number>  // e.g. { sand: 100, gravel: 70, ... }
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
  const [columnModes, setColumnModes] = useState<Record<string, 'scoring' | 'exclusion' | 'skip' | 'connection'>>({})

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
        else if (col.endsWith('_dominant')) { layerName = col.replace(/_dominant$/, ''); mode = 'seabed_dominant' }
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
        // For kV connection layers, default mode is fixed at 'connection'
      modes[layerName] = isKvConnectionLayer(layerName) ? 'connection' as any : 'scoring'

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

        // Any layer whose config entry has type='bathymetry_dual' (Bathymetry, Wind Speed, Slope in OffShore mode)
        // uses the depth-threshold dual scoring: ≤threshold → bottom_fixed_levels, >threshold → floating_levels
        const layerCfgRaw = config.scoring_configs[layerName] as any
        const isDualMode = layerCfgRaw?.type === 'bathymetry_dual'
        const isSeabedCat = layerCfgRaw?.type === 'seabed_categorical'
          || ('seabed_dominant' in group.modes)

        if (isSeabedCat) {
          const dominantCol = group.modes['seabed_dominant'] ?? Object.values(group.modes)[0]
          const defaultCatScores = { sand: 100, gravel: 70, 'rack/bad rack/mud': 40, 'boulder/stony/silt': 0 }
          sConfigs[layerName] = {
            type: 'seabed_categorical',
            column: dominantCol,
            weight: layerCfgRaw?.weight ?? 10,
            levels: [],
            depth_threshold: layerCfgRaw?.depth_threshold ?? 60,
            category_scores: layerCfgRaw?.category_scores ?? defaultCatScores,
          }
        } else if (isDualMode) {
          const firstMode = Object.keys(group.modes)[0]
          // Prefer mean column for wind/slope; max column for bathymetry
          const preferredCol = group.modes['mean'] ?? group.modes['max'] ?? group.modes[firstMode]
          // For non-bathymetry dual layers (wind, slope), depth is taken from the Bathymetry _max column
          const isBathLayer = layerName.toLowerCase().includes('bathymetry')
          sConfigs[layerName] = {
            type: 'bathymetry_dual',
            column: preferredCol,
            weight: layerCfgRaw?.weight ?? 10,
            levels: [],
            depth_threshold: layerCfgRaw?.depth_threshold ?? 60,
            depth_column: isBathLayer ? preferredCol : undefined, // resolved at scoring send time
            bottom_fixed_levels: (layerCfgRaw?.bottom_fixed_levels ?? []).map((l: ScoringLevel) => ({ ...l })),
            floating_levels: (layerCfgRaw?.floating_levels ?? []).map((l: ScoringLevel) => ({ ...l })),
          }
        } else if (hasDistance && hasCoverage) {
          const distLevels = config.scoring_configs[layerName]?.levels
            || config.scoring_configs['distance']?.levels || defaultLevels
          sConfigs[layerName] = {
            type: 'distance_coverage',
            column: group.modes['distance'],
            distance_column: group.modes['distance'],
            coverage_column: group.modes['coverage'],
            max_coverage_threshold: 5,
            weight: config.scoring_configs[layerName]?.weight ?? 10,
            levels: distLevels.map((l: ScoringLevel) => ({ ...l })),
          }
        } else {
          const firstMode = Object.keys(group.modes)[0]
          sConfigs[layerName] = {
            type: 'single_mode',
            column: group.modes[firstMode],
            weight: config.scoring_configs[layerName]?.weight ?? 10,
            levels: defaultLevels.map((l: ScoringLevel) => ({ ...l })),
            normalize_by_max: config.scoring_configs[layerName]?.normalize_by_max ?? false,
          }
        }
      }

      // Preserve user-edited weights/levels for layers that already exist in state;
      // only apply defaults for brand-new layers (e.g. after a new analysis run).
      setColumnModes(prev => {
        const merged: Record<string, 'scoring' | 'exclusion' | 'skip' | 'connection'> = {}
        for (const name of Object.keys(modes)) {
          // kV layers are always 'connection' — ignore any previous mode
          merged[name] = isKvConnectionLayer(name) ? 'connection' : (prev[name] ?? modes[name] as any)
        }
        return merged
      })
      setScoringConfigs(prev => {
        const merged: Record<string, LayerScoringConfig> = {}
        for (const [name, cfg] of Object.entries(sConfigs)) {
          if (prev[name]) {
            // Layer already known — keep whatever the user set
            merged[name] = {
              ...cfg,
              weight: prev[name].weight,
              levels: prev[name].levels,
              ...(cfg.type === 'distance_coverage' && prev[name].distance_levels
                ? { distance_levels: prev[name].distance_levels }
                : {}),
              ...(cfg.max_coverage_threshold !== undefined && prev[name].max_coverage_threshold !== undefined
                ? { max_coverage_threshold: prev[name].max_coverage_threshold }
                : {}),
              ...(cfg.type === 'bathymetry_dual' ? {
                depth_threshold: prev[name].depth_threshold ?? cfg.depth_threshold,
                bottom_fixed_levels: prev[name].bottom_fixed_levels ?? cfg.bottom_fixed_levels,
                floating_levels: prev[name].floating_levels ?? cfg.floating_levels,
              } : {}),
              ...(cfg.type === 'seabed_categorical' ? {
                depth_threshold: prev[name].depth_threshold ?? cfg.depth_threshold,
                category_scores: prev[name].category_scores ?? cfg.category_scores,
              } : {}),
            }
          } else {
            merged[name] = cfg
          }
        }
        return merged
      })
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

  function updateDepthThreshold(col: string, value: number) {
    setScoringConfigs(prev => ({ ...prev, [col]: { ...prev[col], depth_threshold: value } }))
  }

  function updateBathyLevel(col: string, section: 'bottom_fixed_levels' | 'floating_levels', idx: number, field: 'min' | 'max' | 'score', value: number) {
    setScoringConfigs(prev => {
      const cfg = prev[col]
      if (!cfg) return prev
      const levels = (cfg[section] || []).map((l: any) => ({ ...l }))
      levels[idx] = { ...levels[idx], [field]: value }
      if (field === 'min' && idx < levels.length - 1) levels[idx + 1] = { ...levels[idx + 1], max: value }
      if (field === 'max' && idx > 0) levels[idx - 1] = { ...levels[idx - 1], min: value }
      return { ...prev, [col]: { ...cfg, [section]: levels } }
    })
  }

  function updateCategoryScore(col: string, cat: string, value: number) {
    setScoringConfigs(prev => ({
      ...prev,
      [col]: { ...prev[col], category_scores: { ...(prev[col].category_scores ?? {}), [cat]: value } }
    }))
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

  // Non-kV scoring layers (Tab 3 only)
  const scoringLayerWeights = Object.entries(columnModes)
    .filter(([, m]) => m === 'scoring')
    .map(([name]) => ({ name, weight: scoringConfigs[name]?.weight ?? 0 }))
  // kV connection layers (contribute to Tab 4, but their weight counts toward 100%)
  const kvLayerWeights = Object.entries(columnModes)
    .filter(([, m]) => (m as string) === 'connection')
    .map(([name]) => ({ name, weight: scoringConfigs[name]?.weight ?? 0 }))
  const allLayerWeights = [...scoringLayerWeights, ...kvLayerWeights]
  const totalWeight = allLayerWeights.reduce((s, l) => s + l.weight, 0)
  const weightOk = allLayerWeights.length === 0 || Math.abs(totalWeight - 100) < 0.01

  function distributeWeightsEvenly() {
    const n = allLayerWeights.length
    if (n === 0) return
    const even = Math.round(100 / n)
    const remainder = 100 - even * n
    setScoringConfigs(prev => {
      const updated = { ...prev }
      allLayerWeights.forEach(({ name }, i) => {
        updated[name] = { ...updated[name], weight: even + (i === 0 ? remainder : 0) }
      })
      return updated
    })
  }

  async function runScoring() {
    setLoading(true); setError(''); setResult(null)
    document.body.style.cursor = 'wait'
    try {
      const scoring: Record<string, any> = {}
      const constraints: Record<string, any> = {}

      // Validate level ranges before submitting
      for (const [layerName, mode] of Object.entries(columnModes)) {
        if (mode === 'scoring' && scoringConfigs[layerName]) {
          const cfg = scoringConfigs[layerName]
          if (cfg.type === 'seabed_categorical') {
            continue  // no numeric levels to validate
          } else if (cfg.type === 'bathymetry_dual') {
            const checkLevels = (lvls: any[], label: string) => {
              const inv = (lvls || []).map((l, i) => l.min >= l.max ? `${label} Level ${i + 1} (min=${l.min} ≥ max=${l.max})` : null).filter(Boolean)
              return inv
            }
            const invalid = [
              ...checkLevels(cfg.bottom_fixed_levels || [], 'Bottom Fixed'),
              ...checkLevels(cfg.floating_levels || [], 'Floating'),
            ]
            if (invalid.length > 0) {
              setError(`"⚠️ ${layerName}": ${invalid.join(', ')} — each level must have min < max.`)
              setLoading(false)
              return
            }
          } else {
            const invalidLevels = cfg.levels
              .map((l, i) => (l.min >= l.max ? `Level ${i + 1} (min=${l.min} ≥ max=${l.max})` : null))
              .filter(Boolean)
            if (invalidLevels.length > 0) {
              setError(`"⚠️ ${layerName}": ${invalidLevels.join(', ')} — each level must have min < max.`)
              setLoading(false)
              return
            }
          }
        }
      }

      // Validate weight sum
      if (allLayerWeights.length > 0 && !weightOk) {
        const lines = allLayerWeights.map(({ name, weight }) => `  • ${name}: ${weight}%`).join('\n')
        setError(
          `⚠️ Layer weights must sum to 100%.\n\nCurrent weights:\n${lines}\n\nTotal: ${totalWeight}%\n\n` +
          `Please adjust the weights or use the "Distribute Evenly" button.`
        )
        setLoading(false)
        return
      }

      for (const [layerName, mode] of Object.entries(columnModes)) {
        if (mode === 'scoring' && scoringConfigs[layerName]) {
          const cfg = { ...scoringConfigs[layerName], weight: scoringConfigs[layerName].weight / 100 }
          // For distance_coverage type, backend expects `distance_levels`
          if (cfg.type === 'distance_coverage') {
            cfg.distance_levels = cfg.levels
          }
          // For bathymetry_dual non-bathymetry layers, resolve depth_column from available columns
          if (cfg.type === 'bathymetry_dual' && !cfg.depth_column) {
            // Find the Bathymetry _max column in analysed data
            const bathMaxCol = columns.find(c => c.toLowerCase().includes('bathymetry') && c.endsWith('_max'))
            if (bathMaxCol) cfg.depth_column = bathMaxCol
          }
          // For seabed_categorical, resolve depth_column from Bathymetry _max column
          if (cfg.type === 'seabed_categorical' && !cfg.depth_column) {
            const bathMaxCol = columns.find(c => c.toLowerCase().includes('bathymetry') && c.endsWith('_max'))
            if (bathMaxCol) cfg.depth_column = bathMaxCol
          }
          scoring[layerName] = cfg
        } else if (mode === 'exclusion' && constraintConfigs[layerName]) {
          constraints[layerName] = constraintConfigs[layerName]
        }
      }

      // Collect kV layer weights (for Tab 4 connection scoring)
      const kvWeights: Record<string, number> = {}
      for (const [layerName, mode] of Object.entries(columnModes)) {
        if ((mode as string) === 'connection' && scoringConfigs[layerName]) {
          kvWeights[layerName] = scoringConfigs[layerName].weight / 100
        }
      }

      const res = await apiRunWithProgress(
        '/scoring/run-async/',
        { scoring_config: scoring, constraint_config: constraints, kv_weights: kvWeights },
      )
      // Fetch all rows for the data table
      try {
        const full = await apiGet<{ data: any[]; columns: string[] }>('/scoring/results/?page=1&page_size=100000')
        res.preview = full.data
        res.previewColumns = full.columns
      } catch { /* keep original preview if full fetch fails */ }
      setResult(res)
      onComplete()
    } catch (e: any) { setError(e.message) } finally { setLoading(false); document.body.style.cursor = '' }
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
                {isKvConnectionLayer(layerName) ? (
                  <div className="flex items-center justify-between">
                    <h4 className="font-medium text-slate-700">{layerName}</h4>
                    <div className="flex items-center gap-4">
                      <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">🔌 Connection Layer (Tab 4)</span>
                      <label className="text-sm text-slate-600 flex items-center">
                        Weight for Tab 4 (%):
                        <input type="number" min={0} max={100} step={1}
                          value={scoringConfigs[layerName]?.weight ?? 10}
                          onChange={e => updateWeight(layerName, +e.target.value)}
                          className="ml-2 w-20 border rounded p-1.5 text-sm" />
                      </label>
                    </div>
                  </div>
                ) : (
                  <>
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
                        {scoringConfigs[layerName].type === 'bathymetry_dual' && (
                          <div className="flex items-center gap-4 flex-wrap">
                            <label className="text-sm text-slate-600">
                              Depth Threshold (m):
                              <input type="number" min={0} step={1}
                                value={scoringConfigs[layerName].depth_threshold ?? 60}
                                onChange={e => updateDepthThreshold(layerName, +e.target.value)}
                                className="ml-2 w-24 border rounded p-1.5 text-sm" />
                              <span className="ml-1 text-xs text-slate-400 cursor-help" title="Cells with depth ≤ threshold use Bottom Fixed scoring; deeper cells use Floating scoring">ⓘ</span>
                            </label>
                            {!layerName.toLowerCase().includes('bathymetry') && (
                              <span className="text-xs text-slate-400 italic">
                                Depth read from Bathymetry layer
                              </span>
                            )}
                          </div>
                        )}
                        {scoringConfigs[layerName].type === 'seabed_categorical' && (
                          <div className="flex items-center gap-4 flex-wrap">
                            <label className="text-sm text-slate-600">
                              Depth Threshold (m):
                              <input type="number" min={0} step={1}
                                value={scoringConfigs[layerName].depth_threshold ?? 60}
                                onChange={e => updateDepthThreshold(layerName, +e.target.value)}
                                className="ml-2 w-24 border rounded p-1.5 text-sm" />
                              <span className="ml-1 text-xs text-slate-400 cursor-help" title="Cells deeper than threshold are floating and not scored by seabed">ⓘ</span>
                            </label>
                            <span className="text-xs text-slate-400 italic">Depth read from Bathymetry layer</span>
                          </div>
                        )}
                      </div>

                      {/* Seabed categorical — category score cards */}
                      {scoringConfigs[layerName].type === 'seabed_categorical' ? (
                        <div className="space-y-3">
                          <p className="text-xs font-medium text-amber-600 mb-2">🪨 Seabed Category Scores (bottom-fixed only)</p>
                          <div className="grid grid-cols-4 gap-3">
                            {Object.entries(scoringConfigs[layerName].category_scores ?? {}).map(([cat, score]) => (
                              <div key={cat} className="rounded-lg p-3 bg-amber-50 border border-amber-200 space-y-2">
                                <p className="text-xs font-semibold text-slate-600 truncate" title={cat}>{cat}</p>
                                <label className="block text-xs text-slate-500">Score
                                  <input type="number" min={0} max={100} step={1} value={score as number}
                                    onChange={e => updateCategoryScore(layerName, cat, +e.target.value)}
                                    className="w-full border rounded p-1.5 text-sm mt-0.5" />
                                </label>
                              </div>
                            ))}
                          </div>
                        </div>
                      ) : scoringConfigs[layerName].type === 'bathymetry_dual' ? (
                        <div className="space-y-4">
                          {/* Bottom Fixed */}
                          <div>
                            <p className="text-xs font-medium text-blue-600 mb-2">
                              ⚓ Bottom Fixed — depth ≤ {scoringConfigs[layerName].depth_threshold ?? 60} m
                            </p>
                            <div className="grid grid-cols-4 gap-3">
                              {(scoringConfigs[layerName].bottom_fixed_levels || []).map((lv, i) => {
                                const invalid = lv.min >= lv.max
                                return (
                                  <div key={i} className={`rounded-lg p-3 border space-y-2 ${invalid ? 'bg-red-50 border-red-300' : 'bg-blue-50 border-blue-200'}`}>
                                    <div className="flex items-center justify-between">
                                      <p className="text-xs font-semibold text-slate-600">Level {i + 1}</p>
                                      {invalid && <span className="text-xs text-red-500 font-medium">min ≥ max</span>}
                                    </div>
                                    <label className="block text-xs text-slate-500">Max
                                      <input type="number" step="any" value={lv.max}
                                        onChange={e => updateBathyLevel(layerName, 'bottom_fixed_levels', i, 'max', +e.target.value)}
                                        className={`w-full border rounded p-1.5 text-sm mt-0.5 ${invalid ? 'border-red-400 bg-red-50' : ''}`} />
                                    </label>
                                    <label className="block text-xs text-slate-500">Min
                                      <input type="number" step="any" value={lv.min}
                                        onChange={e => updateBathyLevel(layerName, 'bottom_fixed_levels', i, 'min', +e.target.value)}
                                        className={`w-full border rounded p-1.5 text-sm mt-0.5 ${invalid ? 'border-red-400 bg-red-50' : ''}`} />
                                    </label>
                                    <label className="block text-xs text-slate-500">Score
                                      <input type="number" step={1} min={0} max={100} value={lv.score}
                                        onChange={e => updateBathyLevel(layerName, 'bottom_fixed_levels', i, 'score', +e.target.value)}
                                        className="w-full border rounded p-1.5 text-sm mt-0.5" />
                                    </label>
                                  </div>
                                )
                              })}
                            </div>
                          </div>
                          {/* Floating */}
                          <div>
                            <p className="text-xs font-medium text-cyan-600 mb-2">
                              🌊 Floating — depth &gt; {scoringConfigs[layerName].depth_threshold ?? 60} m
                            </p>
                            <div className="grid grid-cols-4 gap-3">
                              {(scoringConfigs[layerName].floating_levels || []).map((lv, i) => {
                                const invalid = lv.min >= lv.max
                                return (
                                  <div key={i} className={`rounded-lg p-3 border space-y-2 ${invalid ? 'bg-red-50 border-red-300' : 'bg-cyan-50 border-cyan-200'}`}>
                                    <div className="flex items-center justify-between">
                                      <p className="text-xs font-semibold text-slate-600">Level {i + 1}</p>
                                      {invalid && <span className="text-xs text-red-500 font-medium">min ≥ max</span>}
                                    </div>
                                    <label className="block text-xs text-slate-500">Max
                                      <input type="number" step="any" value={lv.max}
                                        onChange={e => updateBathyLevel(layerName, 'floating_levels', i, 'max', +e.target.value)}
                                        className={`w-full border rounded p-1.5 text-sm mt-0.5 ${invalid ? 'border-red-400 bg-red-50' : ''}`} />
                                    </label>
                                    <label className="block text-xs text-slate-500">Min
                                      <input type="number" step="any" value={lv.min}
                                        onChange={e => updateBathyLevel(layerName, 'floating_levels', i, 'min', +e.target.value)}
                                        className={`w-full border rounded p-1.5 text-sm mt-0.5 ${invalid ? 'border-red-400 bg-red-50' : ''}`} />
                                    </label>
                                    <label className="block text-xs text-slate-500">Score
                                      <input type="number" step={1} min={0} max={100} value={lv.score}
                                        onChange={e => updateBathyLevel(layerName, 'floating_levels', i, 'score', +e.target.value)}
                                        className="w-full border rounded p-1.5 text-sm mt-0.5" />
                                    </label>
                                  </div>
                                )
                              })}
                            </div>
                          </div>
                        </div>
                      ) : (
                      /* Standard level cards — 4 columns like original Streamlit */
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
                      )}
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
                  </>
                )}
              </div>
            ))}
          </div>

          {/* Weight summary bar */}
          {allLayerWeights.length > 0 && (
            <div className={`flex items-center justify-between px-4 py-3 rounded-lg border ${
              weightOk ? 'bg-emerald-50 border-emerald-200' : 'bg-amber-50 border-amber-300'
            }`}>
              <span className={`text-sm font-medium ${ weightOk ? 'text-emerald-700' : 'text-amber-700'}`}>
                {weightOk ? '✅' : '⚠️'} Total weight: <strong>{totalWeight}%</strong>
                {!weightOk && ` (should be 100% — ${totalWeight < 100 ? `missing ${100 - totalWeight}%` : `over by ${totalWeight - 100}%`})`}
              </span>
              {!weightOk && (
                <button onClick={distributeWeightsEvenly}
                  className="text-xs px-3 py-1.5 bg-amber-100 text-amber-800 rounded-lg border border-amber-300 hover:bg-amber-200 transition">
                  ⚖️ Distribute Evenly
                </button>
              )}
            </div>
          )}

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
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-emerald-700">✅ {result.message}</h3>
              <button onClick={() => apiDownload('/scoring/download/', 'final_scored_analysis.csv')}
                className="text-sm px-4 py-1.5 bg-slate-100 rounded-lg hover:bg-slate-200">📥 Download</button>
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

          {/* Data Table */}
          {result.preview?.length > 0 && (
            <div className="bg-white rounded-xl p-6 shadow-sm border">
              <AnalysisResultsTable
                columns={result.previewColumns || Object.keys(result.preview[0])}
                data={result.preview}
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}
