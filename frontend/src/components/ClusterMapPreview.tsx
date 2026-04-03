'use client'

import { useEffect, useRef, useState } from 'react'
import { apiGet } from '@/lib/api'
import 'leaflet/dist/leaflet.css'

let L: typeof import('leaflet') | null = null

/** EPSG:3857 → EPSG:4326 */
function xy3857ToLatLng(x: number, y: number): [number, number] {
  const lon = (x / 20037508.34) * 180
  const lat = (Math.atan(Math.exp((y / 20037508.34) * Math.PI)) * 360) / Math.PI - 90
  return [lat, lon]
}

/** EPSG:4326 → EPSG:3857 */
function lonLatTo3857(lon: number, lat: number): [number, number] {
  const x = (lon * 20037508.34) / 180
  const y = Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360)) * 20037508.34 / Math.PI
  return [x, y]
}

/** Return fill color based on Overall_Score */
function scoreColor(score: number): string {
  if (score === 0) return '#ef4444'        // red
  if (score <= 40) return '#fb923c'        // light orange
  if (score <= 70) return '#facc15'        // light yellow
  return '#22c55e'                          // green
}

interface ClusterRow { wkt: string; Overall_Score?: number; [k: string]: any }

interface Props {
  clusters: ClusterRow[]
  focusWkt?: string | null
  activeTab?: number
}

/**
 * Parse WKT POLYGON or MULTIPOLYGON (EPSG:3857) → GeoJSON polygons (EPSG:4326).
 * Skips any features with invalid (NaN/Infinity) coordinates.
 */
function wktToFeatures(wkt: string, score: number): GeoJSON.Feature[] {
  if (!wkt || typeof wkt !== 'string') return []
  const features: GeoJSON.Feature[] = []

  // Extract all coordinate rings: find all (( ... )) blocks
  // Works for both POLYGON ((ring)) and MULTIPOLYGON (((ring)),((ring)))
  const ringPattern = /\(\(([^()]+)\)\)/g
  let ringMatch: RegExpExecArray | null
  while ((ringMatch = ringPattern.exec(wkt)) !== null) {
    const coords = parseCoordRing(ringMatch[1])
    if (coords && coords.length >= 3) {
      features.push({
        type: 'Feature',
        geometry: { type: 'Polygon', coordinates: [coords] },
        properties: { score },
      })
    }
  }

  return features
}

function parseCoordRing(coordStr: string): [number, number][] | null {
  const coords: [number, number][] = []
  for (const pair of coordStr.split(',')) {
    const parts = pair.trim().split(/\s+/)
    if (parts.length < 2) continue
    const x = Number(parts[0])
    const y = Number(parts[1])
    if (!isFinite(x) || !isFinite(y)) continue // skip NaN / Infinity
    const [lat, lng] = xy3857ToLatLng(x, y)
    if (!isFinite(lat) || !isFinite(lng)) continue
    coords.push([lng, lat]) // GeoJSON [lon, lat]
  }
  return coords.length >= 3 ? coords : null
}

export default function ClusterMapPreview({ clusters, focusWkt, activeTab }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<any>(null)
  const clusterLayerRef = useRef<any>(null)
  const boundaryLayerRef = useRef<any>(null)
  const gridLayerRef = useRef<any>(null)
  const focusHighlightRef = useRef<any>(null)
  const osmLayerRef = useRef<any>(null)
  const satLayerRef = useRef<any>(null)

  const [baseMap, setBaseMap] = useState<'osm' | 'satellite'>('osm')
  const [showBoundary, setShowBoundary] = useState(true)
  const [showGrid, setShowGrid] = useState(true)
  const [showClusters, setShowClusters] = useState(true)
  const [loading, setLoading] = useState(false)
  const [mapReady, setMapReady] = useState(false)
  const [gridInfo, setGridInfo] = useState<{
    bounds: [[number, number], [number, number]]
    grid_size_x: number
    grid_size_y: number
    grid_origin_x: number | null
    grid_origin_y: number | null
  } | null>(null)

  // Initialize map + load boundary from grid-info
  useEffect(() => {
    let mounted = true

    ;(async () => {
      if (!containerRef.current) return

      const leaflet = await import('leaflet')
      L = leaflet
      if (!mounted || !containerRef.current) return

      if (!mapRef.current) {
        const map = leaflet.map(containerRef.current, {
          center: [48, 16], zoom: 4, preferCanvas: true, attributionControl: false,
        })
        const osm = leaflet.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 18 }).addTo(map)
        const sat = leaflet.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', { maxZoom: 18 })
        osmLayerRef.current = osm
        satLayerRef.current = sat
        mapRef.current = map
      }

      setTimeout(() => mapRef.current?.invalidateSize(), 200)
      setMapReady(true)

      // Load boundary + grid info
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
        if (!mounted || !L || !mapRef.current) return
        const bLayer = L.geoJSON(info.geojson, {
          style: { color: '#2563eb', weight: 2, fillColor: '#3b82f6', fillOpacity: 0.06 },
        }).addTo(mapRef.current)
        boundaryLayerRef.current = bLayer
        mapRef.current.fitBounds(info.bounds, { padding: [20, 20] })
        if (mounted) setGridInfo({
          bounds: info.bounds,
          grid_size_x: info.grid_size_x,
          grid_size_y: info.grid_size_y,
          grid_origin_x: info.grid_origin_x,
          grid_origin_y: info.grid_origin_y,
        })
      } catch { /* no grid yet */ }
      finally { if (mounted) setLoading(false) }
    })()

    return () => {
      mounted = false
      if (mapRef.current) { try { mapRef.current.remove() } catch {} mapRef.current = null }
      setMapReady(false)
    }
  }, [])

  // Draw clusters when data or map is ready
  useEffect(() => {
    if (!mapReady || !L || !mapRef.current || !clusters.length) return
    const map = mapRef.current

    if (clusterLayerRef.current) { map.removeLayer(clusterLayerRef.current); clusterLayerRef.current = null }

    const features: GeoJSON.Feature[] = []
    for (const row of clusters) {
      if (!row.wkt) continue
      const score = row.Overall_Score ?? 0
      const feats = wktToFeatures(row.wkt, score)
      features.push(...feats)
    }
    if (!features.length) return

    const layer = L.geoJSON({ type: 'FeatureCollection', features } as any, {
      style: (feature: any) => {
        const s = feature?.properties?.score ?? 0
        return { color: '#475569', weight: 1, fillColor: scoreColor(s), fillOpacity: 0.55 }
      },
    }).addTo(map)
    clusterLayerRef.current = layer

    // Fit bounds to clusters
    const bounds = layer.getBounds()
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [30, 30] })
  }, [mapReady, clusters])

  // Focus on a cluster when row is clicked
  useEffect(() => {
    if (!focusWkt || !L || !mapRef.current) return
    const map = mapRef.current

    if (focusHighlightRef.current) { map.removeLayer(focusHighlightRef.current); focusHighlightRef.current = null }

    const feats = wktToFeatures(focusWkt, 0)
    if (!feats.length) return

    const highlight = L.geoJSON({ type: 'FeatureCollection', features: feats } as any, {
      style: { color: '#ef4444', weight: 3, fillColor: '#ef4444', fillOpacity: 0.25, dashArray: '6 4' },
    }).addTo(map)
    focusHighlightRef.current = highlight

    const bounds = highlight.getBounds()
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [80, 80], maxZoom: 14 })

    const timer = setTimeout(() => {
      if (focusHighlightRef.current) { map.removeLayer(focusHighlightRef.current); focusHighlightRef.current = null }
    }, 6000)
    return () => clearTimeout(timer)
  }, [focusWkt])

  // Basemap toggle
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

  // Draw grid lines when gridInfo is ready
  useEffect(() => {
    if (!mapReady || !L || !mapRef.current || !gridInfo) return
    const { grid_size_x, grid_size_y, bounds, grid_origin_x, grid_origin_y } = gridInfo
    if (grid_size_x <= 0 || grid_size_y <= 0) return

    if (gridLayerRef.current) { mapRef.current.removeLayer(gridLayerRef.current); gridLayerRef.current = null }

    const [[south, west], [north, east]] = bounds
    const [xmin3857, ymin3857] = lonLatTo3857(west, south)
    const [xmax3857, ymax3857] = lonLatTo3857(east, north)

    const originX = (grid_origin_x !== null && grid_origin_x !== undefined && grid_origin_x > 0) ? grid_origin_x : xmin3857
    const originY = (grid_origin_y !== null && grid_origin_y !== undefined && grid_origin_y > 0) ? grid_origin_y : ymin3857

    const iStart = Math.max(0, Math.floor((xmin3857 - originX) / grid_size_x))
    const iEnd   = Math.ceil((xmax3857 - originX) / grid_size_x)
    const jStart = Math.max(0, Math.floor((ymin3857 - originY) / grid_size_y))
    const jEnd   = Math.ceil((ymax3857 - originY) / grid_size_y)

    const nLon = iEnd - iStart + 1
    const nLat = jEnd - jStart + 1
    const stepMul = (nLon + nLat > 1500) ? Math.max(1, Math.ceil(Math.max(nLon, nLat) / 750)) : 1

    const lines: [number, number][][] = []
    for (let i = iStart; i <= iEnd; i += stepMul) {
      const [, lon] = xy3857ToLatLng(originX + i * grid_size_x, 0)
      lines.push([[south, lon], [north, lon]])
    }
    for (let j = jStart; j <= jEnd; j += stepMul) {
      const [lat] = xy3857ToLatLng(0, originY + j * grid_size_y)
      lines.push([[lat, west], [lat, east]])
    }

    if (lines.length > 0) {
      const gLayer = L.polyline(lines as any, {
        color: '#6366f1', weight: 1, opacity: 0.5, interactive: false,
      }).addTo(mapRef.current)
      gridLayerRef.current = gLayer
    }
  }, [mapReady, gridInfo])

  // Toggle boundary
  useEffect(() => {
    if (!mapRef.current || !boundaryLayerRef.current) return
    if (showBoundary) mapRef.current.addLayer(boundaryLayerRef.current)
    else mapRef.current.removeLayer(boundaryLayerRef.current)
  }, [showBoundary])

  // Toggle grid
  useEffect(() => {
    if (!mapRef.current || !gridLayerRef.current) return
    if (showGrid) mapRef.current.addLayer(gridLayerRef.current)
    else mapRef.current.removeLayer(gridLayerRef.current)
  }, [showGrid])

  // Toggle clusters
  useEffect(() => {
    if (!mapRef.current || !clusterLayerRef.current) return
    if (showClusters) mapRef.current.addLayer(clusterLayerRef.current)
    else mapRef.current.removeLayer(clusterLayerRef.current)
  }, [showClusters])

  // Invalidate on tab change
  useEffect(() => {
    if (activeTab !== 3) return
    const t1 = setTimeout(() => mapRef.current?.invalidateSize(), 50)
    const t2 = setTimeout(() => mapRef.current?.invalidateSize(), 300)
    return () => { clearTimeout(t1); clearTimeout(t2) }
  }, [activeTab])

  return (
    <div className="bg-white rounded-xl p-4 shadow-sm border space-y-3">
      <h3 className="font-semibold text-slate-700">🗺️ Cluster Map</h3>

      {/* Toggles */}
      <div className="flex flex-wrap gap-4 text-sm">
        <label className="flex items-center gap-1.5 cursor-pointer">
          <input type="checkbox" checked={showBoundary} onChange={() => setShowBoundary(v => !v)} className="accent-blue-600" />
          <span className="text-slate-600">Boundary</span>
        </label>
        <label className="flex items-center gap-1.5 cursor-pointer">
          <input type="checkbox" checked={showGrid} onChange={() => setShowGrid(v => !v)} className="accent-indigo-500" />
          <span className="text-slate-600">Grid</span>
        </label>
        <label className="flex items-center gap-1.5 cursor-pointer">
          <input type="checkbox" checked={showClusters} onChange={() => setShowClusters(v => !v)} className="accent-indigo-600" />
          <span className="text-slate-600">Clusters</span>
        </label>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 text-xs">
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded" style={{ background: '#ef4444' }} /> 0</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded" style={{ background: '#fb923c' }} /> 1–40</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded" style={{ background: '#facc15' }} /> 41–70</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded" style={{ background: '#22c55e' }} /> 71–100</span>
      </div>

      {/* Map container */}
      <div className="relative rounded-lg overflow-hidden border" style={{ height: 600 }}>
        <div className="absolute top-3 right-3 z-[1000] bg-white/90 backdrop-blur rounded-lg shadow-md border px-3 py-2 flex gap-3 text-xs">
          <label className="flex items-center gap-1.5 cursor-pointer">
            <input type="radio" name="cluster-basemap" checked={baseMap === 'osm'} onChange={() => setBaseMap('osm')} className="accent-blue-600" />
            <span className="text-slate-700 font-medium">Street</span>
          </label>
          <label className="flex items-center gap-1.5 cursor-pointer">
            <input type="radio" name="cluster-basemap" checked={baseMap === 'satellite'} onChange={() => setBaseMap('satellite')} className="accent-emerald-600" />
            <span className="text-slate-700 font-medium">Satellite</span>
          </label>
        </div>
        {loading && (
          <div className="absolute inset-0 z-[1000] flex items-center justify-center bg-white/60">
            <span className="text-sm text-slate-500">Loading map...</span>
          </div>
        )}
        <div ref={containerRef} style={{ height: '100%', width: '100%' }} />
      </div>
    </div>
  )
}
