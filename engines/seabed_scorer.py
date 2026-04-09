"""
Seabed Vector Layer Scorer
Processes a shapefile whose polygons carry a 'Substrate' attribute.
For each grid cell the dominant substrate type (by intersection area) is found,
mapped to one of the standard categories, and stored in
  {prefix}_dominant   (string: 'sand' | 'gravel' | 'rack/bad rack/mud' | 'boulder/stony/silt')
"""
import os
import geopandas as gpd
import pandas as pd

# Mapping from EMODnet Substrate attribute values → internal category
SUBSTRATE_MAP = {
    'seabed':                     'sand',
    'sand':                       'sand',
    'coarse & mixed sediment':    'gravel',
    'coarse and mixed sediment':  'gravel',
    'fine mud':                   'rack/bad rack/mud',
    '[posidonia oceanica] meadows':'boulder/stony/silt',
    'posidonia oceanica meadows': 'boulder/stony/silt',
    'muddy sand':                 'rack/bad rack/mud',
    'rock or other hard substrata':'boulder/stony/silt',
    'sandy mud':                  'rack/bad rack/mud',
    'dead mattes of [posidonia oceanica]': 'boulder/stony/silt',
    'dead mattes of posidonia oceanica':   'boulder/stony/silt',
    # Long Ficopomatus entry — match by prefix
    'facies with [ficopomatus':   'boulder/stony/silt',
    'facies with ficopomatus':    'boulder/stony/silt',
}

# Canonical fallback if no mapping found
FALLBACK_CATEGORY = 'boulder/stony/silt'


def _map_substrate(raw: str) -> str:
    """Map a raw Substrate string to an internal category (case-insensitive)."""
    if not isinstance(raw, str):
        return FALLBACK_CATEGORY
    key = raw.strip().lower()
    if key in SUBSTRATE_MAP:
        return SUBSTRATE_MAP[key]
    # prefix match for long strings
    for k, v in SUBSTRATE_MAP.items():
        if key.startswith(k):
            return v
    return FALLBACK_CATEGORY


def calculate_seabed_layer(grid_gdf: gpd.GeoDataFrame,
                            shapefile_path: str,
                            layer_prefix: str,
                            substrate_column: str = 'Substrate') -> pd.DataFrame:
    """
    For each grid cell find the dominant seabed substrate by intersection area,
    map it to a standard category, and return a DataFrame with columns:
      cell_id, {prefix}_dominant

    Parameters
    ----------
    grid_gdf : GeoDataFrame  (EPSG:3857)
    shapefile_path : str
    layer_prefix : str  e.g. 'Sea bed (only for bottom fixed)'
    substrate_column : str  attribute name in the shapefile that holds the substrate type

    Returns
    -------
    pd.DataFrame with 'cell_id' and '{prefix}_dominant'
    """
    print(f"   [Seabed] Loading {shapefile_path}")
    norm_path = os.path.normpath(shapefile_path)
    if not os.path.isfile(norm_path):
        print(f"   [Seabed] ERROR: file not found: {norm_path}")
        result = grid_gdf[['cell_id']].copy()
        result[f'{layer_prefix}_dominant'] = FALLBACK_CATEGORY
        return result
    seabed_gdf = gpd.read_file(norm_path)

    # ── CRS alignment ──────────────────────────────────────────────────────────
    if seabed_gdf.crs is None:
        seabed_gdf = seabed_gdf.set_crs("EPSG:4326")
    if seabed_gdf.crs.to_epsg() != 3857:
        seabed_gdf = seabed_gdf.to_crs("EPSG:3857")

    # ── Find the substrate column (case-insensitive) ─────────────────────────
    col_map = {c.lower(): c for c in seabed_gdf.columns}
    actual_col = col_map.get(substrate_column.lower())
    if actual_col is None:
        # Try common alternatives
        for alt in ['substrate', 'Substrate', 'SUBSTRATE', 'hab_type', 'type', 'class']:
            if alt.lower() in col_map:
                actual_col = col_map[alt.lower()]
                break
    if actual_col is None:
        print(f"   [Seabed] WARNING: column '{substrate_column}' not found. Available: {list(seabed_gdf.columns)}")
        # Return all cells with fallback category
        result = grid_gdf[['cell_id']].copy()
        result[f'{layer_prefix}_dominant'] = FALLBACK_CATEGORY
        return result

    print(f"   [Seabed] Using substrate column: '{actual_col}'")
    print(f"   [Seabed] Intersecting {len(grid_gdf):,} cells with {len(seabed_gdf):,} seabed polygons...")

    # Keep only geometry + substrate column
    seabed_slim = seabed_gdf[[actual_col, 'geometry']].copy()
    seabed_slim = seabed_slim.rename(columns={actual_col: '_substrate'})

    # Spatial intersection
    grid_proj = grid_gdf[['cell_id', 'geometry']].copy()
    try:
        overlay = gpd.overlay(grid_proj, seabed_slim, how='intersection', keep_geom_type=False)
    except Exception as e:
        print(f"   [Seabed] overlay failed: {e}. Returning fallback.")
        result = grid_gdf[['cell_id']].copy()
        result[f'{layer_prefix}_dominant'] = FALLBACK_CATEGORY
        return result

    if overlay.empty:
        print("   [Seabed] No overlaps found. Returning fallback for all cells.")
        result = grid_gdf[['cell_id']].copy()
        result[f'{layer_prefix}_dominant'] = FALLBACK_CATEGORY
        return result

    # Compute intersection area
    overlay['_area'] = overlay.geometry.area

    # Map substrate to category
    overlay['_category'] = overlay['_substrate'].apply(_map_substrate)

    # For each cell, sum area per category → pick dominant
    area_by_cat = (
        overlay.groupby(['cell_id', '_category'])['_area']
        .sum()
        .reset_index()
    )
    dominant = (
        area_by_cat.sort_values('_area', ascending=False)
        .drop_duplicates(subset='cell_id')
        [['cell_id', '_category']]
        .rename(columns={'_category': f'{layer_prefix}_dominant'})
    )

    # Left-join back to all cells (cells without any overlap get fallback)
    result = grid_gdf[['cell_id']].merge(dominant, on='cell_id', how='left')
    result[f'{layer_prefix}_dominant'] = result[f'{layer_prefix}_dominant'].fillna(FALLBACK_CATEGORY)

    print(f"   [Seabed] Done. Category distribution:")
    print(result[f'{layer_prefix}_dominant'].value_counts().to_string())

    return result[['cell_id', f'{layer_prefix}_dominant']]
