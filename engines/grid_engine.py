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
    
    def create_rectangular_grid(self, dx, dy, progress_callback=None):
        """
        Generates a rectangular grid clipped to the boundary geometry.
        
        Parameters:
        -----------
        dx : float
            Grid cell width in meters
        dy : float
            Grid cell height in meters
        progress_callback : callable, optional
            Function(percent, message) to report progress
        
        Returns:
        --------
        pd.DataFrame
            Grid cells with geometry and metadata
        """
        start_time = time.time()
        
        def update(pct, text):
            if progress_callback:
                progress_callback(pct, text)
        
        # 1. Bounding Box Calculation
        update(0.1, "Calculating coordinate space...")
        xmin, ymin, xmax, ymax = self.boundary_gdf.total_bounds
        cols = np.arange(xmin, xmax, dx)
        rows = np.arange(ymin, ymax, dy)
        x_mesh, y_mesh = np.meshgrid(cols, rows)
        x_flat = x_mesh.ravel()
        y_flat = y_mesh.ravel()
        
        # 2. Vectorized Geometry Creation
        update(0.3, f"Generating {len(x_flat):,} raw grid cells...")
        polygons = shapely.box(x_flat, y_flat, x_flat + dx, y_flat + dy)
        
        # Create temporary GeoDataFrame for spatial filtering
        grid_gdf = gpd.GeoDataFrame({
            'left': x_flat,
            'bottom': y_flat,
            'right': x_flat + dx,
            'top': y_flat + dy,
            'geometry': polygons
        }, crs="EPSG:3857")
        
        # 3. Spatial Filtering (Using Centroids)
        update(0.5, "Filtering cells by center point...")
        # Create a single unified geometry for the check
        mask_geom = self.boundary_gdf.geometry.unary_union
        # Keep only cells whose center point is within the boundary
        is_inside = grid_gdf.geometry.centroid.within(mask_geom)
        grid_gdf = grid_gdf[is_inside].copy().reset_index(drop=True)
        grid_gdf['cell_id'] = grid_gdf.index
        
        # 4. Center Points and WKT
        update(0.7, "Calculating center points and WGS84 coordinates...")
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
        update(0.9, "Finalizing the table structure...")
        final_table = pd.DataFrame(grid_gdf.drop(columns='geometry'))
        
        cols_order = [
            'cell_id', 'left', 'top', 'right', 'bottom', 
            'wkt', 'Center_X', 'Center_Y', 
            'Center_X_4326', 'Center_Y_4326'
        ]
        
        end_time = time.time()
        update(1.0, f"✅ Complete! {len(final_table):,} cells in {end_time - start_time:.2f}s")
        
        return final_table[cols_order]