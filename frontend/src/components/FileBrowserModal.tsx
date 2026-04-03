'use client'

import { useState, useEffect, useCallback } from 'react'
import { apiGet } from '@/lib/api'

const LS_LAST_PATH = 'fileBrowser_lastPath'
const LS_RECENT = 'fileBrowser_recentFolders'
const MAX_RECENT = 6

function loadRecent(): string[] {
  try { return JSON.parse(localStorage.getItem(LS_RECENT) || '[]') } catch { return [] }
}

function persistRecent(folder: string) {
  if (!folder) return
  const updated = [folder, ...loadRecent().filter(p => p !== folder)].slice(0, MAX_RECENT)
  localStorage.setItem(LS_RECENT, JSON.stringify(updated))
  localStorage.setItem(LS_LAST_PATH, folder)
}

function folderLabel(path: string) {
  return path.split(/[\\/]/).filter(Boolean).pop() || path
}

interface BrowseResult {
  path: string
  parent: string
  folders: string[]
  files: string[]
}

interface Props {
  onSelect: (path: string) => void
  onClose: () => void
}

export default function FileBrowserModal({ onSelect, onClose }: Props) {
  const [currentPath, setCurrentPath] = useState('')
  const [browsed, setBrowsed] = useState<BrowseResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [recentFolders, setRecentFolders] = useState<string[]>([])
  const [showRecent, setShowRecent] = useState(true)

  const navigate = useCallback(async (path: string) => {
    setLoading(true)
    setError('')
    try {
      const query = path ? `?path=${encodeURIComponent(path)}` : ''
      const r = await apiGet<BrowseResult>(`/browse/${query}`)
      setBrowsed(r)
      setCurrentPath(r.path)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const recent = loadRecent()
    setRecentFolders(recent)
    // Open at last used path; fall back to root on error
    const lastPath = localStorage.getItem(LS_LAST_PATH) || ''
    if (lastPath) {
      navigate(lastPath).catch(() => navigate(''))
    } else {
      navigate('')
    }
  }, [navigate])

  function selectFile(filename: string) {
    const sep = currentPath.endsWith('\\') || currentPath.endsWith('/') ? '' : '\\'
    const fullPath = currentPath ? `${currentPath}${sep}${filename}` : filename
    persistRecent(currentPath)
    setRecentFolders(loadRecent())
    onSelect(fullPath)
    onClose()
  }

  function goUp() {
    if (browsed?.parent !== undefined && browsed.parent !== currentPath) {
      navigate(browsed.parent)
    } else {
      navigate('')
    }
  }

  function jumpToRecent(path: string) {
    navigate(path)
    setShowRecent(false)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-xl flex flex-col" style={{ maxHeight: '80vh' }}>
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b">
          <h3 className="font-semibold text-slate-700">📂 Select Raster File (.tif)</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-xl leading-none">×</button>
        </div>

        {/* Path bar */}
        <div className="flex items-center gap-2 px-4 py-2 bg-slate-50 border-b text-sm text-slate-500">
          <button
            onClick={goUp}
            disabled={!browsed || loading}
            className="px-2 py-0.5 bg-white border rounded text-xs hover:bg-slate-100 disabled:opacity-40"
            title="Go up"
          >⬆ Up</button>
          <span className="truncate font-mono text-xs flex-1">{currentPath || 'Drives'}</span>
          {recentFolders.length > 0 && (
            <button
              onClick={() => setShowRecent(v => !v)}
              className={`px-2 py-0.5 border rounded text-xs whitespace-nowrap ${showRecent ? 'bg-blue-100 text-blue-700 border-blue-300' : 'bg-white hover:bg-slate-100'}`}
              title="Toggle recent folders"
            >🕐 Recent</button>
          )}
        </div>

        {/* Recent folders panel */}
        {showRecent && recentFolders.length > 0 && (
          <div className="px-3 pt-2 pb-2 bg-blue-50 border-b">
            <p className="text-xs font-semibold text-blue-700 mb-1">Recent Folders</p>
            <div className="flex flex-col gap-0.5">
              {recentFolders.map(folder => (
                <button
                  key={folder}
                  onClick={() => jumpToRecent(folder)}
                  className="flex items-center gap-2 px-2 py-1 rounded hover:bg-blue-100 text-left group"
                  title={folder}
                >
                  <span className="text-sm">📁</span>
                  <span className="text-sm font-medium text-slate-800 truncate">{folderLabel(folder)}</span>
                  <span className="text-xs text-slate-400 truncate opacity-0 group-hover:opacity-100 transition-opacity">{folder}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Contents */}
        <div className="overflow-y-auto flex-1 p-3 space-y-0.5">
          {loading && (
            <div className="text-center py-8 text-slate-400 text-sm">Loading...</div>
          )}
          {error && (
            <div className="text-red-600 text-sm px-2 py-1">{error}</div>
          )}
          {!loading && browsed && (
            <>
              {browsed.folders.length === 0 && browsed.files.length === 0 && (
                <p className="text-slate-400 text-sm text-center py-6">Empty directory</p>
              )}
              {browsed.folders.map(folder => (
                <button
                  key={folder}
                  onClick={() => {
                    const sep = currentPath.endsWith('\\') || currentPath.endsWith('/') ? '' : '\\'
                    navigate(currentPath ? `${currentPath}${sep}${folder}` : folder)
                  }}
                  className="w-full flex items-center gap-2 px-3 py-1.5 rounded hover:bg-blue-50 text-left text-sm text-slate-700"
                >
                  <span className="text-base">📁</span>
                  <span className="truncate">{folder}</span>
                </button>
              ))}
              {browsed.files.map(file => (
                <button
                  key={file}
                  onClick={() => selectFile(file)}
                  className="w-full flex items-center gap-2 px-3 py-1.5 rounded hover:bg-emerald-50 text-left text-sm text-slate-800 font-medium"
                >
                  <span className="text-base">🗺️</span>
                  <span className="truncate">{file}</span>
                </button>
              ))}
            </>
          )}
        </div>

        <div className="px-5 py-3 border-t text-xs text-slate-400">
          Click a .tif file to select it — no upload needed.
        </div>
      </div>
    </div>
  )
}
