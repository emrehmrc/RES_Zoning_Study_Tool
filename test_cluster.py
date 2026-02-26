import logging
from engines.cluster_engine import ClusterEngine

logging.basicConfig(level=logging.INFO)

try:
    print("Starting test...")
    gdf = ClusterEngine.run_clustering_pipeline(
        filepath="final_scored_analysis (5).csv",
        nominal_capacity_mw=13.0,
        max_capacity_mw=250.0,
        adjust_for_coverage=True
    )
    print(f"Generated {len(gdf)} clusters successfully.")
    print("Sample output:")
    if not gdf.empty:
        print(gdf[['final_cluster_id', 'Calculated_Capacity_MW', 'FINAL_GRID_SCORE']].head())
except Exception as e:
    print(f"Test failed: {e}")
