'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { apiPost, setSessionId } from '@/lib/api'

const modes = [
  {
    key: 'Solar',
    icon: '☀️',
    title: 'Solar PV Project',
    subtitle: 'Analysis for Photovoltaic Power Plants',
    bullets: ['Solar PV Potential Analysis', 'Slope & Terrain Constraints', 'Proximity to Transmission Lines'],
    gradient: 'from-orange-400 to-amber-500',
    border: 'border-orange-300',
    btn: 'bg-orange-500 hover:bg-orange-600',
  },
  {
    key: 'OnShore',
    icon: '🌬️',
    title: 'On-Shore Wind',
    subtitle: 'Analysis for On-Shore Wind Zoning',
    bullets: ['Wind Resource & Potential Assessment', 'Turbine Specific Suitability', 'Environmental & Social Constraints'],
    gradient: 'from-blue-900 to-indigo-800',
    border: 'border-blue-400',
    btn: 'bg-blue-900 hover:bg-blue-950',
  },
  {
    key: 'OffShore',
    icon: '🌊',
    title: 'Off-Shore Wind',
    subtitle: 'Analysis for Off-Shore Wind Zoning',
    bullets: ['Wind Resource & Potential Assessment', 'Turbine Specific Suitability', 'Marine Constraints'],
    gradient: 'from-blue-400 to-cyan-500',
    border: 'border-cyan-300',
    btn: 'bg-blue-500 hover:bg-blue-600',
  },
]

export default function LandingPage() {
  const router = useRouter()
  const [loading, setLoading] = useState<string | null>(null)

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
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex flex-col items-center justify-center px-4">
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
              <span className="text-5xl">{m.icon}</span>
              <h2 className="text-2xl font-bold text-white mt-3">{m.title}</h2>
              <p className="text-white/80 text-sm mt-1">{m.subtitle}</p>
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

      <p className="text-slate-400 mt-10 text-sm">ℹ️ Select a mode to load specific analysis layers and scoring criteria.</p>
    </div>
  )
}
