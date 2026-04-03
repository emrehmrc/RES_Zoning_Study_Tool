/* ------------------------------------------------------------------ */
/*  API client – typed wrapper around fetch                           */
/*  Session ID is passed via X-Session-ID header                      */
/* ------------------------------------------------------------------ */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

function getSessionId(): string {
  if (typeof window === 'undefined') return ''
  return localStorage.getItem('dashboard_session_id') || ''
}

function setSessionId(id: string) {
  if (typeof window !== 'undefined') {
    localStorage.setItem('dashboard_session_id', id)
  }
}

async function request(path: string, options: RequestInit = {}): Promise<Response> {
  const headers: Record<string, string> = {
    'X-Session-ID': getSessionId(),
    ...(options.headers as Record<string, string> ?? {}),
  }

  // Don't set Content-Type for FormData (browser sets boundary automatically)
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })

  // Persist session ID from response
  const sid = res.headers.get('X-Session-ID')
  if (sid) setSessionId(sid)

  return res
}

/* -------- typed helpers -------- */

export async function apiGet<T = any>(path: string): Promise<T> {
  const res = await request(path)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.error || `Request failed (${res.status})`)
  }
  return res.json()
}

export async function apiPost<T = any>(path: string, data?: any): Promise<T> {
  const body = data instanceof FormData ? data : JSON.stringify(data)
  const res = await request(path, { method: 'POST', body })
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}))
    throw new Error(errBody.error || `Request failed (${res.status})`)
  }
  return res.json()
}

export async function apiPut<T = any>(path: string, data: any): Promise<T> {
  const res = await request(path, { method: 'PUT', body: JSON.stringify(data) })
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}))
    throw new Error(errBody.error || `Request failed (${res.status})`)
  }
  return res.json()
}

export async function apiDelete<T = any>(path: string): Promise<T> {
  const res = await request(path, { method: 'DELETE' })
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}))
    throw new Error(errBody.error || `Request failed (${res.status})`)
  }
  return res.json()
}

export async function apiDownload(path: string, filename: string) {
  document.body.style.cursor = 'wait'
  try {
    const res = await request(path)
    if (!res.ok) throw new Error('Download failed')
    const blob = await res.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    window.URL.revokeObjectURL(url)
  } finally {
    document.body.style.cursor = 'default'
  }
}

/* -------- Task polling -------- */

export interface TaskProgress {
  task_id: string
  status: 'running' | 'completed' | 'failed'
  progress: number
  message: string
  steps: string[]
  result?: any
  error?: string
}

/**
 * Start an async task then poll until complete.
 * @param startPath  POST endpoint that returns { task_id }
 * @param body       Request body for the POST
 * @param onProgress Called on each poll with current progress (optional)
 * @param interval   Polling interval in ms (default 3000)
 */
export async function apiRunWithProgress<T = any>(
  startPath: string,
  body: any,
  onProgress?: (p: TaskProgress) => void,
  interval = 3000,
): Promise<T> {
  const start = await apiPost<{ task_id: string }>(startPath, body)
  const taskId = start.task_id

  return new Promise((resolve, reject) => {
    const poll = setInterval(async () => {
      try {
        const p = await apiGet<TaskProgress>(`/task/${taskId}/progress/`)
        if (onProgress) onProgress(p)
        if (p.status === 'completed') {
          clearInterval(poll)
          resolve(p.result as T)
        } else if (p.status === 'failed') {
          clearInterval(poll)
          reject(new Error(p.error || 'Task failed'))
        }
      } catch (err) {
        clearInterval(poll)
        reject(err)
      }
    }, interval)
  })
}

export { getSessionId, setSessionId }
