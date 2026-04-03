'use client'

import { useState, useEffect, useCallback } from 'react'
import dynamic from 'next/dynamic'
import { apiGet, apiPost, apiPut, apiDownload, apiRunWithProgress } from '@/lib/api'
import type { ProjectConfig, ProjectStatus, ClusterScoringRule } from '@/lib/types'
import ProcessingOverlay from './ProcessingOverlay'
import AnalysisResultsTable from './AnalysisResultsTable'

const ClusterMapPreview = dynamic(() => import('./ClusterMapPreview'), { ssr: false })

/** Human-friendly labels for financial constant keys */
const FINANCIAL_LABELS: Record<string, { label: string; unit?: string; modes?: string[] }> = {
  pv_capex_per_mw:          { label: 'PV CAPEX Per MW', unit: '$' },
  wind_capex_per_mw:        { label: 'Wind CAPEX Per MW', unit: '$' },
  substation_pv_ratio:      { label: 'Substation Installation Cost Ratio of CAPEX', modes: ['Solar'] },
  substation_wind_ratio:    { label: 'Substation Installation Cost Ratio of CAPEX', modes: ['OnShore', 'OffShore'] },
  line_expropriation_ratio: { label: 'Line Expropriation Cost Ratio of CAPEX' },
  land_cost_ratio:          { label: 'Land Expropriation Cost Ratio of CAPEX' },
  transport_network_base:   { label: 'Transport Network Base Cost', unit: '$' },
  transport_network_per_mw: { label: 'Transport Network Cost Per MW', unit: '$' },
}

interface Props { config: ProjectConfig; onComplete: () => void; activeTab?: number; status?: ProjectStatus | null }

export default function ClusterTab({ config, onComplete, activeTab, status }: Props) {
  const [nominalCapacity, setNominalCapacity] = useState(13)
  const [maxCapacity, setMaxCapacity] = useState(250)
  const [adjustCoverage, setAdjustCoverage] = useState(true)
  const [source, setSource] = useState<'step3' | 'upload'>('step3')

  const [scoringRules, setScoringRules] = useState<ClusterScoringRule[]>([])
  const [financialConstants, setFinancialConstants] = useState<Record<string, any>>({})
  const [cpValues, setCpValues] = useState<any[]>([])

  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState('')
  const [activeRefTab, setActiveRefTab] = useState<'rules' | 'financial' | 'cp'>('rules')
  const [focusWkt, setFocusWkt] = useState<string | null>(null)
  const [clusterRows, setClusterRows] = useState<any[]>([])

  // Wait cursor while loading
  useEffect(() => {
    document.body.style.cursor = loading ? 'wait' : ''
    return () => { document.body.style.cursor = '' }
  }, [loading])

  const loadRefData = useCallback(async () => {
    try {
      const [rules, fin, cp] = await Promise.all([
        apiGet<ClusterScoringRule[]>('/scoring-rules/'),
        apiGet<Record<string, any>>('/financial-constants/'),
        apiGet<any[]>('/cp-values/'),
      ])
      setScoringRules(rules)
      setFinancialConstants(fin)
      setCpValues(cp)
    } catch { /* ignore */ }
  }, [])

  useEffect(() => { loadRefData() }, [loadRefData])

  // Re-fetch reference data when this tab (index 3) becomes active
  useEffect(() => {
    if (activeTab === 3) loadRefData()
  }, [activeTab, loadRefData])

  async function uploadCSV(file: File) {
    setError('')
    try {
      const fd = new FormData()
      fd.append('csv_file', file)
      await apiPost('/cluster/upload-csv/', fd)
      setSource('upload')
    } catch (e: any) { setError(e.message) }
  }

  async function saveRules() {
    try {
      await apiPut('/scoring-rules/', scoringRules)
    } catch (e: any) { setError(e.message) }
  }

  async function saveFinancial() {
    try {
      await apiPut('/financial-constants/', financialConstants)
    } catch (e: any) { setError(e.message) }
  }

  async function saveCp() {
    try {
      await apiPut('/cp-values/', cpValues)
    } catch (e: any) { setError(e.message) }
  }

  function updateRule(idx: number, field: string, value: any) {
    setScoringRules(prev => {
      const updated = [...prev]
      updated[idx] = { ...updated[idx], [field]: value }
      return updated
    })
  }

  async function runCluster() {
    setLoading(true); setError(''); setResult(null); setClusterRows([]); setFocusWkt(null)
    try {
      const res = await apiRunWithProgress(
        '/cluster/run-async/',
        {
          nominal_capacity_mw: nominalCapacity,
          max_capacity_mw: maxCapacity,
          adjust_for_coverage: adjustCoverage,
          source,
          scoring_rules: scoringRules,
          financial_constants: financialConstants,
          cp_values: cpValues,
        },
      )
      setResult(res)
      // Fetch full cluster data for DataTable + map
      try {
        const full = await apiGet<{ data: any[]; columns: string[] }>('/cluster/results/?page=1&page_size=100000')
        setClusterRows(full.data)
        if (full.columns) res.columns = full.columns
      } catch {
        // Use preview from result as fallback
        if (res.preview?.length) setClusterRows(res.preview)
      }
      onComplete()
    } catch (e: any) { setError(e.message) } finally { setLoading(false) }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-800">🔗 Step 4: Cluster Analysis</h2>
      <hr />

      {(!status || !status.has_final_scored) ? (
        <div className="bg-amber-50 text-amber-700 p-6 rounded-xl border border-amber-200 text-center">
          <p className="font-medium">No scoring data available.</p>
          <p className="text-sm mt-1">Complete Step 3 (Scoring) first, or upload a CSV with scored data.</p>
        </div>
      ) : (<>

      {/* Data Source & Capacity Params */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Data Source */}
        <div className="bg-white rounded-xl p-6 shadow-sm border space-y-4">
          <h3 className="font-semibold text-slate-700">📂 Data Source</h3>
          <div className="flex gap-3">
            <button onClick={() => setSource('step3')}
              className={`px-4 py-1.5 rounded text-sm ${source === 'step3' ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600'}`}
            >Step 3 Results</button>
            <label className={`cursor-pointer px-4 py-1.5 rounded text-sm ${source === 'upload' ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600'}`}>
              📤 Upload CSV
              <input type="file" accept=".csv" className="hidden" onChange={e => { if (e.target.files?.[0]) uploadCSV(e.target.files[0]) }} />
            </label>
          </div>
          {source === 'upload' && (
            <p className="text-xs text-emerald-600">✅ CSV uploaded — will use uploaded data.</p>
          )}
        </div>

        {/* Right: Capacity Constraints */}
        <div className="bg-white rounded-xl p-6 shadow-sm border space-y-4">
          <h3 className="font-semibold text-slate-700">⚡ Capacity Constraints</h3>
          <label className="block text-sm text-slate-600">
            Nominal Capacity (MW)
            <input type="number" value={nominalCapacity} onChange={e => setNominalCapacity(+e.target.value)}
              className="mt-1 w-full border rounded-lg p-2.5" step={0.5} min={0.1} />
          </label>
          <label className="block text-sm text-slate-600">
            Max Cluster Capacity (MW)
            <input type="number" value={maxCapacity} onChange={e => setMaxCapacity(+e.target.value)}
              className="mt-1 w-full border rounded-lg p-2.5" step={10} min={10} />
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={adjustCoverage}
              onChange={e => setAdjustCoverage(e.target.checked)}
              className="rounded" />
            Adjust capacity for coverage
          </label>
        </div>
      </div>

      {/* Reference Data Tabs */}
      <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
        <div className="flex border-b">
          {[
            { key: 'rules', label: '📏 Connection Rules' },
            { key: 'financial', label: '💰 Financial Constants' },
            { key: 'cp', label: '⚙️ Technical Constants' },
          ].map(tab => (
            <button key={tab.key} onClick={() => setActiveRefTab(tab.key as any)}
              className={`px-5 py-3 text-sm font-medium transition ${activeRefTab === tab.key ? 'bg-blue-50 text-blue-700 border-b-2 border-blue-600' : 'text-slate-500 hover:bg-slate-50'}`}>
              {tab.label}
            </button>
          ))}
        </div>

        <div className="p-5 max-h-96 overflow-auto">
          {/* Scoring Rules */}
          {activeRefTab === 'rules' && (
            <div className="space-y-3">
              {scoringRules.length === 0 ? (
                <p className="text-sm text-slate-400">No scoring rules configured.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full text-xs">
                    <thead className="bg-slate-50">
                      <tr>
                        <th className="px-2 py-1.5 text-left">Criteria</th>
                        <th className="px-2 py-1.5 text-left">Weight</th>
                        <th className="px-2 py-1.5 text-left">kV</th>
                        <th className="px-2 py-1.5 text-left">Kind</th>
                        <th className="px-2 py-1.5 text-left">L1 Min</th>
                        <th className="px-2 py-1.5 text-left">L1 Max</th>
                        <th className="px-2 py-1.5 text-left">L1 Score</th>
                        <th className="px-2 py-1.5 text-left">L2 Min</th>
                        <th className="px-2 py-1.5 text-left">L2 Max</th>
                        <th className="px-2 py-1.5 text-left">L2 Score</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {scoringRules.map((r, i) => (
                        <tr key={i}>
                          <td className="px-2 py-1">{r.criteria_norm}</td>
                          <td className="px-2 py-1">
                            <input type="number" value={r.weight_frac} step={0.01}
                              onChange={e => updateRule(i, 'weight_frac', +e.target.value)}
                              className="w-16 border rounded p-0.5 text-xs" />
                          </td>
                          <td className="px-2 py-1">{r.kv}</td>
                          <td className="px-2 py-1">{r.kind}</td>
                          <td className="px-2 py-1">
                            <input type="number" value={r.L1_min} onChange={e => updateRule(i, 'L1_min', +e.target.value)} className="w-14 border rounded p-0.5 text-xs" />
                          </td>
                          <td className="px-2 py-1">
                            <input type="number" value={r.L1_max} onChange={e => updateRule(i, 'L1_max', +e.target.value)} className="w-14 border rounded p-0.5 text-xs" />
                          </td>
                          <td className="px-2 py-1">
                            <input type="number" value={r.L1_score} onChange={e => updateRule(i, 'L1_score', +e.target.value)} className="w-14 border rounded p-0.5 text-xs" />
                          </td>
                          <td className="px-2 py-1">
                            <input type="number" value={r.L2_min} onChange={e => updateRule(i, 'L2_min', +e.target.value)} className="w-14 border rounded p-0.5 text-xs" />
                          </td>
                          <td className="px-2 py-1">
                            <input type="number" value={r.L2_max} onChange={e => updateRule(i, 'L2_max', +e.target.value)} className="w-14 border rounded p-0.5 text-xs" />
                          </td>
                          <td className="px-2 py-1">
                            <input type="number" value={r.L2_score} onChange={e => updateRule(i, 'L2_score', +e.target.value)} className="w-14 border rounded p-0.5 text-xs" />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <button onClick={saveRules}
                className="px-4 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">
                💾 Save Rules
              </button>
            </div>
          )}

          {/* Financial Constants */}
          {activeRefTab === 'financial' && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {Object.entries(financialConstants)
                  .filter(([k]) => typeof financialConstants[k] !== 'object')
                  .filter(([k]) => {
                    const meta = FINANCIAL_LABELS[k]
                    if (!meta?.modes) return true
                    return meta.modes.includes(config.project_type)
                  })
                  .map(([key, val]) => {
                    const meta = FINANCIAL_LABELS[key]
                    const displayLabel = meta
                      ? `${meta.unit ? `(${meta.unit}) ` : ''}${meta.label}`
                      : key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
                    return (
                      <label key={key} className="block text-xs text-slate-600">
                        {displayLabel}
                        <input type="number" value={val as number}
                          onChange={e => setFinancialConstants(prev => ({ ...prev, [key]: +e.target.value }))}
                          className="mt-1 w-full border rounded p-2 text-sm" />
                      </label>
                    )
                  })}
              </div>
              <button onClick={saveFinancial}
                className="px-4 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">
                💾 Save Financial Constants
              </button>
            </div>
          )}

          {/* Technical Constants (Cp Values + Capacity Factor) */}
          {activeRefTab === 'cp' && (
            <div className="space-y-4">
              {/* Capacity Factor */}
              <div>
                <h4 className="text-sm font-medium text-slate-700 mb-2">Capacity Factor</h4>
                <label className="block text-xs text-slate-600">
                  Capacity Factor (0–1)
                  <input
                    type="number" step={0.01} min={0} max={1}
                    value={financialConstants.capacity_factor ?? ''}
                    onChange={e => setFinancialConstants(prev => ({ ...prev, capacity_factor: +e.target.value }))}
                    placeholder="Leave empty for auto-calculation"
                    className="mt-1 w-full border rounded p-2 text-sm"
                  />
                  <span className="text-xs text-slate-400 mt-0.5 block">If set, overrides the calculated capacity factor in financial analysis.</span>
                </label>
              </div>

              {/* Cp Values — only for wind projects */}
              {(config.project_type === 'OnShore' || config.project_type === 'OffShore') && (
                <div>
                  <h4 className="text-sm font-medium text-slate-700 mb-2">Cp Values (Wind Power Curve)</h4>
                  <div className="overflow-x-auto max-h-60">
                    <table className="min-w-full text-xs">
                      <thead className="bg-slate-50 sticky top-0">
                        <tr>
                          <th className="px-3 py-1.5 text-left">Wind Speed (m/s)</th>
                          <th className="px-3 py-1.5 text-left">Cp</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {cpValues.map((row, i) => (
                          <tr key={i}>
                            <td className="px-3 py-1">
                              <input type="number" value={row['Wind speed'] ?? row['wind_speed'] ?? 0}
                                onChange={e => {
                                  const updated = [...cpValues]
                                  updated[i] = { ...updated[i], 'Wind speed': +e.target.value }
                                  setCpValues(updated)
                                }}
                                className="w-20 border rounded p-0.5 text-xs" />
                            </td>
                            <td className="px-3 py-1">
                              <input type="number" step={0.01} value={row['Cp'] ?? row['cp'] ?? 0}
                                onChange={e => {
                                  const updated = [...cpValues]
                                  updated[i] = { ...updated[i], Cp: +e.target.value }
                                  setCpValues(updated)
                                }}
                                className="w-20 border rounded p-0.5 text-xs" />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              <button onClick={() => { saveCp(); saveFinancial() }}
                className="px-4 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">
                💾 Save Technical Constants
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Run Button */}
      <button onClick={runCluster} disabled={loading}
        className="w-full py-3 bg-indigo-600 text-white rounded-lg font-semibold hover:bg-indigo-700 disabled:opacity-50 transition">
        {loading ? '⏳ Running Cluster Analysis...' : '🚀 Run Cluster Analysis & Scoring'}
      </button>

      {/* Processing Animation */}
      {loading && (
        <ProcessingOverlay message="Running cluster analysis & scoring..." accentColor="indigo" />
      )}

      {error && <div className="bg-red-50 text-red-700 p-4 rounded-lg border border-red-200">{error}</div>}

      {/* Results */}
      {result && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl p-6 shadow-sm border">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-emerald-700">✅ {result.message}</h3>
            </div>

            {result.summary && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                {[
                  { label: 'Total Clusters', value: result.summary.total_clusters },
                  { label: 'Avg Capacity (MW)', value: result.summary.avg_capacity_mw },
                  { label: 'Total Capacity (MW)', value: result.summary.total_capacity_mw },
                  { label: 'Avg Overall Score', value: result.summary.avg_overall_score },
                  { label: 'Avg LCOE ($/MWh)', value: result.summary.avg_lcoe },
                ].filter(s => s.value != null).map(s => (
                  <div key={s.label} className="bg-slate-50 rounded-lg p-3 border text-center">
                    <p className="text-lg font-bold text-slate-800">{typeof s.value === 'number' ? s.value.toLocaleString() : s.value}</p>
                    <p className="text-xs text-slate-500">{s.label}</p>
                  </div>
                ))}
              </div>
            )}

          </div>

          {/* Cluster Map */}
          {clusterRows.length > 0 && (
            <ClusterMapPreview clusters={clusterRows} focusWkt={focusWkt} activeTab={activeTab} />
          )}

          {/* Data Table */}
          {clusterRows.length > 0 && result.columns && (
            <div className="bg-white rounded-xl p-6 shadow-sm border">
              <div className="flex justify-end mb-3">
                <button onClick={() => apiDownload('/cluster/download/', 'clustered_scored_results.csv')}
                  className="text-sm px-4 py-1.5 bg-slate-100 rounded-lg hover:bg-slate-200 border">📥 Download CSV</button>
              </div>
              <AnalysisResultsTable
                columns={result.columns}
                data={clusterRows}
                onRowClick={(row) => { if (row.wkt) setFocusWkt(row.wkt) }}
              />
            </div>
          )}
        </div>
      )}
      </>)}
    </div>
  )
}
