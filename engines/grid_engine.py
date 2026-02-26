"""
Grid generation engine
"""
import geopandas as gpd
import numpy as np
import shapely
import pandas as pd
import time
from pathlib import Path


class FastGridEngine:
    def __init__(self, boundary_gdf):
        """
        Initialize grid engine with boundary geometry
        
        Parameters:
        -----------
        boundary_gdf : GeoDataFrame
            Boundary geometry for grid clipping
        """
        # Ensure the boundary is in meters for accurate grid sizing
        self.boundary_gdf = boundary_gdf.to_crs("EPSG:3857")
    
    def create_rectangular_grid(self, dx, dy, progress_callback=None, chunk_rows=500):
        """
        Generates a rectangular grid clipped to the boundary geometry.
        Uses chunked processing to avoid Out-Of-Memory errors on large areas.
        
        Parameters:
        -----------
        dx : float
            Grid cell width in meters
        dy : float
            Grid cell height in meters
        progress_callback : callable, optional
            Function(percent, message) to report progress
        chunk_rows : int, optional
            Number of Y-axis rows to process per batch (default: 500)
        
        Returns:
        --------
        pd.DataFrame
            Grid cells with geometry and metadata
        """
        start_time = time.time()
        
        def update(pct, text):
            if progress_callback:
                progress_callback(pct, text)
        
        # 1. Bounding Box & Axis Vectors
        update(0.05, "Calculating coordinate space...")
        xmin, ymin, xmax, ymax = self.boundary_gdf.total_bounds
        cols = np.arange(xmin, xmax, dx)
        rows = np.arange(ymin, ymax, dy)
        
        total_rows = len(rows)
        total_cols = len(cols)
        estimated_cells = total_rows * total_cols
        update(0.08, f"Grid space: {total_cols} cols × {total_rows} rows = {estimated_cells:,} candidate cells")
        
        # Prepare boundary mask once
        mask_geom = self.boundary_gdf.geometry.unary_union
        
        # 2. Chunked Processing – process `chunk_rows` Y-values at a time
        chunk_results = []
        num_chunks = max(1, int(np.ceil(total_rows / chunk_rows)))
        
        for chunk_idx in range(num_chunks):
            row_start = chunk_idx * chunk_rows
            row_end = min(row_start + chunk_rows, total_rows)
            rows_batch = rows[row_start:row_end]
            
            # Progress: map chunk index to the 0.10 → 0.70 range
            pct = 0.10 + (chunk_idx / num_chunks) * 0.60
            update(pct, f"Processing batch {chunk_idx + 1}/{num_chunks} "
                        f"(rows {row_start + 1}–{row_end} of {total_rows})...")
            
            # Meshgrid for this chunk only
            x_mesh, y_mesh = np.meshgrid(cols, rows_batch)
            x_flat = x_mesh.ravel()
            y_flat = y_mesh.ravel()
            
            # Vectorized geometry creation
            polygons = shapely.box(x_flat, y_flat, x_flat + dx, y_flat + dy)
            
            chunk_gdf = gpd.GeoDataFrame({
                'left': x_flat,
                'bottom': y_flat,
                'right': x_flat + dx,
                'top': y_flat + dy,
                'geometry': polygons
            }, crs="EPSG:3857")
            
            # Spatial filtering – keep cells whose centroid is within boundary
            is_inside = chunk_gdf.geometry.centroid.within(mask_geom)
            valid = chunk_gdf[is_inside]
            
            if len(valid) > 0:
                chunk_results.append(valid)
            
            # Free memory for the batch
            del x_mesh, y_mesh, x_flat, y_flat, polygons, chunk_gdf, is_inside
        
        # 3. Concatenate All Chunks
        update(0.72, "Merging filtered chunks...")
        if not chunk_results:
            raise ValueError("No grid cells fall within the provided boundary.")
        
        grid_gdf = pd.concat(chunk_results, ignore_index=True)
        grid_gdf = gpd.GeoDataFrame(grid_gdf, geometry='geometry', crs="EPSG:3857")
        grid_gdf['cell_id'] = grid_gdf.index
        
        # 4. Center Points and WKT
        update(0.78, "Calculating center points and WGS84 coordinates...")
        grid_gdf['Center_X'] = grid_gdf['left'] + (dx / 2)
        grid_gdf['Center_Y'] = grid_gdf['bottom'] + (dy / 2)
        grid_gdf['wkt'] = grid_gdf.geometry.to_wkt()
        
        # 5. WGS84 Conversion (Vectorized)
        temp_points = gpd.GeoSeries(
            gpd.points_from_xy(grid_gdf['Center_X'], grid_gdf['Center_Y']), 
            crs="EPSG:3857"
        ).to_crs("EPSG:4326")
        
        grid_gdf['Center_X_4326'] = temp_points.x 
        grid_gdf['Center_Y_4326'] = temp_points.y 
        
        # 6. Finalization
        update(0.92, "Finalizing the table structure...")
        final_table = pd.DataFrame(grid_gdf.drop(columns='geometry'))
        
        cols_order = [
            'cell_id', 'left', 'top', 'right', 'bottom', 
            'wkt', 'Center_X', 'Center_Y', 
            'Center_X_4326', 'Center_Y_4326'
        ]
        
        end_time = time.time()
        update(1.0, f"✅ Complete! {len(final_table):,} cells in {end_time - start_time:.2f}s")
        
        return final_table[cols_order]