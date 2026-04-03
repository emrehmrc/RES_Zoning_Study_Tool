'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { apiGet } from '@/lib/api'
import type { LayerConfig } from '@/lib/types'
import 'leaflet/dist/leaflet.css'

let L: typeof import('leaflet') | null = null

interface Props {
  layers: LayerConfig[]
  activeTab?: number
  focusCell?: string | null
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

export default function LayerMapPreview({ layers, activeTab, focusCell }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<any>(null)
  const mapReady = useRef(false)

  // Layers stored on the map
  const boundaryLayerRef = useRef<any>(null)
  const gridLayerRef = useRef<any>(null)
  const rasterOverlaysRef = useRef<Map<string, any>>(new Map())

  // Grid info from session
  const [gridInfo, setGridInfo] = useState<{
    geojson: any
    bounds: [[number, number], [number, number]]
    grid_size_x: number
    grid_size_y: number
    grid_origin_x: number | null
    grid_origin_y: number | null
  } | null>(null)

  // Base map layers
  const osmLayerRef = useRef<any>(null)
  const satLayerRef = useRef<any>(null)

  // Visibility toggles
  const [showBoundary, setShowBoundary] = useState(true)
  const [showGrid, setShowGrid] = useState(true)
  const [baseMap, setBaseMap] = useState<'osm' | 'satellite'>('osm')
  const [visibleLayers, setVisibleLayers] = useState<Set<string>>(new Set())
  const [loadingLayers, setLoadingLayers] = useState<Set<string>>(new Set())

  const focusHighlightRef = useRef<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Set wait cursor while any raster layer preview is loading
  useEffect(() => {
    if (loadingLayers.size > 0) {
      document.body.style.cursor = 'wait'
    } else {
      document.body.style.cursor = ''
    }
    return () => { document.body.style.cursor = '' }
  }, [loadingLayers])

  // Initialize Leaflet map once, then fetch grid info
  useEffect(() => {
    let mounted = true

    ;(async () => {
      if (!containerRef.current) return

      // 1) Load leaflet
      const leaflet = await import('leaflet')
      L = leaflet
      if (!mounted || !containerRef.current) return

      // 2) Create map if not exists
      if (!mapRef.current) {
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
      }

      // Force invalidateSize after map is in the DOM
      setTimeout(() => {
        mapRef.current?.invalidateSize()
      }, 200)

      mapReady.current = true

      // 3) Fetch grid info
      setLoading(true)
      try {
        const info = await apiGet<{
          geojson: any
          bounds: [[number, number], [number, number]]
          grid_size_x: number
          grid_size_y: number
          grid_origin_x: number | null
          grid_origin_y: number | null
        }>('/grid-info/')
        if (mounted) setGridInfo(info)
      } catch {
        // Grid not created yet
      } finally {
        if (mounted) setLoading(false)
      }
    })()

    return () => {
      mounted = false
      // Destroy Leaflet map properly to prevent stale state on remount
      if (mapRef.current) {
        try { mapRef.current.remove() } catch { /* ignore */ }
        mapRef.current = null
      }
      mapReady.current = false
    }
  }, [])

  // Draw boundary + grid when gridInfo is available AND map is ready
  useEffect(() => {
    if (!gridInfo || !L || !mapRef.current) return

    const map = mapRef.current

    // Draw boundary
    if (boundaryLayerRef.current) {
      map.removeLayer(boundaryLayerRef.current)
    }
    const bLayer = L.geoJSON(gridInfo.geojson, {
      style: { color: '#2563eb', weight: 2, fillColor: '#3b82f6', fillOpacity: 0.08 },
    }).addTo(map)
    boundaryLayerRef.current = bLayer

    // Fit map, then invalidateSize after a tick to ensure tiles load
    map.fitBounds(gridInfo.bounds, { padding: [20, 20] })
    setTimeout(() => map.invalidateSize(), 100)
    setTimeout(() => map.invalidateSize(), 500)

    // Draw grid lines
    if (gridLayerRef.current) {
      map.removeLayer(gridLayerRef.current)
      gridLayerRef.current = null
    }

    const { grid_size_x, grid_size_y, bounds, grid_origin_x, grid_origin_y } = gridInfo
    if (grid_size_x > 0 && grid_size_y > 0) {
      const [[south, west], [north, east]] = bounds

      // Convert 4326 bounds → 3857 for extent
      const [xmin3857, ymin3857] = lonLatTo3857(west, south)
      const [xmax3857, ymax3857] = lonLatTo3857(east, north)

      // Use true grid origin only if it's a valid EPSG:3857 coordinate (> 0);
      // fall back to boundary bbox origin for old sessions or missing data
      const originX = (grid_origin_x !== null && grid_origin_x !== undefined && grid_origin_x > 0)
        ? grid_origin_x : xmin3857
      const originY = (grid_origin_y !== null && grid_origin_y !== undefined && grid_origin_y > 0)
        ? grid_origin_y : ymin3857

      // Clip grid lines to visible boundary bbox range
      const iStart = Math.max(0, Math.floor((xmin3857 - originX) / grid_size_x))
      const iEnd   = Math.ceil((xmax3857 - originX) / grid_size_x)
      const jStart = Math.max(0, Math.floor((ymin3857 - originY) / grid_size_y))
      const jEnd   = Math.ceil((ymax3857 - originY) / grid_size_y)

      const nLon = iEnd - iStart + 1
      const nLat = jEnd - jStart + 1
      const lines: [number, number][][] = []

      // stepMul: draw every Nth line when too dense (always show something)
      const stepMul = (nLon + nLat > 1500)
        ? Math.max(1, Math.ceil(Math.max(nLon, nLat) / 750))
        : 1

      // Vertical lines (constant X in 3857 → constant lon in 4326)
      for (let i = iStart; i <= iEnd; i += stepMul) {
        const [, lon] = xy3857ToLatLng(originX + i * grid_size_x, 0)
        lines.push([[south, lon], [north, lon]])
      }
      // Horizontal lines (constant Y in 3857 → constant lat in 4326)
      for (let j = jStart; j <= jEnd; j += stepMul) {
        const [lat] = xy3857ToLatLng(0, originY + j * grid_size_y)
        lines.push([[lat, west], [lat, east]])
      }

      if (lines.length > 0) {
        const gLayer = L.polyline(lines as any, {
          color: '#6366f1', weight: 2.5, opacity: 0.75, interactive: false,
        }).addTo(map)
        gridLayerRef.current = gLayer
      }
    }
  }, [gridInfo])

  // When this tab becomes active, force Leaflet to recalculate container size
  useEffect(() => {
    if (activeTab !== 1) return
    if (!mapRef.current) return
    // Multiple invalidateSize calls to ensure tiles fully render
    const t1 = setTimeout(() => {
      mapRef.current?.invalidateSize()
      if (gridInfo) mapRef.current?.fitBounds(gridInfo.bounds, { padding: [20, 20] })
    }, 50)
    const t2 = setTimeout(() => mapRef.current?.invalidateSize(), 300)
    const t3 = setTimeout(() => mapRef.current?.invalidateSize(), 600)
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3) }
  }, [activeTab, gridInfo])

  // Toggle boundary visibility
  useEffect(() => {
    if (!mapRef.current || !boundaryLayerRef.current) return
    if (showBoundary) mapRef.current.addLayer(boundaryLayerRef.current)
    else mapRef.current.removeLayer(boundaryLayerRef.current)
  }, [showBoundary])

  // Toggle grid visibility
  useEffect(() => {
    if (!mapRef.current || !gridLayerRef.current) return
    if (showGrid) mapRef.current.addLayer(gridLayerRef.current)
    else mapRef.current.removeLayer(gridLayerRef.current)
  }, [showGrid])

  // Load raster preview for a layer
  const loadRasterPreview = useCallback(async (path: string, name: string) => {
    if (!L || !mapRef.current) return
    if (rasterOverlaysRef.current.has(path)) return

    setLoadingLayers(prev => new Set(prev).add(path))
    try {
      const res = await apiGet<{
        bounds: [[number, number], [number, number]]
        image: string
        width: number
        height: number
        value_range: [number, number]
      }>(`/raster-preview/?path=${encodeURIComponent(path)}`)

      const overlay = L.imageOverlay(res.image, res.bounds, {
        opacity: 0.7,
        interactive: false,
      }).addTo(mapRef.current)

      rasterOverlaysRef.current.set(path, overlay)
      setVisibleLayers(prev => new Set(prev).add(path))
    } catch (e: any) {
      setError(`Failed to load preview for ${name}: ${e.message}`)
    } finally {
      setLoadingLayers(prev => {
        const next = new Set(prev)
        next.delete(path)
        return next
      })
    }
  }, [])

  // Toggle raster layer visibility
  const toggleLayerVisibility = useCallback((path: string, name: string) => {
    const overlay = rasterOverlaysRef.current.get(path)

    if (!overlay) {
      loadRasterPreview(path, name)
      return
    }

    if (visibleLayers.has(path)) {
      mapRef.current?.removeLayer(overlay)
      setVisibleLayers(prev => { const n = new Set(prev); n.delete(path); return n })
    } else {
      overlay.addTo(mapRef.current)
      setVisibleLayers(prev => new Set(prev).add(path))
    }
  }, [visibleLayers, loadRasterPreview])

  // Clean up raster overlays for layers that have been removed
  useEffect(() => {
    const currentPaths = new Set(layers.map(l => l.path))
    rasterOverlaysRef.current.forEach((overlay, path) => {
      if (!currentPaths.has(path)) {
        mapRef.current?.removeLayer(overlay)
        rasterOverlaysRef.current.delete(path)
        setVisibleLayers(prev => { const n = new Set(prev); n.delete(path); return n })
      }
    })
  }, [layers])

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

  return (
    <div className="bg-white rounded-xl p-4 shadow-sm border space-y-3">
      <h3 className="font-semibold text-slate-700">🗺️ Map</h3>

      {/* Layer toggle checkboxes */}
      <div className="flex flex-wrap gap-4 text-sm">
        <label className="flex items-center gap-1.5 cursor-pointer">
          <input type="checkbox" checked={showBoundary} onChange={() => setShowBoundary(v => !v)} className="accent-blue-600" />
          <span className="text-slate-600">Boundary</span>
        </label>
        <label className="flex items-center gap-1.5 cursor-pointer">
          <input type="checkbox" checked={showGrid} onChange={() => setShowGrid(v => !v)} className="accent-indigo-600" />
          <span className="text-slate-600">Grid</span>
        </label>
        {layers.map((l) => (
          <label key={l.path} className="flex items-center gap-1.5 cursor-pointer">
            <input type="checkbox" checked={visibleLayers.has(l.path)} onChange={() => toggleLayerVisibility(l.path, l.prefix)} className="accent-emerald-600" />
            <span className="text-slate-600">
              {l.prefix}
              {loadingLayers.has(l.path) && <span className="ml-1 text-xs text-amber-500">(loading...)</span>}
            </span>
          </label>
        ))}
      </div>

      {/* Map */}
      <div className="relative rounded-lg overflow-hidden border" style={{ height: 700 }}>
        {/* Base map toggle — top-right */}
        <div className="absolute top-3 right-3 z-[1000] bg-white/90 backdrop-blur rounded-lg shadow-md border px-3 py-2 flex gap-3 text-xs">
          <label className="flex items-center gap-1.5 cursor-pointer">
            <input type="radio" name="basemap-layer" checked={baseMap === 'osm'} onChange={() => setBaseMap('osm')} className="accent-blue-600" />
            <span className="text-slate-700 font-medium">Street</span>
          </label>
          <label className="flex items-center gap-1.5 cursor-pointer">
            <input type="radio" name="basemap-layer" checked={baseMap === 'satellite'} onChange={() => setBaseMap('satellite')} className="accent-emerald-600" />
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
