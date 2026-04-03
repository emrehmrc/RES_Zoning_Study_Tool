'use client'

import { apiPost } from '@/lib/api'
import type { ProjectConfig, ProjectStatus } from '@/lib/types'

interface Props {
  status: ProjectStatus
  config: ProjectConfig
  onRefresh: () => void
  onReset: () => void
}

export default function Sidebar({ status, config, onRefresh, onReset }: Props) {
  async function resetProject() {
    if (!confirm('Are you sure you want to reset the current project data?')) return
    try {
      await apiPost('/project/reset/', { keep_project_type: true })
    } catch { /* ignore */ }
    onReset()
  }

  const steps = [
    { label: 'Grid', ok: status.grid_created, detail: status.grid_count ? `${status.grid_count.toLocaleString()} cells` : null },
    { label: 'Layers', ok: status.layer_count > 0, detail: status.layer_count ? `${status.layer_count} layer(s)` : null },
    { label: 'Scoring', ok: status.scoring_complete, detail: status.scoring_count ? `${status.scoring_count.toLocaleString()} cells` : null },
    { label: 'Clusters', ok: status.has_cluster_results, detail: status.cluster_count ? `${status.cluster_count} clusters` : null },
  ]

  return (
    <aside className="w-64 bg-white border-r flex flex-col">
      <div className="p-4 border-b">
        <h2 className="font-bold text-slate-700 text-sm uppercase tracking-wide">
          📊 {config.project_type} Status
        </h2>
      </div>

      <div className="flex-1 p-4 space-y-3">
        {steps.map((step, i) => (
          <div key={i} className={`p-3 rounded-lg border ${step.ok ? 'bg-emerald-50 border-emerald-200' : 'bg-slate-50 border-slate-200'}`}>
            <div className="flex items-center gap-2">
              <span className={`text-sm ${step.ok ? 'text-emerald-600' : 'text-amber-500'}`}>
                {step.ok ? '✅' : '⏳'}
              </span>
              <span className="text-sm font-medium text-slate-700">{step.label}</span>
            </div>
            {step.detail && (
              <p className="text-xs text-slate-500 mt-1 ml-6">{step.detail}</p>
            )}
          </div>
        ))}
      </div>

      <div className="p-4 border-t">
        <button
          onClick={resetProject}
          className="w-full py-2 text-sm rounded-lg bg-red-50 text-red-600 border border-red-200 hover:bg-red-100 transition"
        >
          🗑️ Reset Project
        </button>
      </div>
    </aside>
  )
}
