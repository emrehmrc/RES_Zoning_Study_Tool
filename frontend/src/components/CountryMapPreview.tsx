'use client'

import { useEffect, useRef, useState } from 'react'
import { apiGet } from '@/lib/api'
import 'leaflet/dist/leaflet.css'

// Lazy-load leaflet to avoid SSR issues
let L: typeof import('leaflet') | null = null

interface Props {
  country?: string
  zone?: string
  albRegion?: string
  albDistrict?: string
  gridSizeX: number   // meters
  gridSizeY: number   // meters
  focusCell?: string | null
  wktCells?: string[]
  gridOriginX?: number  // actual grid origin X in EPSG:3857 (from first cell's left)
  gridOriginY?: number  // actual grid origin Y in EPSG:3857 (from first cell's bottom)
  uploadMode?: boolean  // show boundary from /grid-info/ when no country/zone given
}

/** EPSG:4326 → EPSG:3857 (forward Web Mercator) */
function lonLatTo3857(lon: number, lat: number): [number, number] {
  const x = (lon * 20037508.34) / 180
  const y = Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360)) * 20037508.34 / Math.PI
  return [x, y]
}
/** EPSG:3857 → EPSG:4326 (inverse Web Mercator) */
function xy3857ToLatLng(x: number, y: number): [number, number] {
  const lon = (x / 20037508.34) * 180
  const lat = (Math.atan(Math.exp((y / 20037508.34) * Math.PI)) * 360) / Math.PI - 90
  return [lat, lon]
}

export default function CountryMapPreview({ country, zone, albRegion, albDistrict, gridSizeX, gridSizeY, focusCell, wktCells, gridOriginX, gridOriginY, uploadMode }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<any>(null)
  const boundaryLayerRef = useRef<any>(null)
  const gridLayerRef = useRef<any>(null)

  const osmLayerRef = useRef<any>(null)
  const satLayerRef = useRef<any>(null)
  const focusHighlightRef = useRef<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showBoundary, setShowBoundary] = useState(true)
  const [showGrid, setShowGrid] = useState(true)
  const [baseMap, setBaseMap] = useState<'osm' | 'satellite'>('osm')
  const [mapReady, setMapReady] = useState(false)
  const [loadedBounds, setLoadedBounds] = useState<[[number,number],[number,number]] | null>(null)
  const uploadedCellsLayerRef = useRef<any>(null)
  const uploadBoundaryLayerRef = useRef<any>(null)

  // Load boundary from /grid-info/ when in upload mode (no country/zone available)
  useEffect(() => {
    if (!uploadMode || !mapReady || !L) return
    let cancelled = false
    ;(async () => {
      try {
        const info = await apiGet<{ geojson: any; bounds: [[number, number], [number, number]] }>('/grid-info/')
        if (cancelled || !L || !mapRef.current) return
        if (uploadBoundaryLayerRef.current) { mapRef.current.removeLayer(uploadBoundaryLayerRef.current); uploadBoundaryLayerRef.current = null }
        const layer = L.geoJSON(info.geojson, {
          style: { color: '#2563eb', weight: 2, fillColor: '#3b82f6', fillOpacity: 0.08 },
        }).addTo(mapRef.current)
        uploadBoundaryLayerRef.current = layer
        if (!wktCells?.length) {
          mapRef.current.fitBounds(info.bounds, { padding: [20, 20] })
        }
      } catch { /* grid not created yet */ }
    })()
    return () => { cancelled = true }
  }, [uploadMode, mapReady])

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

      const osm = leaflet.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 18,
      }).addTo(map)

      const sat = leaflet.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 18,
      })

      osmLayerRef.current = osm
      satLayerRef.current = sat
      mapRef.current = map
      if (mounted) setMapReady(true)
    })()

    return () => {
      mounted = false
      // Destroy Leaflet map properly to prevent stale state on remount
      if (mapRef.current) {
        try { mapRef.current.remove() } catch { /* ignore */ }
        mapRef.current = null
      }
    }
  }, [])

  // Load boundary when country/zone/albRegion/albDistrict changes
  useEffect(() => {
    if (!country && !zone) return
    if (!L) return

    const controller = new AbortController()
    let cancelled = false

    ;(async () => {
      setLoading(true)
      setError('')

      // Clear old layers
      if (boundaryLayerRef.current) { mapRef.current?.removeLayer(boundaryLayerRef.current); boundaryLayerRef.current = null }
      if (gridLayerRef.current) { mapRef.current?.removeLayer(gridLayerRef.current); gridLayerRef.current = null }

      try {
        // Use most granular Albania boundary if provided, else country/zone
        let param: string
        if (albDistrict) {
          param = `adm2=${encodeURIComponent(albDistrict)}`
        } else if (albRegion) {
          param = `adm1=${encodeURIComponent(albRegion)}`
        } else if (country) {
          param = `country=${encodeURIComponent(country)}`
        } else {
          param = `zone=${encodeURIComponent(zone!)}`
        }
        const data = await apiGet<{ geojson: any; bounds: [[number, number], [number, number]] }>(
          `/country-boundary/?${param}`
        )

        if (cancelled) return

        // Draw boundary
        const boundaryLayer = L!.geoJSON(data.geojson, {
          style: { color: '#2563eb', weight: 2, fillColor: '#3b82f6', fillOpacity: 0.08 }
        }).addTo(mapRef.current)
        boundaryLayerRef.current = boundaryLayer

        // Fit map to boundary
        mapRef.current.fitBounds(data.bounds, { padding: [20, 20] })

        // Store bounds so the grid overlay effect can redraw with correct origin
        setLoadedBounds(data.bounds as [[number, number], [number, number]])

      } catch (e: any) {
        if (!cancelled) setError(e.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()

    return () => { cancelled = true; controller.abort() }
  }, [country, zone, albRegion, albDistrict])

  // Toggle boundary visibility
  useEffect(() => {
    if (!mapRef.current || !boundaryLayerRef.current) return
    if (showBoundary) mapRef.current.addLayer(boundaryLayerRef.current)
    else mapRef.current.removeLayer(boundaryLayerRef.current)
  }, [showBoundary])

  // Toggle grid / uploaded cells visibility
  useEffect(() => {
    if (!mapRef.current) return
    if (gridLayerRef.current) {
      if (showGrid) mapRef.current.addLayer(gridLayerRef.current)
      else mapRef.current.removeLayer(gridLayerRef.current)
    }
    if (uploadedCellsLayerRef.current) {
      if (showGrid) mapRef.current.addLayer(uploadedCellsLayerRef.current)
      else mapRef.current.removeLayer(uploadedCellsLayerRef.current)
    }
  }, [showGrid])

  // Resize map when visibility changes
  useEffect(() => {
    const timer = setTimeout(() => mapRef.current?.invalidateSize(), 300)
    return () => clearTimeout(timer)
  }, [country, zone])

  // Redraw grid overlay whenever bounds, grid size, or actual grid origin changes
  useEffect(() => {
    if (!mapReady || !L || !mapRef.current || !loadedBounds) return

    // Remove old grid layer and info control
    if (gridLayerRef.current) { mapRef.current.removeLayer(gridLayerRef.current); gridLayerRef.current = null }

    if (gridSizeX <= 0 || gridSizeY <= 0) return

    const [[south, west], [north, east]] = loadedBounds
    const [bboxX0, bboxY0] = lonLatTo3857(west, south)
    const [bboxX1, bboxY1] = lonLatTo3857(east, north)

    // Use actual grid cell origin when provided — this aligns visual grid with real cells
    const originX = (gridOriginX != null && gridOriginX > 0) ? gridOriginX : bboxX0
    const originY = (gridOriginY != null && gridOriginY > 0) ? gridOriginY : bboxY0

    // Compute how many grid lines fit from origin to bbox extent
    // Start index: first line >= bboxX0 (skip lines before visible area)
    const iStart = Math.max(0, Math.floor((bboxX0 - originX) / gridSizeX))
    const iEnd   = Math.ceil((bboxX1 - originX) / gridSizeX)
    const jStart = Math.max(0, Math.floor((bboxY0 - originY) / gridSizeY))
    const jEnd   = Math.ceil((bboxY1 - originY) / gridSizeY)

    const nLon = iEnd - iStart + 1
    const nLat = jEnd - jStart + 1
    const maxLines = 1500
    const totalCells = Math.ceil((bboxX1 - bboxX0) / gridSizeX) * Math.ceil((bboxY1 - bboxY0) / gridSizeY)
    const tooManyLines = (nLon + nLat) > maxLines

    if (!tooManyLines) {
      const lines: [number, number][][] = []
      for (let i = iStart; i <= iEnd; i++) {
        const [, lon] = xy3857ToLatLng(originX + i * gridSizeX, 0)
        lines.push([[south, lon], [north, lon]])
      }
      for (let j = jStart; j <= jEnd; j++) {
        const [lat] = xy3857ToLatLng(0, originY + j * gridSizeY)
        lines.push([[lat, west], [lat, east]])
      }
      const layer = L!.polyline(lines as any, {
        color: '#6366f1', weight: 2.5, opacity: 0.75, interactive: false,
      }).addTo(mapRef.current)
      gridLayerRef.current = layer
    }


  }, [mapReady, loadedBounds, gridSizeX, gridSizeY, gridOriginX, gridOriginY])

  // Toggle base map
  useEffect(() => {
    if (!mapRef.current || !osmLayerRef.current || !satLayerRef.current) return
    if (baseMap === 'satellite') {
      if (!mapRef.current.hasLayer(satLayerRef.current)) satLayerRef.current.addTo(mapRef.current)
      if (mapRef.current.hasLayer(osmLayerRef.current)) mapRef.current.removeLayer(osmLayerRef.current)
    } else {
      if (!mapRef.current.hasLayer(osmLayerRef.current)) osmLayerRef.current.addTo(mapRef.current)
      if (mapRef.current.hasLayer(satLayerRef.current)) mapRef.current.removeLayer(satLayerRef.current)
    }
  }, [baseMap])

  // Focus on a specific cell when focusCell (WKT in EPSG:3857) changes
  useEffect(() => {
    if (!focusCell || !L || !mapRef.current) return
    const map = mapRef.current

    if (focusHighlightRef.current) {
      map.removeLayer(focusHighlightRef.current)
      focusHighlightRef.current = null
    }

    // Parse WKT safely — supports POLYGON and MULTIPOLYGON, skips NaN coords
    const allLatLngs: [number, number][] = []
    const ringPattern = /\(\(([^()]+)\)\)/g
    let ringMatch: RegExpExecArray | null
    while ((ringMatch = ringPattern.exec(focusCell)) !== null) {
      for (const pair of ringMatch[1].split(',')) {
        const parts = pair.trim().split(/\s+/)
        if (parts.length < 2) continue
        const x = Number(parts[0])
        const y = Number(parts[1])
        if (!isFinite(x) || !isFinite(y)) continue
        const [lat, lng] = xy3857ToLatLng(x, y)
        if (!isFinite(lat) || !isFinite(lng)) continue
        allLatLngs.push([lat, lng])
      }
    }

    if (allLatLngs.length < 3) return

    const bounds = L.latLngBounds(allLatLngs.map(([lat, lng]) => L.latLng(lat, lng)))
    if (!bounds.isValid()) return
    map.fitBounds(bounds, { padding: [80, 80], maxZoom: 16 })

    const rect = L.polygon(allLatLngs, {
      color: '#ef4444', weight: 3, fillColor: '#ef4444', fillOpacity: 0.25, dashArray: '6 4',
    }).addTo(map)
    focusHighlightRef.current = rect

    const timer = setTimeout(() => {
      if (focusHighlightRef.current) {
        map.removeLayer(focusHighlightRef.current)
        focusHighlightRef.current = null
      }
    }, 6000)
    return () => clearTimeout(timer)
  }, [focusCell])

  // Render uploaded WKT cells directly (upload mode — no country/zone)
  useEffect(() => {
    if (!mapReady || !wktCells?.length || !L) return
    const map = mapRef.current
    if (!map) return

    if (uploadedCellsLayerRef.current) {
      map.removeLayer(uploadedCellsLayerRef.current)
      uploadedCellsLayerRef.current = null
    }

    const features: any[] = []
    let minLat = Infinity, maxLat = -Infinity, minLng = Infinity, maxLng = -Infinity

    for (const wkt of wktCells) {
      const match = wkt.match(/POLYGON\s*\(\(([^)]+)\)\)/)
      if (!match) continue
      const coords4326 = match[1].split(',').map(pair => {
        const [x, y] = pair.trim().split(/\s+/).map(Number)
        const [lat, lng] = xy3857ToLatLng(x, y)
        if (lat < minLat) minLat = lat
        if (lat > maxLat) maxLat = lat
        if (lng < minLng) minLng = lng
        if (lng > maxLng) maxLng = lng
        return [lng, lat] // GeoJSON [lon, lat]
      })
      features.push({ type: 'Feature', geometry: { type: 'Polygon', coordinates: [coords4326] }, properties: {} })
    }

    if (features.length === 0) return

    const layer = L.geoJSON({ type: 'FeatureCollection', features } as any, {
      style: { color: '#6366f1', weight: 1, fillColor: '#3b82f6', fillOpacity: 0.08 },
    }).addTo(map)
    uploadedCellsLayerRef.current = layer

    if (isFinite(minLat)) {
      map.fitBounds([[minLat, minLng], [maxLat, maxLng]], { padding: [20, 20] })
    }

    return () => {
      if (uploadedCellsLayerRef.current && mapRef.current) {
        mapRef.current.removeLayer(uploadedCellsLayerRef.current)
        uploadedCellsLayerRef.current = null
      }
    }
  }, [mapReady, wktCells])

  if (!country && !zone && !wktCells?.length && !uploadMode) return null

  return (
    <div className="space-y-3">
      {/* Layer toggle checkboxes */}
      <div className="flex flex-wrap gap-4 text-sm">
        {(country || zone) && (
        <label className="flex items-center gap-1.5 cursor-pointer">
          <input type="checkbox" checked={showBoundary} onChange={() => setShowBoundary(v => !v)} className="accent-blue-600" />
          <span className="text-slate-600">Boundary</span>
        </label>
        )}
        {(gridSizeX > 0 && gridSizeY > 0 || (wktCells?.length ?? 0) > 0) && (
        <label className="flex items-center gap-1.5 cursor-pointer">
          <input type="checkbox" checked={showGrid} onChange={() => setShowGrid(v => !v)} className="accent-indigo-600" />
          <span className="text-slate-600">Grid</span>
        </label>
        )}
      </div>

      <div className="relative rounded-lg overflow-hidden border" style={{ height: 700 }}>
        {/* Base map toggle — top-right */}
        <div className="absolute top-3 right-3 z-[1000] bg-white/90 backdrop-blur rounded-lg shadow-md border px-3 py-2 flex gap-3 text-xs">
          <label className="flex items-center gap-1.5 cursor-pointer">
            <input type="radio" name="basemap-grid" checked={baseMap === 'osm'} onChange={() => setBaseMap('osm')} className="accent-blue-600" />
            <span className="text-slate-700 font-medium">Street</span>
          </label>
          <label className="flex items-center gap-1.5 cursor-pointer">
            <input type="radio" name="basemap-grid" checked={baseMap === 'satellite'} onChange={() => setBaseMap('satellite')} className="accent-emerald-600" />
            <span className="text-slate-700 font-medium">Satellite</span>
          </label>
        </div>
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
    </div>
  )
}
