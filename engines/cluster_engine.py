import geopandas as gpd
import pandas as pd
import numpy as np
import networkx as nx
from shapely import wkt
import time
import logging

class ClusterEngine:
    """
    Optimized highly-vectorized engine for clustering and aggregating spatial grid cells
    for Renewable Energy Zoning using GeoPandas and NetworkX.
    """

    @staticmethod
    def load_and_prepare_data(filepath_or_df, sep=';', decimal=','):
        """
        Reads the results CSV or takes a DataFrame directly and converts to a valid GeoDataFrame.
        Filters out cells with 0 score.
        """
        if isinstance(filepath_or_df, pd.DataFrame):
            logging.info("Loading data from provided DataFrame.")
            df = filepath_or_df.copy()
        else:
            logging.info(f"Loading data from {filepath_or_df}")
            
            # Read the file
            try:
                df = pd.read_csv(filepath_or_df, sep=sep, decimal=decimal)
            except Exception:
                # Fallback for standard CSV format
                df = pd.read_csv(filepath_or_df)

        if 'wkt' not in df.columns or 'FINAL_GRID_SCORE' not in df.columns:
            raise ValueError("Required columns 'wkt' and 'FINAL_GRID_SCORE' not found in the dataset.")

        # Filter out 0 scores or nulls
        df = df[df['FINAL_GRID_SCORE'].notna() & (df['FINAL_GRID_SCORE'] > 0)].copy()
        
        if df.empty:
            raise ValueError("No valid cells found with a positive FINAL_GRID_SCORE.")

        # Convert WKT to geometry
        df['geometry'] = df['wkt'].apply(wkt.loads)
        gdf = gpd.GeoDataFrame(df, geometry='geometry', crs='EPSG:3857')
        
        return gdf

    @staticmethod
    def calculate_cell_capacities(gdf, nominal_capacity_mw, adjust_for_coverage=True):
        """
        Calculates the actual capacity of each cell.
        If adjust_for_coverage is True, reduces capacity proportionally to combined layer coverage.
        """
        capacities = pd.Series(nominal_capacity_mw, index=gdf.index, dtype=float)
        
        if adjust_for_coverage:
            coverage_cols = [c for c in gdf.columns if c.endswith('_coverage_pct')]
            if coverage_cols:
                # Fill NAs with 0
                cov_df = gdf[coverage_cols].fillna(0)
                # We assume coverages could be strictly additive or overlapping. 
                # Being conservative, we sum them, capped at 100%.
                total_coverage = cov_df.sum(axis=1).clip(upper=100.0)
                free_pct = (100.0 - total_coverage) / 100.0
                capacities = capacities * free_pct

        gdf['Calculated_Capacity_MW'] = capacities
        return gdf

    @staticmethod
    def build_adjacency_components(gdf):
        """
        Finds adjacent polygons using spatial join and groups them into 
        connected components using NetworkX.
        Returns the GeoDataFrame with an initial 'component_id' column.
        """
        # Create a spatial index based adjacency list using sjoin predicate='touches' or 'intersects'
        # 'intersects' is sometimes safer against precision errors from WKT conversions
        logging.info("Building spatial adjacency graph...")
        
        # Reset index for clean joining
        gdf = gdf.reset_index(drop=True)
        gdf['original_index'] = gdf.index
        
        # Self-join to find intersecting/touching polygons
        # We use 'intersects' because adjacent grid cells share edges 
        # (and WKT round-trip might lose microscopic precision for 'touches')
        join_gdf = gpd.sjoin(gdf[['original_index', 'geometry']], 
                             gdf[['original_index', 'geometry']], 
                             how='inner', predicate='intersects')
        
        # Remove self-loops
        join_gdf = join_gdf[join_gdf['original_index_left'] != join_gdf['original_index_right']]
        
        # Build NetworkX Graph
        G = nx.Graph()
        G.add_nodes_from(gdf['original_index'])
        
        edges = list(zip(join_gdf['original_index_left'], join_gdf['original_index_right']))
        G.add_edges_from(edges)
        
        # Find connected components
        components = list(nx.connected_components(G))
        
        # Assign Component IDs to the GDF
        comp_map = {}
        for comp_id, nodes in enumerate(components):
            for node in nodes:
                comp_map[node] = comp_id
                
        gdf['component_id'] = gdf['original_index'].map(comp_map)
        
        return gdf, G, components

    @staticmethod
    def enforce_capacity_limits(gdf, G, components, max_capacity_mw):
        """
        Checks each component's total capacity. If it exceeds max_capacity,
        splits it using a localized graph balancing.
        """
        logging.info(f"Enforcing max capacity: {max_capacity_mw} MW")
        final_component_map = {}
        next_new_id = 0
        
        cap_dict = gdf.set_index('original_index')['Calculated_Capacity_MW'].to_dict()
        
        for comp in components:
            comp_nodes = list(comp)
            total_cap = sum(cap_dict[n] for n in comp_nodes)
            
            if total_cap <= max_capacity_mw:
                # Safe, assign all to next_new_id
                for n in comp_nodes:
                    final_component_map[n] = next_new_id
                next_new_id += 1
            else:
                # Needs splitting. Extract subgraph
                sub_g = G.subgraph(comp_nodes).copy()
                
                # Greedy BFS approach to split into chunks chunks <= max_capacity_mw
                unassigned = set(sub_g.nodes())
                
                while unassigned:
                    # Pick an arbitrary starting node
                    start_node = next(iter(unassigned))
                    current_chunk = set([start_node])
                    current_cap = cap_dict[start_node]
                    unassigned.remove(start_node)
                    
                    # We will grow this chunk layer by layer using BFS
                    queue = [start_node]
                    
                    while queue:
                        curr = queue.pop(0)
                        
                        # Find unassigned neighbors
                        neighbors = [n for n in sub_g.neighbors(curr) if n in unassigned]
                        
                        for neighbor in neighbors:
                            if current_cap + cap_dict[neighbor] <= max_capacity_mw:
                                current_chunk.add(neighbor)
                                current_cap += cap_dict[neighbor]
                                unassigned.remove(neighbor)
                                queue.append(neighbor)
                            else:
                                # We cannot add this neighbor without exceeding capacity.
                                # Since we want contiguous sub-blocks, we skip it for this chunk.
                                pass
                                
                    # Assign the built chunk to a new ID
                    for c_node in current_chunk:
                        final_component_map[c_node] = next_new_id
                    
                    next_new_id += 1
                    
        gdf['final_cluster_id'] = gdf['original_index'].map(final_component_map)
        return gdf

    @staticmethod
    def dissolve_and_aggregate(gdf):
        """
        Dissolves the cells into contiguous clusters and aggregates the metrics.
        """
        logging.info("Dissolving geometries and aggregating statistics...")
        
        # Define aggregation dictionary dynamically based on columns
        agg_dict = {
            'Calculated_Capacity_MW': 'sum',
            'FINAL_GRID_SCORE': 'mean'
        }
        
        if 'cell_id' in gdf.columns:
            agg_dict['cell_id'] = lambda x: ', '.join(str(i) for i in x.dropna())
        
        # Add min distances, max scores, mean coverages, etc.
        for col in gdf.columns:
            if col.endswith('_dist_km'):
                agg_dict[col] = 'min'
            elif col.endswith('_SCORE'):
                agg_dict[col] = 'mean'
            elif col.endswith('_coverage_pct'):
                agg_dict[col] = 'mean'
        
        # Ensure we only aggregate existing columns
        agg_dict = {k: v for k, v in agg_dict.items() if k in gdf.columns}
        
        # Dissolve using final_cluster_id
        cluster_gdf = gdf.dissolve(by='final_cluster_id', aggfunc=agg_dict)
        
        # Reset index to bring final_cluster_id back as a column
        cluster_gdf = cluster_gdf.reset_index()
        
        # Create new WKT strings
        cluster_gdf['wkt'] = cluster_gdf['geometry'].apply(lambda geom: geom.wkt)
        
        return cluster_gdf

    @classmethod
    def run_clustering_pipeline(cls, filepath_or_df, nominal_capacity_mw, max_capacity_mw, adjust_for_coverage=True):
        """
        Executes the entire end-to-end vectorized clustering pipeline.
        Returns the final clustered GeoDataFrame.
        """
        t0 = time.time()
        
        gdf = cls.load_and_prepare_data(filepath_or_df)
        t1 = time.time()
        
        gdf = cls.calculate_cell_capacities(gdf, nominal_capacity_mw, adjust_for_coverage)
        t2 = time.time()
        
        gdf, G, components = cls.build_adjacency_components(gdf)
        t3 = time.time()
        
        gdf = cls.enforce_capacity_limits(gdf, G, components, max_capacity_mw)
        t4 = time.time()
        
        final_gdf = cls.dissolve_and_aggregate(gdf)
        t5 = time.time()
        
        logging.info(f"Pipeline completed in {t5-t0:.2f}s! Stats:")
        logging.info(f"- Load & Prepare: {t1-t0:.2f}s")
        logging.info(f"- Capacity Calc: {t2-t1:.2f}s")
        logging.info(f"- Graph Build: {t3-t2:.2f}s")
        logging.info(f"- Split / Enforce: {t4-t3:.2f}s")
        logging.info(f"- Dissolve & Agg: {t5-t4:.2f}s")
        
        return final_gdf
