'use client'

import { useEffect, useRef, useState } from 'react'
import { apiGet } from '@/lib/api'
import 'leaflet/dist/leaflet.css'

// Lazy-load leaflet to avoid SSR issues
let L: typeof import('leaflet') | null = null

interface Props {
  country?: string
  zone?: string
  gridSizeX: number   // meters
  gridSizeY: number   // meters
}

/** Approximate degrees per meter at a given latitude */
function metersToDegreesLat(_lat: number) { return 1 / 111_320 }
function metersToDegreesLon(lat: number) { return 1 / (111_320 * Math.cos(lat * Math.PI / 180)) }

export default function CountryMapPreview({ country, zone, gridSizeX, gridSizeY }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<any>(null)
  const layersRef = useRef<any[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Initialize Leaflet map once
  useEffect(() => {
    let mounted = true
    ;(async () => {
      if (!containerRef.current) return
      if (mapRef.current) return // already initialized

      const leaflet = await import('leaflet')
      L = leaflet

      if (!mounted || !containerRef.current) return

      const map = leaflet.map(containerRef.current, {
        center: [48, 16],
        zoom: 4,
        preferCanvas: true,
        zoomControl: true,
        attributionControl: false,
      })

      leaflet.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 18,
      }).addTo(map)

      mapRef.current = map
    })()

    return () => { mounted = false }
  }, [])

  // Load boundary when country/zone changes
  useEffect(() => {
    if (!country && !zone) return
    if (!L) return

    const controller = new AbortController()
    let cancelled = false

    ;(async () => {
      setLoading(true)
      setError('')

      // Clear old layers
      layersRef.current.forEach(l => mapRef.current?.removeLayer(l))
      layersRef.current = []

      try {
        const param = country
          ? `country=${encodeURIComponent(country)}`
          : `zone=${encodeURIComponent(zone!)}`
        const data = await apiGet<{ geojson: any; bounds: [[number, number], [number, number]] }>(
          `/country-boundary/?${param}`
        )

        if (cancelled) return

        // Draw boundary
        const boundaryLayer = L!.geoJSON(data.geojson, {
          style: { color: '#2563eb', weight: 2, fillColor: '#3b82f6', fillOpacity: 0.08 }
        }).addTo(mapRef.current)
        layersRef.current.push(boundaryLayer)

        // Fit map to boundary
        mapRef.current.fitBounds(data.bounds, { padding: [20, 20] })

        // Draw grid overlay using a Canvas-based custom layer for performance
        const [[south, west], [north, east]] = data.bounds
        const centerLat = (south + north) / 2

        const dLat = gridSizeY * metersToDegreesLat(centerLat)
        const dLon = gridSizeX * metersToDegreesLon(centerLat)

        // Limit grid lines drawn (performance guard)
        const maxLines = 600
        const nLon = Math.ceil((east - west) / dLon)
        const nLat = Math.ceil((north - south) / dLat)

        if (nLon + nLat <= maxLines) {
          // Draw actual grid lines
          const lines: [number, number][][] = []

          // Vertical lines
          for (let i = 0; i <= nLon; i++) {
            const x = west + i * dLon
            lines.push([[south, x], [north, x]])
          }
          // Horizontal lines
          for (let j = 0; j <= nLat; j++) {
            const y = south + j * dLat
            lines.push([[y, west], [y, east]])
          }

          const gridLayer = L!.polyline(lines as any, {
            color: '#6366f1',
            weight: 0.5,
            opacity: 0.45,
            interactive: false,
          }).addTo(mapRef.current)
          layersRef.current.push(gridLayer)
        } else {
          // Too many cells — show a sampled grid (every Nth line)
          const step = Math.max(1, Math.ceil(Math.max(nLon, nLat) / 300))
          const lines: [number, number][][] = []

          for (let i = 0; i <= nLon; i += step) {
            const x = west + i * dLon
            lines.push([[south, x], [north, x]])
          }
          for (let j = 0; j <= nLat; j += step) {
            const y = south + j * dLat
            lines.push([[y, west], [y, east]])
          }

          const gridLayer = L!.polyline(lines as any, {
            color: '#6366f1',
            weight: 0.4,
            opacity: 0.3,
            interactive: false,
          }).addTo(mapRef.current)
          layersRef.current.push(gridLayer)
        }

        // Info label
        const totalCells = nLon * nLat
        const infoDiv = document.createElement('div')
        infoDiv.className = 'leaflet-control'
        infoDiv.innerHTML = `<div style="background:white;padding:4px 8px;border-radius:6px;font-size:11px;border:1px solid #e2e8f0;color:#334155">
          Grid: ${gridSizeX}m × ${gridSizeY}m &nbsp;|&nbsp; ~${totalCells.toLocaleString()} cells
        </div>`
        const InfoControl = L!.Control.extend({
          onAdd() { return infoDiv },
        })
        const info = new InfoControl({ position: 'bottomleft' })
        info.addTo(mapRef.current)
        layersRef.current.push(info)

      } catch (e: any) {
        if (!cancelled) setError(e.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()

    return () => { cancelled = true; controller.abort() }
  }, [country, zone, gridSizeX, gridSizeY])

  // Resize map when visibility changes
  useEffect(() => {
    const timer = setTimeout(() => mapRef.current?.invalidateSize(), 300)
    return () => clearTimeout(timer)
  }, [country, zone])

  if (!country && !zone) return null

  return (
    <div className="relative rounded-lg overflow-hidden border" style={{ height: 350 }}>
      {loading && (
        <div className="absolute inset-0 z-[1000] flex items-center justify-center bg-white/60">
          <span className="text-sm text-slate-500">Loading map...</span>
        </div>
      )}
      {error && (
        <div className="absolute top-2 left-2 z-[1000] text-xs text-red-600 bg-white/90 px-2 py-1 rounded">{error}</div>
      )}
      <div ref={containerRef} style={{ height: '100%', width: '100%' }} />
    </div>
  )
}
