"""
Grid generation engine
"""
import geopandas as gpd
import numpy as np
import shapely
import pandas as pd
import time
from pathlib import Path
from pyproj import Transformer


class FastGridEngine:
    def __init__(self, boundary_gdf):
        """
        Initialize grid engine with boundary geometry
        
        Parameters:
        -----------
        boundary_gdf : GeoDataFrame
            Boundary geometry for grid clipping
        """
        # Work in EPSG:3857 (Web Mercator, metres)
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
        
        # 1. Bounding Box & Axis Vectors (EPSG:3857 — already in metres)
        update(0.05, "Calculating coordinate space...")
        xmin, ymin, xmax, ymax = self.boundary_gdf.total_bounds

        cols = np.arange(xmin, xmax, dx)
        rows = np.arange(ymin, ymax, dy)
        
        total_rows = len(rows)
        total_cols = len(cols)
        estimated_cells = total_rows * total_cols
        update(0.08, f"Grid space: {total_cols} cols × {total_rows} rows = {estimated_cells:,} candidate cells ({dx}m × {dy}m)")
        
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
            
            # --- Intersection clipping (like QGIS Intersection) ---
            # 1) Keep only cells that intersect the boundary
            is_intersecting = chunk_gdf.geometry.intersects(mask_geom)
            candidates = chunk_gdf[is_intersecting].copy()
            
            if len(candidates) > 0:
                # 2) Cells fully within boundary → keep as-is (fast path)
                is_within = candidates.geometry.within(mask_geom)
                full_cells = candidates[is_within].copy()
                
                # 3) Cells partially overlapping → clip to boundary
                edge_cells = candidates[~is_within].copy()
                
                if len(edge_cells) > 0:
                    clipped_geoms = edge_cells.geometry.intersection(mask_geom)
                    # Drop empty results and keep only Polygon/MultiPolygon
                    valid_mask = (~clipped_geoms.is_empty) & clipped_geoms.geom_type.isin(['Polygon', 'MultiPolygon'])
                    edge_cells = edge_cells[valid_mask].copy()
                    edge_cells['geometry'] = clipped_geoms[valid_mask]
                    # Update bounding columns from clipped geometry
                    clipped_bounds = edge_cells.geometry.bounds  # minx, miny, maxx, maxy
                    edge_cells['left'] = clipped_bounds['minx'].values
                    edge_cells['bottom'] = clipped_bounds['miny'].values
                    edge_cells['right'] = clipped_bounds['maxx'].values
                    edge_cells['top'] = clipped_bounds['maxy'].values
                
                valid = pd.concat([full_cells, edge_cells], ignore_index=True) if len(edge_cells) > 0 else full_cells
            else:
                valid = candidates
            
            if len(valid) > 0:
                chunk_results.append(valid)
            
            # Free memory for the batch
            del x_mesh, y_mesh, x_flat, y_flat, polygons, chunk_gdf
        
        # 3. Concatenate All Chunks
        update(0.72, "Merging filtered chunks...")
        if not chunk_results:
            raise ValueError("No grid cells fall within the provided boundary.")
        
        grid_gdf = pd.concat(chunk_results, ignore_index=True)
        grid_gdf = gpd.GeoDataFrame(grid_gdf, geometry='geometry', crs="EPSG:3857")
        grid_gdf['cell_id'] = grid_gdf.index
        
        # 4. Center Points and WKT
        update(0.78, "Calculating center points...")
        # Use actual geometry centroid (correct for both full and clipped cells)
        centroids = grid_gdf.geometry.centroid
        grid_gdf['Center_X'] = centroids.x
        grid_gdf['Center_Y'] = centroids.y
        grid_gdf['wkt'] = grid_gdf.geometry.to_wkt()
        
        # Convert EPSG:3857 centres → EPSG:4326 for Leaflet display
        _t = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
        lons, lats = _t.transform(grid_gdf['Center_X'].values, grid_gdf['Center_Y'].values)
        grid_gdf['Center_X_4326'] = lons
        grid_gdf['Center_Y_4326'] = lats
        
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