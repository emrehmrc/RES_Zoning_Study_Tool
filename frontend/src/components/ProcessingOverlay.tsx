'use client'

/**
 * Full-section overlay shown while a long-running task is executing.
 * Displays a pulsing animation and a single status message.
 */
export default function ProcessingOverlay({
  message = 'Processing...',
  accentColor = 'emerald',
}: {
  message?: string
  accentColor?: 'emerald' | 'purple' | 'indigo' | 'blue'
}) {
  const colors: Record<string, { bg: string; ring: string; text: string; dot: string }> = {
    emerald: { bg: 'bg-emerald-50', ring: 'border-emerald-500', text: 'text-emerald-700', dot: 'bg-emerald-500' },
    purple: { bg: 'bg-purple-50', ring: 'border-purple-500', text: 'text-purple-700', dot: 'bg-purple-500' },
    indigo: { bg: 'bg-indigo-50', ring: 'border-indigo-500', text: 'text-indigo-700', dot: 'bg-indigo-500' },
    blue: { bg: 'bg-blue-50', ring: 'border-blue-500', text: 'text-blue-700', dot: 'bg-blue-500' },
  }
  const c = colors[accentColor] || colors.emerald

  return (
    <div className={`${c.bg} rounded-xl p-8 border-2 ${c.ring} border-dashed flex flex-col items-center justify-center gap-4`}>
      {/* Animated dots */}
      <div className="flex items-center gap-2">
        {[0, 1, 2].map(i => (
          <span
            key={i}
            className={`block w-3 h-3 rounded-full ${c.dot} animate-bounce`}
            style={{ animationDelay: `${i * 0.15}s`, animationDuration: '0.8s' }}
          />
        ))}
      </div>
      <p className={`text-sm font-medium ${c.text}`}>{message}</p>
      <p className="text-xs text-slate-400">Please wait — this may take a while for large datasets.</p>
    </div>
  )
}
