"""
Universal Raster Distance & Coverage Calculator - ENHANCED
Now supports: Distance, Coverage, Mean, Max, Min, and Categorical modes
"""
import os
import sys
import ctypes
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterstats import zonal_stats
import pandas as pd
from osgeo import gdal
from multiprocessing import Pool, cpu_count
import time


def get_short_path(long_path):
    """Converts a Windows path with special characters to a safe short path."""
    buf = ctypes.create_unicode_buffer(260)
    ctypes.windll.kernel32.GetShortPathNameW(long_path, buf, 260)
    return buf.value


def init_worker_env():
    """Initializes the GDAL/PROJ environment for each parallel worker."""
    from osgeo import gdal
    
    gdal.UseExceptions()
    venv_base = get_short_path(sys.prefix)
    proj_path = os.path.join(venv_base, 'Lib', 'site-packages', 'osgeo', 'data', 'proj')
    
    os.environ['PROJ_LIB'] = proj_path
    gdal.SetConfigOption('GTIFF_SRS_SOURCE', 'EPSG')
    gdal.UseExceptions()


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
            print(f"   📐 Non-square pixels: {pixel_width:.2f}m x {pixel_height:.2f}m (avg: {avg_pixel_size:.2f}m)")
        else:
            print(f"   📐 Square pixels: {avg_pixel_size:.2f}m x {avg_pixel_size:.2f}m")
        
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
        
        drv = gdal.GetDriverByName('MEM')
        global_src_ds = drv.Create('', target_w, target_h, 1, gdal.GDT_Byte)
        global_band = global_src_ds.GetRasterBand(1)
        
        zero_array = np.zeros((target_h, target_w), dtype=np.uint8)
        global_band.WriteArray(zero_array)
        
        win_gt = list(src_gt)
        win_gt[0] += win_xoff * src_gt[1]
        win_gt[3] += win_yoff * src_gt[5]
        global_src_ds.SetGeoTransform(win_gt)
        global_src_ds.SetProjection(src_ds.GetProjection())
        
        ixoff = max(0, win_xoff)
        iyoff = max(0, win_yoff)
        ixsize = min(win_xoff + target_w, max_width) - ixoff
        iysize = min(win_yoff + target_h, max_height) - iyoff
        
        if ixsize > 0 and iysize > 0:
            raster_data = src_band.ReadAsArray(ixoff, iyoff, ixsize, iysize)
            
            if src_nodata is not None:
                raster_data = np.where(raster_data == src_nodata, 0, raster_data)
            
            dest_xoff = ixoff - win_xoff
            dest_yoff = iyoff - win_yoff
            global_band.WriteArray(raster_data, dest_xoff, dest_yoff)
        
        prox_ds = drv.Create('', target_w, target_h, 1, gdal.GDT_Float32)
        prox_band = prox_ds.GetRasterBand(1)
        prox_ds.SetGeoTransform(win_gt)
        prox_ds.SetProjection(src_ds.GetProjection())
        prox_band.SetNoDataValue(-9999)
        
        max_distance_meters = max_distance_km * 1000
        max_distance_pixels = int(max_distance_meters / avg_pixel_size)
        
        print(f"   🎯 Max search distance: {max_distance_km} km = {max_distance_pixels} pixels")
        
        if is_square:
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
            proximity_meters = proximity_pixels * avg_pixel_size
            proximity_meters = np.where(proximity_pixels == -9999, -9999, proximity_meters)
            
        else:
            gdal.PushErrorHandler('CPLQuietErrorHandler')
            gdal.ComputeProximity(
                global_band, 
                prox_band, 
                [f'VALUES={target_value}',
                f'MAXDIST={max_distance_pixels}',
                'DISTUNITS=GEO',
                f'NODATA=-9999']
            )
            gdal.PopErrorHandler()
            
            proximity_meters = prox_band.ReadAsArray()
        
        proximity_meters = np.where(proximity_meters == -9999, 999999, proximity_meters)
        
        src_ds = global_src_ds = prox_ds = None
        
        return proximity_meters
    
    def calculate_layer(self, grid_gdf, raster_path, layer_prefix, analysis_modes=None, target_value=1):
        """
        Universal layer calculation supporting multiple analysis modes
        
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
        
        safe_nodata = 255
        
        with rasterio.open(raster_path) as src:
            raster_crs = src.crs
            grid_transformed = grid_gdf.to_crs(raster_crs)
            
            xmin, ymin, xmax, ymax = grid_transformed.total_bounds
            window = from_bounds(xmin, ymin, xmax, ymax, src.transform)
            
            raster_data = src.read(1, window=window).astype(np.float32)
            win_transform = src.window_transform(window)
        
        results = []
        
        # Process each analysis mode
        for mode in analysis_modes:
            print(f"   📊 Processing mode: {mode}")
            
            if mode == 'distance':
                # Distance calculation
                proximity_meters = self._compute_proximity_gdal(raster_path, target_value, window)
                dist_km_array = (proximity_meters / 1000.0).astype(np.float32)
                
                dist_stats = zonal_stats(grid_transformed, dist_km_array, affine=win_transform, 
                                        stats=['min'], nodata=safe_nodata, all_touched=True)
                
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
        Adaptive layer calculation with automatic strategy selection
        """
        if n_workers is None:
            n_workers = max(1, cpu_count() - 1)
        
        n_cells = len(grid_gdf)
        n_layers = len(layer_configs)
        
        total_start = time.time()
        
        print(f"{'='*60}")
        print(f"🎯 ADAPTIVE STRATEGY SELECTION")
        print(f"{'='*60}")
        print(f"Grid size: {n_cells:,} cells")
        print(f"Layers: {n_layers}")
        print(f"Available workers: {n_workers}")
        
        # Strategy selection
        if n_cells < 5000:
            print(f"📊 Strategy: LAYER PARALLELIZATION (small grid)")
            print(f"{'='*60}\n")
            result = self._parallel_by_layers(grid_gdf, layer_configs, n_workers)
        
        elif n_cells < 20000 and n_layers > 5:
            print(f"📊 Strategy: HYBRID (medium grid, many layers)")
            print(f"{'='*60}\n")
            result = self._process_grid_chunked(grid_gdf, layer_configs, chunk_size, n_workers)
        
        else:
            print(f"📊 Strategy: GRID-CHUNKED (large grid or single layer)")
            print(f"   Using {n_workers} parallel chunks")
            print(f"{'='*60}\n")
            result = self._process_grid_chunked(grid_gdf, layer_configs, chunk_size, n_workers)
        
        total_time = time.time() - total_start
        
        print(f"\n{'='*60}")
        print(f"✅ ADAPTIVE PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Avg per cell: {total_time/n_cells*1000:.2f}ms")
        print(f"Avg per layer: {total_time/n_layers:.2f}s")
        print(f"{'='*60}\n")
        
        return result
    
    def _parallel_by_layers(self, grid_gdf, layer_configs, n_workers):
        """Process all layers in parallel"""
        print(f"🚀 Processing all {len(layer_configs)} layers in parallel...")
        
        args_list = [
            (grid_gdf, layer['path'], layer['prefix'], 
             layer.get('analysis_modes', ['distance']), 
             layer.get('target_value', 1), layer.get('config', {}))
            for layer in layer_configs
        ]
        
        with Pool(processes=n_workers, initializer=init_worker_env) as pool:
            # Use the module-level function instead of class method
            results = pool.starmap(_process_layer_worker, args_list)
        
        merged = grid_gdf[['cell_id', 'wkt']].copy()
        for result in results:
            merged = merged.merge(result, on='cell_id', how='left')
        
        return merged
    
    def _process_grid_chunked(self, grid_gdf, layer_configs, chunk_size, n_workers):
        """Process large grids by chunking"""
        n_chunks = max(1, len(grid_gdf) // chunk_size)
        n_chunks = min(n_chunks, n_workers * 2)
        
        print(f"Splitting grid into {n_chunks} chunks...")
        grid_chunks = self._split_grid_spatially(grid_gdf, n_chunks)
        
        all_results = []
        
        for layer_idx, layer in enumerate(layer_configs):
            print(f"\n{'─'*60}")
            print(f"🔄 Layer {layer_idx+1}/{len(layer_configs)}: {layer['prefix']}")
            print(f"{'─'*60}")
            layer_start = time.time()
            
            args_list = [
                (chunk, layer['path'], layer['prefix'], 
                layer.get('analysis_modes', ['distance']),
                layer.get('target_value', 1), layer.get('config', {}))
                for chunk in grid_chunks
            ]
            
            with Pool(processes=n_workers, initializer=init_worker_env) as pool:
                # Use the module-level function instead of class method
                chunk_results = pool.starmap(_process_layer_worker, args_list)
            
            layer_result = pd.concat(chunk_results, ignore_index=True)
            all_results.append(layer_result)
            
            print(f"   ✅ Completed in {time.time()-layer_start:.2f}s")
        
        merged = grid_gdf[['cell_id', 'wkt']].copy()
        for result_df in all_results:
            merged = merged.merge(result_df, on='cell_id', how='left')
        
        return merged