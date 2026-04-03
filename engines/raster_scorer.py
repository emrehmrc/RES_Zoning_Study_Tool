"""
Universal Raster Distance & Coverage Calculator - ENHANCED
Now supports: Distance, Coverage, Mean, Max, Min, and Categorical modes
"""
import gc
import math
import os
import sys
import ctypes
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterstats import zonal_stats
import pandas as pd
from osgeo import gdal, osr
from multiprocessing import Pool, cpu_count
import time
import psutil
from pyproj.exceptions import ProjError

# ── Fix PROJ_LIB before any CRS operations ──────────────────────────
# GDAL 3.11 ships PROJ 9.7 which requires proj.db with
# DATABASE.LAYOUT.VERSION.MINOR >= 6.  pyproj's bundled copy is only
# minor=4, so we must prefer the newest proj.db available.
def _init_proj_env():
    """Set PROJ_LIB to the newest compatible proj data directory."""
    import sqlite3

    sp = os.path.join(sys.prefix, 'Lib', 'site-packages')
    # Candidate directories ordered by typical freshness
    candidate_dirs = []
    # rasterio ships its own PROJ data
    candidate_dirs.append(os.path.join(sp, 'rasterio', 'proj_data'))
    # osgeo (GDAL wheel)
    candidate_dirs.append(os.path.join(sp, 'osgeo', 'data', 'proj'))
    # pyogrio
    candidate_dirs.append(os.path.join(sp, 'pyogrio', 'proj_data'))
    # pyproj
    try:
        import pyproj
        candidate_dirs.append(pyproj.datadir.get_data_dir())
    except Exception:
        pass
    # fiona
    candidate_dirs.append(os.path.join(sp, 'fiona', 'proj_data'))

    best_dir = None
    best_minor = -1
    for d in candidate_dirs:
        db = os.path.join(d, 'proj.db') if d else ''
        if not os.path.isfile(db):
            continue
        try:
            conn = sqlite3.connect(db)
            row = conn.execute(
                "SELECT value FROM metadata "
                "WHERE key='DATABASE.LAYOUT.VERSION.MINOR'"
            ).fetchone()
            conn.close()
            minor = int(row[0]) if row else 0
        except Exception:
            minor = 0
        if minor > best_minor:
            best_minor = minor
            best_dir = d

    if best_dir:
        os.environ['PROJ_LIB'] = best_dir
        os.environ['PROJ_DATA'] = best_dir  # some PROJ builds read this
        try:
            import pyproj
            pyproj.datadir.set_data_dir(best_dir)
        except Exception:
            pass

_init_proj_env()

# Limit GDAL's internal block cache to prevent allocation failures with large rasters
gdal.SetConfigOption('GDAL_CACHEMAX', '512')
gdal.SetConfigOption('GTIFF_SRS_SOURCE', 'EPSG')


def get_short_path(long_path):
    """Converts a Windows path with special characters to a safe short path."""
    buf = ctypes.create_unicode_buffer(260)
    ctypes.windll.kernel32.GetShortPathNameW(long_path, buf, 260)
    return buf.value


def init_worker_env():
    """Initializes the GDAL/PROJ environment for each parallel worker."""
    from osgeo import gdal
    
    _init_proj_env()
    gdal.SetConfigOption('GTIFF_SRS_SOURCE', 'EPSG')
    # Limit GDAL block cache to 256 MB per worker to prevent allocation failures
    gdal.SetConfigOption('GDAL_CACHEMAX', '256')
    gdal.UseExceptions()


def _get_safe_worker_count(n_workers=None, per_worker_mb=512):
    """Determine safe number of workers based on available memory."""
    try:
        available_mb = psutil.virtual_memory().available / (1024 * 1024)
        max_by_mem = max(1, int(available_mb / per_worker_mb))
        cpu_based = max(1, cpu_count() - 1) if n_workers is None else n_workers
        safe = min(cpu_based, max_by_mem)
        print(f"   Memory-safe workers: {safe} (available: {available_mb:.0f} MB, per-worker estimate: {per_worker_mb} MB)")
        return safe
    except Exception:
        return max(1, (n_workers or 2))


# MOVED OUTSIDE CLASS - Required for Windows multiprocessing pickling
def _process_layer_worker(grid_gdf, raster_path, layer_prefix, analysis_modes, target_value, config):
    """Worker function for parallel processing - MUST be at module level"""
    init_worker_env()
    scorer = UniversalRasterScorer(config)
    return scorer.calculate_layer(grid_gdf, raster_path, layer_prefix, analysis_modes, target_value)


class UniversalRasterScorer:
    """
    Enhanced raster analysis supporting multiple modes:
    - 'distance': Distance to target pixel value
    - 'coverage': Percentage of target pixel value
    - 'mean': Mean of all pixel values
    - 'max': Maximum pixel value
    - 'min': Minimum pixel value
    - 'categorical': Distribution of all pixel values
    """
    
    # Available analysis modes
    ANALYSIS_MODES = {
        'distance': 'Distance to Target Value (km)',
        'coverage': 'Coverage Percentage (%)',
        'mean': 'Mean Pixel Value',
        'max': 'Maximum Pixel Value',
        'min': 'Minimum Pixel Value',
        'median': 'Median Pixel Value',
        'std': 'Standard Deviation',
        'categorical': 'Categorical Distribution'
    }
    
    def __init__(self, config=None):
        self.config = config or {}
        self.proximity_cache = {}
        self.max_window_mb = 1024  # hard cap per processing window

    def _transform_grid_to_raster_crs(self, grid_gdf, raster_crs):
        """Safely transform grid to raster CRS with fallbacks for problematic CRS metadata."""
        if grid_gdf.crs is None:
            # Grid is generated in EPSG:3857 in this project; enforce it if missing.
            grid_gdf = grid_gdf.set_crs("EPSG:3857", allow_override=True)

        if raster_crs is None:
            # No raster CRS metadata; assume same CRS to avoid hard-failing.
            return grid_gdf

        try:
            return grid_gdf.to_crs(raster_crs)
        except ProjError:
            # Reinitialize PROJ env in case external apps poisoned PROJ_LIB at runtime.
            _init_proj_env()
            try:
                return grid_gdf.to_crs(raster_crs)
            except ProjError:
                pass

        crs_text = str(raster_crs).upper()

        # Some rasters store CRS as LOCAL_CS with unit EPSG codes only (e.g. EPSG:9001).
        # Map known names to their real projected CRS EPSG code.
        local_name_to_epsg = {
            'ALBANIA TM 2010': 'EPSG:6870',
            'ALBANIA LCC 2010': 'EPSG:6962',
        }
        for local_name, epsg_code in local_name_to_epsg.items():
            if local_name in crs_text:
                return grid_gdf.to_crs(epsg_code)

        # Fallback heuristics for common CRS cases where source metadata is odd.
        if '4326' in crs_text:
            return grid_gdf.to_crs("EPSG:4326")
        if '3857' in crs_text or '900913' in crs_text:
            if str(grid_gdf.crs).upper() in ['EPSG:3857', '3857']:
                return grid_gdf
            return grid_gdf.to_crs("EPSG:3857")

        raise ValueError(
            f"CRS transform failed. grid_crs={grid_gdf.crs}, raster_crs={raster_crs}, "
            f"PROJ_LIB={os.environ.get('PROJ_LIB')}"
        )
    
    def _compute_proximity_gdal(self, raster_path, target_value, window=None, max_distance_km=100):
        """
        Dynamic proximity calculation that adapts to any pixel size.
        Handles both square and non-square pixels correctly.
        """
        src_ds = gdal.Open(raster_path)
        src_band = src_ds.GetRasterBand(1)
        max_width = src_ds.RasterXSize
        max_height = src_ds.RasterYSize
        
        src_nodata = src_band.GetNoDataValue()
        if src_nodata is None:
            src_nodata = 255
        
        src_gt = src_ds.GetGeoTransform()
        pixel_width = abs(src_gt[1])
        pixel_height = abs(src_gt[5])
        avg_pixel_size = (pixel_width + pixel_height) / 2
        
        pixel_diff = abs(pixel_width - pixel_height)
        is_square = pixel_diff < (avg_pixel_size * 0.01)
        
        if not is_square:
            print(f"   - Non-square pixels: {pixel_width:.6f} x {pixel_height:.6f} (avg: {avg_pixel_size:.6f})")
        else:
            print(f"   - Square pixels: {avg_pixel_size:.6f} x {avg_pixel_size:.6f}")
        
        # Detect geographic CRS (degrees) and compute meter-equivalent pixel size
        _srs = osr.SpatialReference()
        _srs.ImportFromWkt(src_ds.GetProjection())
        is_geographic = _srs.IsGeographic()
        
        if is_geographic:
            center_y = src_gt[3] + src_gt[5] * max_height / 2
            px_m_x = pixel_width * 111_320 * math.cos(math.radians(center_y))
            px_m_y = pixel_height * 111_320
            pixel_size_m = (px_m_x + px_m_y) / 2
            print(f"   - Geographic CRS: ~{pixel_size_m:.1f} m/pixel (at lat {center_y:.2f}°)")
        else:
            pixel_size_m = avg_pixel_size
        
        if window:
            target_w = int(window.width)
            target_h = int(window.height)
            win_xoff = int(window.col_off)
            win_yoff = int(window.row_off)
        else:
            target_w = max_width
            target_h = max_height
            win_xoff = 0
            win_yoff = 0

        # Cap MEM dataset resolution to avoid OOM on very large rasters.
        # For distance mode, coarser resolution is still accurate enough (km-scale results).
        MAX_PROXIMITY_DIM = 6000
        scale = min(1.0, MAX_PROXIMITY_DIM / max(target_w, target_h, 1))
        scaled_w = max(1, int(target_w * scale))
        scaled_h = max(1, int(target_h * scale))
        # Effective pixel size grows proportionally when downsampled.
        effective_pixel_size_m = pixel_size_m / scale
        if scale < 1.0:
            print(f"   - Downsampling {target_w}x{target_h} → {scaled_w}x{scaled_h} "
                  f"(scale={scale:.4f}) to fit proximity in memory")

        drv = gdal.GetDriverByName('MEM')
        global_src_ds = drv.Create('', scaled_w, scaled_h, 1, gdal.GDT_Byte)
        global_band = global_src_ds.GetRasterBand(1)

        zero_array = np.zeros((scaled_h, scaled_w), dtype=np.uint8)
        global_band.WriteArray(zero_array)

        win_gt = list(src_gt)
        win_gt[0] += win_xoff * src_gt[1]
        win_gt[3] += win_yoff * src_gt[5]
        if scale < 1.0:
            win_gt[1] = src_gt[1] / scale   # wider pixels
            win_gt[5] = src_gt[5] / scale   # taller pixels (negative)
        global_src_ds.SetGeoTransform(win_gt)
        global_src_ds.SetProjection(src_ds.GetProjection())

        ixoff = max(0, win_xoff)
        iyoff = max(0, win_yoff)
        ixsize = min(win_xoff + target_w, max_width) - ixoff
        iysize = min(win_yoff + target_h, max_height) - iyoff

        if ixsize > 0 and iysize > 0:
            buf_xsize = max(1, int(ixsize * scale))
            buf_ysize = max(1, int(iysize * scale))
            raster_data = src_band.ReadAsArray(ixoff, iyoff, ixsize, iysize, buf_xsize, buf_ysize)

            if src_nodata is not None:
                raster_data = np.where(raster_data == src_nodata, 0, raster_data)

            dest_xoff = max(0, int((ixoff - win_xoff) * scale))
            dest_yoff = max(0, int((iyoff - win_yoff) * scale))
            global_band.WriteArray(raster_data, dest_xoff, dest_yoff)

        prox_ds = drv.Create('', scaled_w, scaled_h, 1, gdal.GDT_Float32)
        prox_band = prox_ds.GetRasterBand(1)
        prox_ds.SetGeoTransform(win_gt)
        prox_ds.SetProjection(src_ds.GetProjection())
        prox_band.SetNoDataValue(-9999)

        max_distance_meters = max_distance_km * 1000
        max_distance_pixels = int(max_distance_meters / effective_pixel_size_m)
        
        print(f"   > Max search distance: {max_distance_km} km = {max_distance_pixels} pixels")

        gdal.PushErrorHandler('CPLQuietErrorHandler')
        gdal.ComputeProximity(
            global_band,
            prox_band,
            [f'VALUES={target_value}',
             f'MAXDIST={max_distance_pixels}',
             'DISTUNITS=PIXEL',
             f'NODATA=-9999']
        )
        gdal.PopErrorHandler()

        proximity_pixels = prox_band.ReadAsArray()
        proximity_meters = proximity_pixels * effective_pixel_size_m
        proximity_meters = np.where(proximity_pixels == -9999, -9999, proximity_meters)
        
        proximity_meters = np.where(proximity_meters == -9999, 999999, proximity_meters)
        
        # Explicitly close GDAL datasets to free memory
        src_band = global_band = prox_band = None
        src_ds = global_src_ds = prox_ds = None
        del zero_array
        gc.collect()
        
        return proximity_meters
    
    def _estimate_raster_memory_mb(self, raster_path, grid_gdf):
        """Estimate memory needed to load the raster window for the given grid."""
        try:
            with rasterio.open(raster_path) as src:
                grid_transformed = self._transform_grid_to_raster_crs(grid_gdf, src.crs)
                xmin, ymin, xmax, ymax = grid_transformed.total_bounds
                window = from_bounds(xmin, ymin, xmax, ymax, src.transform)
                # float32 = 4 bytes per pixel, proximity doubles it
                pixels = int(window.height) * int(window.width)
                return (pixels * 4 * 3) / (1024 * 1024)  # 3x for data + proximity + result
        except Exception:
            return 999999

    def calculate_layer(self, grid_gdf, raster_path, layer_prefix, analysis_modes=None, target_value=1):
        """
        Universal layer calculation supporting multiple analysis modes.
        Automatically chunks large grids to avoid memory allocation failures.
        
        Parameters:
        -----------
        grid_gdf : GeoDataFrame
            Grid cells to analyze
        raster_path : str
            Path to raster file
        layer_prefix : str
            Prefix for output columns
        analysis_modes : list
            List of analysis modes to perform (e.g., ['distance', 'mean', 'max'])
        target_value : int
            Target pixel value (for distance and coverage modes)
        
        Returns:
        --------
        DataFrame with results for each requested mode
        """
        if analysis_modes is None:
            analysis_modes = ['distance']

        # Check if we need to chunk to avoid memory errors
        est_mb = self._estimate_raster_memory_mb(raster_path, grid_gdf)
        try:
            available_mb = psutil.virtual_memory().available / (1024 * 1024)
        except Exception:
            available_mb = 4096

        # If estimated memory is high, split into spatial chunks (even for small grids).
        # A small number of cells can still span a huge extent and trigger large allocations.
        if est_mb > available_mb * 0.6 or est_mb > self.max_window_mb:
            n_chunks = max(2, int(np.ceil(est_mb / max(256, available_mb * 0.35))))
            n_chunks = min(max(2, n_chunks), 32)
            print(f"   ! Large raster detected ({est_mb:.0f} MB est, {available_mb:.0f} MB avail). Splitting into {n_chunks} chunks.")
            chunks = self._split_grid_spatially(grid_gdf, n_chunks)
            chunk_results = []
            for ci, chunk in enumerate(chunks):
                print(f"   > Processing chunk {ci+1}/{len(chunks)} ({len(chunk)} cells)...")
                chunk_result = self._calculate_layer_with_retry(
                    chunk,
                    raster_path,
                    layer_prefix,
                    analysis_modes,
                    target_value,
                    depth=0,
                )
                chunk_results.append(chunk_result)
                gc.collect()
            return pd.concat(chunk_results, ignore_index=True)

        return self._calculate_layer_with_retry(
            grid_gdf,
            raster_path,
            layer_prefix,
            analysis_modes,
            target_value,
            depth=0,
        )

    def _calculate_layer_with_retry(self, grid_gdf, raster_path, layer_prefix, analysis_modes, target_value, depth=0):
        """Retry layer calculation by recursively sub-chunking when allocation errors occur."""
        try:
            return self._calculate_layer_inner(grid_gdf, raster_path, layer_prefix, analysis_modes, target_value)
        except (MemoryError, ValueError, RuntimeError, OSError) as e:
            msg = str(e).lower()
            is_alloc_error = (
                'unable to allocate' in msg
                or 'array is too big' in msg
                or 'out of memory' in msg
                or 'cannot allocate memory' in msg
                or 'read failed' in msg
                or 'not enough' in msg
                or 'allocation' in msg
            )
            if not is_alloc_error:
                raise
            if len(grid_gdf) <= 1 or depth >= 6:
                raise RuntimeError(
                    f"Allocation error after retries (depth={depth}, cells={len(grid_gdf)}): {e}"
                )

            print(
                f"   ! Allocation error at depth {depth} for {len(grid_gdf)} cells. "
                f"Sub-chunking and retrying..."
            )
            sub_chunks = self._split_grid_spatially(grid_gdf, 2)
            sub_results = []
            for sub in sub_chunks:
                if len(sub) == 0:
                    continue
                sub_results.append(
                    self._calculate_layer_with_retry(
                        sub,
                        raster_path,
                        layer_prefix,
                        analysis_modes,
                        target_value,
                        depth=depth + 1,
                    )
                )
            if not sub_results:
                raise RuntimeError("Sub-chunking produced no cells during allocation recovery.")
            return pd.concat(sub_results, ignore_index=True)

    def _calculate_layer_inner(self, grid_gdf, raster_path, layer_prefix, analysis_modes, target_value):
        """Core layer calculation - operates on a grid subset that fits in memory."""
        safe_nodata = 255
        
        with rasterio.open(raster_path) as src:
            raster_crs = src.crs
            grid_transformed = self._transform_grid_to_raster_crs(grid_gdf, raster_crs)

            xmin, ymin, xmax, ymax = grid_transformed.total_bounds
            window = from_bounds(xmin, ymin, xmax, ymax, src.transform)

            # Cap read resolution to avoid OOM when the window spans millions of pixels.
            MAX_DATA_DIM = 6000
            win_w = max(1, int(window.width))
            win_h = max(1, int(window.height))
            scale_r = min(1.0, MAX_DATA_DIM / max(win_w, win_h, 1))
            out_w = max(1, int(win_w * scale_r))
            out_h = max(1, int(win_h * scale_r))

            from rasterio.enums import Resampling
            raster_data = src.read(
                1, window=window, boundless=True, fill_value=safe_nodata,
                out_shape=(out_h, out_w),
                resampling=Resampling.nearest,
            ).astype(np.float32)
            win_transform = src.window_transform(window)
            if scale_r < 1.0:
                from rasterio.transform import Affine
                win_transform = Affine(
                    win_transform.a / scale_r, win_transform.b, win_transform.c,
                    win_transform.d, win_transform.e / scale_r, win_transform.f,
                )
        
        results = []
        
        # Process each analysis mode
        for mode in analysis_modes:
            print(f"   * Processing mode: {mode}")
            
            if mode == 'distance':
                # Distance calculation
                proximity_meters = self._compute_proximity_gdal(raster_path, target_value, window)
                dist_km_array = (proximity_meters / 1000.0).astype(np.float32)
                del proximity_meters  # Free the raw array immediately
                
                dist_stats = zonal_stats(grid_transformed, dist_km_array, affine=win_transform, 
                                        stats=['min'], nodata=safe_nodata, all_touched=True)
                del dist_km_array  # Free after zonal_stats
                
                for i, s in enumerate(dist_stats):
                    min_dist = s['min'] if s['min'] is not None else 99999
                    
                    if i >= len(results):
                        results.append({
                            'cell_id': grid_gdf.iloc[i]['cell_id'],
                            f'{layer_prefix}_dist_km': round(min_dist, 3)
                        })
                    else:
                        results[i][f'{layer_prefix}_dist_km'] = round(min_dist, 3)
            
            elif mode == 'coverage':
                # Coverage calculation
                coverage_stats = zonal_stats(grid_transformed, raster_data, affine=win_transform, 
                                            categorical=True, nodata=safe_nodata, all_touched=True)
                
                for i, cat_dict in enumerate(coverage_stats):
                    target_count = cat_dict.get(target_value, 0)
                    total_count = sum(cat_dict.values())
                    coverage_pct = (target_count / total_count * 100) if total_count > 0 else 0
                    
                    if i >= len(results):
                        results.append({
                            'cell_id': grid_gdf.iloc[i]['cell_id'],
                            f'{layer_prefix}_coverage_pct': round(coverage_pct, 2)
                        })
                    else:
                        results[i][f'{layer_prefix}_coverage_pct'] = round(coverage_pct, 2)
            
            elif mode in ['mean', 'max', 'min', 'median', 'std']:
                # Statistical calculations
                stat_name = mode
                stats_result = zonal_stats(grid_transformed, raster_data, affine=win_transform, 
                                          stats=[stat_name], nodata=safe_nodata, all_touched=True)
                
                for i, s in enumerate(stats_result):
                    value = s[stat_name] if s[stat_name] is not None else 0
                    
                    if i >= len(results):
                        results.append({
                            'cell_id': grid_gdf.iloc[i]['cell_id'],
                            f'{layer_prefix}_{mode}': round(value, 3)
                        })
                    else:
                        results[i][f'{layer_prefix}_{mode}'] = round(value, 3)
            
            elif mode == 'categorical':
                # Categorical distribution
                cat_stats = zonal_stats(grid_transformed, raster_data, affine=win_transform, 
                                       categorical=True, nodata=safe_nodata, all_touched=True)
                
                for i, cat_dict in enumerate(cat_stats):
                    if i >= len(results):
                        results.append({
                            'cell_id': grid_gdf.iloc[i]['cell_id'],
                            f'{layer_prefix}_categories': str(cat_dict)
                        })
                    else:
                        results[i][f'{layer_prefix}_categories'] = str(cat_dict)
        
        # Handle coverage + distance interaction
        if 'coverage' in analysis_modes and 'distance' in analysis_modes:
            for i, row in enumerate(results):
                if f'{layer_prefix}_coverage_pct' in row and row[f'{layer_prefix}_coverage_pct'] > 0:
                    results[i][f'{layer_prefix}_dist_km'] = 0.0
        
        # Explicitly free large arrays to reduce memory pressure
        del raster_data
        gc.collect()
        
        return pd.DataFrame(results)
    
    def _split_grid_spatially(self, grid_gdf, n_chunks):
        """Split grid into roughly equal spatial chunks"""
        xmin, ymin, xmax, ymax = grid_gdf.total_bounds
        
        x_range = xmax - xmin
        y_range = ymax - ymin
        
        if x_range > y_range:
            x_splits = np.linspace(xmin, xmax, n_chunks + 1)
            chunks = []
            for i in range(n_chunks):
                mask = (grid_gdf.geometry.centroid.x >= x_splits[i]) & \
                       (grid_gdf.geometry.centroid.x < x_splits[i + 1])
                chunk = grid_gdf[mask].copy()
                if len(chunk) > 0:
                    chunks.append(chunk)
        else:
            y_splits = np.linspace(ymin, ymax, n_chunks + 1)
            chunks = []
            for i in range(n_chunks):
                mask = (grid_gdf.geometry.centroid.y >= y_splits[i]) & \
                       (grid_gdf.geometry.centroid.y < y_splits[i + 1])
                chunk = grid_gdf[mask].copy()
                if len(chunk) > 0:
                    chunks.append(chunk)
        
        print(f"Split into {len(chunks)} chunks: {[len(c) for c in chunks]} cells each")
        return chunks
    
    def calculate_layers_adaptive(self, grid_gdf, layer_configs, 
                              chunk_size=5000, n_workers=None):
        """
        Adaptive layer calculation with automatic strategy selection.
        Memory-aware: adjusts worker count and chunking based on available RAM.
        """
        n_workers = _get_safe_worker_count(n_workers)
        
        n_cells = len(grid_gdf)
        n_layers = len(layer_configs)
        
        total_start = time.time()
        
        print(f"{'='*60}")
        print(f"> ADAPTIVE STRATEGY SELECTION")
        print(f"{'='*60}")
        print(f"Grid size: {n_cells:,} cells")
        print(f"Layers: {n_layers}")
        print(f"Available workers: {n_workers}")
        
        # Estimate total raster size across all layers
        total_est_mb = sum(
            self._estimate_raster_memory_mb(layer['path'], grid_gdf)
            for layer in layer_configs
        )
        try:
            available_mb = psutil.virtual_memory().available / (1024 * 1024)
        except Exception:
            available_mb = 4096

        any_layer_large = any(
            self._estimate_raster_memory_mb(layer['path'], grid_gdf) > 500
            for layer in layer_configs
        )

        print(f"Total estimated raster memory: {total_est_mb:.0f} MB")
        print(f"Available memory: {available_mb:.0f} MB")
        print(f"Any large layer (>500 MB): {any_layer_large}")
        
        # Strategy selection — never parallelize layers when rasters are large
        if any_layer_large or total_est_mb > available_mb * 0.4 or n_layers >= 3:
            # Process layers one at a time to avoid GDAL cache exhaustion
            print(f"* Strategy: SEQUENTIAL-LAYERS (large rasters or many layers)")
            print(f"{'='*60}\n")
            result = self._process_layers_sequential(grid_gdf, layer_configs, n_workers)
        
        elif n_cells < 5000 and n_layers <= 2:
            print(f"* Strategy: LAYER PARALLELIZATION (small grid, few layers)")
            print(f"{'='*60}\n")
            result = self._parallel_by_layers(grid_gdf, layer_configs, n_workers)
        
        else:
            print(f"* Strategy: GRID-CHUNKED (large grid)")
            print(f"   Using {n_workers} parallel chunks")
            print(f"{'='*60}\n")
            result = self._process_grid_chunked(grid_gdf, layer_configs, chunk_size, n_workers)
        
        total_time = time.time() - total_start
        
        print(f"\n{'='*60}")
        print(f"V ADAPTIVE PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Avg per cell: {total_time/n_cells*1000:.2f}ms")
        print(f"Avg per layer: {total_time/n_layers:.2f}s")
        print(f"{'='*60}\n")
        
        return result
    
    def _parallel_by_layers(self, grid_gdf, layer_configs, n_workers):
        """Process layers in parallel — only safe for small/few rasters."""
        print(f"> Processing all {len(layer_configs)} layers in parallel...")
        
        safe_workers = min(_get_safe_worker_count(n_workers), len(layer_configs))
        
        args_list = [
            (grid_gdf, layer['path'], layer['prefix'], 
             layer.get('analysis_modes', ['distance']), 
             layer.get('target_value', 1), layer.get('config', {}))
            for layer in layer_configs
        ]
        
        with Pool(processes=safe_workers, initializer=init_worker_env) as pool:
            results = pool.starmap(_process_layer_worker, args_list)
        
        merged = grid_gdf[['cell_id', 'wkt']].copy()
        for result in results:
            merged = merged.merge(result, on='cell_id', how='left')
        
        return merged

    def _process_layers_sequential(self, grid_gdf, layer_configs, n_workers):
        """
        Process layers ONE AT A TIME to avoid GDAL block-cache exhaustion.
        Each layer still uses spatial chunking internally via calculate_layer().
        """
        merged = grid_gdf[['cell_id', 'wkt']].copy()

        for layer_idx, layer in enumerate(layer_configs):
            print(f"\n{'-'*60}")
            print(f"> Layer {layer_idx+1}/{len(layer_configs)}: {layer['prefix']}")
            print(f"{'-'*60}")
            layer_start = time.time()

            layer_result = self.calculate_layer(
                grid_gdf,
                layer['path'],
                layer['prefix'],
                layer.get('analysis_modes', ['distance']),
                layer.get('target_value', 1),
            )

            merged = merged.merge(layer_result, on='cell_id', how='left')

            # Aggressively free memory between layers
            del layer_result
            gc.collect()

            print(f"   V Completed in {time.time()-layer_start:.2f}s")

        return merged
    
    def _process_grid_chunked(self, grid_gdf, layer_configs, chunk_size, n_workers):
        """Process large grids by chunking with memory-aware parallelism."""
        n_chunks = max(1, len(grid_gdf) // chunk_size)
        safe_workers = _get_safe_worker_count(n_workers)
        n_chunks = min(n_chunks, safe_workers * 2)
        
        print(f"Splitting grid into {n_chunks} chunks...")
        grid_chunks = self._split_grid_spatially(grid_gdf, n_chunks)
        
        all_results = []
        
        for layer_idx, layer in enumerate(layer_configs):
            print(f"\n{'-'*60}")
            print(f"> Layer {layer_idx+1}/{len(layer_configs)}: {layer['prefix']}")
            print(f"{'-'*60}")
            layer_start = time.time()
            
            args_list = [
                (chunk, layer['path'], layer['prefix'], 
                layer.get('analysis_modes', ['distance']),
                layer.get('target_value', 1), layer.get('config', {}))
                for chunk in grid_chunks
            ]
            
            with Pool(processes=safe_workers, initializer=init_worker_env) as pool:
                chunk_results = pool.starmap(_process_layer_worker, args_list)
            
            layer_result = pd.concat(chunk_results, ignore_index=True)
            all_results.append(layer_result)
            
            # Free memory between layers
            del chunk_results
            gc.collect()
            
            print(f"   V Completed in {time.time()-layer_start:.2f}s")
        
        merged = grid_gdf[['cell_id', 'wkt']].copy()
        for result_df in all_results:
            merged = merged.merge(result_df, on='cell_id', how='left')
        
        return merged