'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { apiGet, apiPost } from '@/lib/api'
import type { ProjectConfig, ProjectStatus } from '@/lib/types'
import Sidebar from './Sidebar'
import GridizationTab from './GridizationTab'
import ScoringTab from './ScoringTab'
import LevelScoringTab from './LevelScoringTab'
import ClusterTab from './ClusterTab'

const TABS = [
  { id: 0, label: '1. Gridization', icon: '📐' },
  { id: 1, label: '2. Layer Calculation', icon: '🎯' },
  { id: 2, label: '3. Scoring', icon: '📈' },
  { id: 3, label: '4. Cluster & Aggregation', icon: '🧩' },
]

const THEME: Record<string, { bar: string; text: string }> = {
  Solar: { bar: 'bg-orange-400', text: 'text-orange-600' },
  OnShore: { bar: 'bg-blue-900', text: 'text-blue-900' },
  OffShore: { bar: 'bg-blue-500', text: 'text-blue-600' },
}

export default function Dashboard() {
  const router = useRouter()
  const [config, setConfig] = useState<ProjectConfig | null>(null)
  const [projectStatus, setProjectStatus] = useState<ProjectStatus | null>(null)
  const [activeTab, setActiveTab] = useState(0)
  const [loading, setLoading] = useState(true)

  const refreshStatus = useCallback(async () => {
    try {
      const st = await apiGet<ProjectStatus>('/project/status/')
      setProjectStatus(st)
    } catch { /* ignore */ }
  }, [])

  useEffect(() => {
    async function init() {
      try {
        const [cfg, st] = await Promise.all([
          apiGet<ProjectConfig>('/project/config/'),
          apiGet<ProjectStatus>('/project/status/'),
        ])
        setConfig(cfg)
        setProjectStatus(st)
      } catch {
        router.push('/')
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [router])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin h-12 w-12 border-4 border-blue-500 border-t-transparent rounded-full" />
      </div>
    )
  }

  if (!config || !projectStatus) return null

  const theme = THEME[config.project_type] ?? { bar: 'bg-gray-400', text: 'text-gray-600' }

  async function switchMode() {
    await apiPost('/project/reset/', { keep_project_type: false })
    router.push('/')
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Color bar */}
      <div className={`h-1.5 ${theme.bar}`} />

      {/* Header */}
      <header className="bg-white shadow-sm border-b px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-3xl">{config.icon}</span>
          <h1 className="text-xl font-bold text-slate-800">{config.app_title}</h1>
        </div>
        <div className="flex items-center gap-4">
          <span className={`text-sm font-medium ${theme.text}`}>
            Mode: {config.project_type}
          </span>
          <button
            onClick={switchMode}
            className="text-sm px-4 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-100 transition"
          >
            🔄 Switch Mode
          </button>
        </div>
      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <Sidebar status={projectStatus} config={config} onRefresh={refreshStatus} />

        {/* Main */}
        <main className="flex-1 flex flex-col overflow-y-auto">
          {/* Tab bar */}
          <div className="bg-white border-b px-6 flex gap-1 pt-2">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-5 py-2.5 text-sm font-medium rounded-t-lg transition-colors ${
                  activeTab === tab.id
                    ? 'bg-slate-50 border border-b-0 border-slate-200 text-slate-800'
                    : 'text-slate-500 hover:text-slate-700 hover:bg-slate-50'
                }`}
              >
                {tab.icon} {tab.label}
              </button>
            ))}
          </div>

          {/* Tab content — all tabs stay mounted, hidden via CSS */}
          <div className="flex-1 bg-slate-50 overflow-y-auto relative">
            <div className={`p-6 ${activeTab === 0 ? '' : 'hidden'}`}>
              <GridizationTab config={config} onComplete={refreshStatus} />
            </div>
            <div className={`p-6 ${activeTab === 1 ? '' : 'hidden'}`}>
              <ScoringTab config={config} onComplete={refreshStatus} />
            </div>
            <div className={`p-6 ${activeTab === 2 ? '' : 'hidden'}`}>
              <LevelScoringTab config={config} onComplete={refreshStatus} activeTab={activeTab} />
            </div>
            <div className={`p-6 ${activeTab === 3 ? '' : 'hidden'}`}>
              <ClusterTab config={config} onComplete={refreshStatus} activeTab={activeTab} />
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
