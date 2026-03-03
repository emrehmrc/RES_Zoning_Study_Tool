"""
Cluster Scorer Engine
Post-processes clustered GeoDataFrame to add transmission/connection scoring columns.
Matches the logic from the Excel reference file (GES/RES sheets).

Columns added:
  - Installed_Capacity_MW (alias for Calculated_Capacity_MW)
  - Mean_Cell_OverallScore (mean of FINAL_GRID_SCORE)
  - Mean_Transport_Total, Mean_Slope_mean
  - Solar-specific: Solar_irradiation_rate, Mean_Temperature_mean
  - Wind-specific: Connection_Grid, Mean_Altitude, Mean_Wind_mean
  - Min_Dist_110kV_Line, Min_Dist_220kV_Line, Min_Dist_400kV_Line
  - Min_Dist_110kV_Substation, Min_Dist_220kV_Substation, Min_Dist_400kV_Substation
  - Nearest_Connection_Type, Nearest_Connection_kV
  - Nearest_Connection_Distance_km, Nearest_Connection_SourceColumn
  - Nearest_Connection_Score, Nearest_Weight_%, Overall_Score
"""
import pandas as pd
import numpy as np
import logging
from engines.financial_scorer import FinancialScorer


# ─────────────────────────────────────────────────────────────────────
# Column pattern matching helpers
# ─────────────────────────────────────────────────────────────────────

# Maps a canonical short-name to a list of substrings that should ALL
# appear (case-insensitive) in a column name for it to match.
_COLUMN_PATTERNS = {
    "dist_110kv_line":       [["110", "line", "dist"]],
    "dist_220kv_line":       [["220", "line", "dist"]],
    "dist_400kv_line":       [["400", "line", "dist"]],
    "dist_110kv_substation": [["110", "substation", "dist"], ["110", "sub", "dist"]],
    "dist_220kv_substation": [["220", "substation", "dist"], ["220", "sub", "dist"]],
    "dist_400kv_substation": [["400", "substation", "dist"], ["400", "sub", "dist"]],
    "transport":             [["transport", "dist"], ["transport_total"]],
    "slope_mean":            [["slope", "mean"]],
    "solar_mean":            [["solar", "mean"], ["solar_irr", "mean"]],
    "temperature_mean":      [["temperature", "mean"], ["temp", "mean"]],
    "altitude":              [["altitude"], ["alt_max"]],
    "wind_mean":             [["wind", "mean"]],
}


def _find_column(columns, canonical_name):
    """
    Find a column in `columns` that matches the canonical_name patterns.
    Returns the actual column name or None.
    """
    patterns = _COLUMN_PATTERNS.get(canonical_name, [])
    cols_lower = {c: c.lower().replace(" ", "_") for c in columns}

    for pattern_set in patterns:
        for col, col_lower in cols_lower.items():
            if all(sub in col_lower for sub in pattern_set):
                return col
    return None


def _find_all_columns(columns):
    """
    Build a mapping: canonical_name -> actual_column_name for all detectable columns.
    """
    mapping = {}
    for canonical in _COLUMN_PATTERNS:
        found = _find_column(columns, canonical)
        if found:
            mapping[canonical] = found
    return mapping


# ─────────────────────────────────────────────────────────────────────
# Scoring rule application
# ─────────────────────────────────────────────────────────────────────

def _score_distance(distance_km, capacity_mw, rule):
    """
    Apply a single scoring rule to a (distance, capacity) pair.
    Returns the score (int) or None if the capacity is out of range for this rule.
    """
    cap_min = rule.get("cap_min", 0)
    cap_max = rule.get("cap_max", 999999)

    if not (cap_min <= capacity_mw <= cap_max):
        return None

    # Check levels L1 -> L4 (best to worst)
    for lvl in ["L1", "L2", "L3", "L4"]:
        lmin = rule.get(f"{lvl}_min", 0)
        lmax = rule.get(f"{lvl}_max", 999999)
        lscore = rule.get(f"{lvl}_score", 0)
        if lmin <= distance_km <= lmax:
            return lscore

    # Outside all level ranges — return lowest score
    return rule.get("L4_score", 0)


# ─────────────────────────────────────────────────────────────────────
# Cluster Scorer
# ─────────────────────────────────────────────────────────────────────

class ClusterScorer:
    """
    Post-processes the clustered GeoDataFrame produced by ClusterEngine.
    Adds transmission scoring columns, connection determination, and Overall_Score.
    """

    # Mapping from canonical distance names to (kind, kv) for the rules
    _ASSET_MAP = {
        "dist_110kv_line":       ("Line", 110),
        "dist_220kv_line":       ("Line", 220),
        "dist_400kv_line":       ("Line", 400),
        "dist_110kv_substation": ("Substation", 110),
        "dist_220kv_substation": ("Substation", 220),
        "dist_400kv_substation": ("Substation", 400),
    }

    # Pretty display names for the source column
    _DISPLAY_NAMES = {
        "dist_110kv_line":       "Distance to 110kV Line",
        "dist_220kv_line":       "Distance to 220kV Line",
        "dist_400kv_line":       "Distance to 400kV Line",
        "dist_110kv_substation": "Distance to 110kV Substation",
        "dist_220kv_substation": "Distance to 220kV Substation",
        "dist_400kv_substation": "Distance to 400kV Substation",
    }

    # Output column names for the min-distance columns
    _OUTPUT_DIST_COLS = {
        "dist_110kv_line":       "Min_Dist_110kV_Line",
        "dist_220kv_line":       "Min_Dist_220kV_Line",
        "dist_400kv_line":       "Min_Dist_400kV_Line",
        "dist_110kv_substation": "Min_Dist_110kV_Substation",
        "dist_220kv_substation": "Min_Dist_220kV_Substation",
        "dist_400kv_substation": "Min_Dist_400kV_Substation",
    }

    @classmethod
    def score_clusters(cls, cluster_gdf, cell_gdf, scoring_rules, financial_constants=None, cp_values=None, project_type="Solar"):
        """
        Main entry point. Enriches the cluster-level GeoDataFrame with
        transmission scoring columns, and then calculates financial metrics.

        Parameters
        ----------
        cluster_gdf : GeoDataFrame
            Output of ClusterEngine (one row per cluster).
            Must have: final_cluster_id, Calculated_Capacity_MW, FINAL_GRID_SCORE.
        cell_gdf : GeoDataFrame
            The per-cell data (before dissolve) with final_cluster_id assigned.
            Used for aggregating additional columns.
        scoring_rules : list[dict]
            List of scoring rule dicts (from the UI / config).
        financial_constants : dict, optional
            Dictionary of financial rates. If None, defaults will be used inside FinancialScorer.
        cp_values : list[dict], optional
            List of CP lookup values for Wind mode.
        project_type : str
            "Solar", "OnShore", or "OffShore".

        Returns
        -------
        GeoDataFrame with all new columns added.
        """
        logging.info(f"ClusterScorer: scoring {len(cluster_gdf)} clusters for {project_type}")

        df = cluster_gdf.copy()
        col_map = _find_all_columns(cell_gdf.columns)

        # ── 1. Basic aliases ──────────────────────────────────────────
        df["Installed_Capacity_MW"] = df["Calculated_Capacity_MW"]
        df["Mean_Cell_OverallScore"] = df["FINAL_GRID_SCORE"]

        # ── 2. Aggregate additional cell-level columns per cluster ────
        agg_specs = cls._build_aggregation_specs(col_map, project_type)
        if agg_specs:
            # Filter to only columns that exist in cell_gdf
            valid_specs = {k: v for k, v in agg_specs.items() if k in cell_gdf.columns}
            if valid_specs:
                extra_agg = cell_gdf.groupby("final_cluster_id").agg(valid_specs)
                # Rename columns to output names
                rename_map = cls._build_rename_map(col_map, project_type)
                extra_agg = extra_agg.rename(columns=rename_map)
                # Merge into cluster df
                df = df.merge(extra_agg, left_on="final_cluster_id",
                              right_index=True, how="left")

        # ── 3. Connection Grid (Wind only) ──────────────────────────
        if project_type in ("OnShore", "OffShore"):
            df["Connection_Grid"] = df["Installed_Capacity_MW"].apply(
                lambda cap: "Distribution" if cap < 30 else "Transmission"
            )

        # ── 4. Within_Cells_Count ──────────────────────────────────
        cell_counts = cell_gdf.groupby("final_cluster_id").size().rename("Within_Cells_Count")
        df = df.merge(cell_counts, left_on="final_cluster_id", right_index=True, how="left")

        # ── 5. Connection scoring per cluster ─────────────────────
        conn_results = cls._compute_connection_scores(df, scoring_rules, col_map)
        for col_name, series in conn_results.items():
            df[col_name] = series

        # ── 6. Overall Score ──────────────────────────────────────
        df["Overall_Score"] = df["Mean_Cell_OverallScore"] + df["Nearest_Weight_%"]

        # ── 7. Financial & Energy Metrics ─────────────────────────
        # Use defaults if config wasn't passed down
        if financial_constants is None:
            financial_constants = {
                "pv_capex_per_mw": 500000, "wind_capex_per_mw": 1000000,
                "substation_pv_ratio": 0.08, "substation_wind_ratio": 0.06,
                "line_expropriation_ratio": 0.1, "land_cost_ratio": 0.1,
                "transport_network_base": 400000, "transport_network_per_mw": 500,
                "transmission": [
                    {"type": "Line", "kv": 110, "capacity_min": 0, "capacity_max": 30, "cost_per_km": 170000, "fixed_cost": 0},
                    {"type": "Line", "kv": 110, "capacity_min": 30, "capacity_max": 70, "cost_per_km": 170000, "fixed_cost": 0},
                    {"type": "Line", "kv": 220, "capacity_min": 70, "capacity_max": 180, "cost_per_km": 280000, "fixed_cost": 0},
                    {"type": "Line", "kv": 400, "capacity_min": 180, "capacity_max": 400, "cost_per_km": 400000, "fixed_cost": 0},
                    {"type": "Substation", "kv": 110, "capacity_min": 0, "capacity_max": 30, "cost_per_km": 170000, "fixed_cost": 500000},
                    {"type": "Substation", "kv": 110, "capacity_min": 30, "capacity_max": 70, "cost_per_km": 170000, "fixed_cost": 1000000},
                    {"type": "Substation", "kv": 220, "capacity_min": 70, "capacity_max": 180, "cost_per_km": 280000, "fixed_cost": 3000000},
                    {"type": "Substation", "kv": 400, "capacity_min": 180, "capacity_max": 400, "cost_per_km": 400000, "fixed_cost": 8000000}
                ]
            }

        df = FinancialScorer.calculate_financials(df, financial_constants, cp_values, project_type)

        logging.info(f"ClusterScorer: finished. Output has {len(df.columns)} columns.")
        return df

    @classmethod
    def _build_aggregation_specs(cls, col_map, project_type):
        """
        Build {source_column: agg_func} for extra columns to aggregate from cell data.
        """
        specs = {}

        # Transport — mean
        if "transport" in col_map:
            specs[col_map["transport"]] = "mean"

        # Slope mean — mean
        if "slope_mean" in col_map:
            specs[col_map["slope_mean"]] = "mean"

        # 6 transmission distance columns — min
        for canon in cls._ASSET_MAP:
            if canon in col_map:
                specs[col_map[canon]] = "min"

        # Mode-specific
        if project_type == "Solar":
            if "solar_mean" in col_map:
                specs[col_map["solar_mean"]] = "mean"
            if "temperature_mean" in col_map:
                specs[col_map["temperature_mean"]] = "mean"
        else:
            # Wind modes
            if "altitude" in col_map:
                specs[col_map["altitude"]] = "mean"
            if "wind_mean" in col_map:
                specs[col_map["wind_mean"]] = "mean"

        return specs

    @classmethod
    def _build_rename_map(cls, col_map, project_type):
        """
        Build {source_column_name: output_column_name} rename mapping.
        """
        rename = {}

        if "transport" in col_map:
            rename[col_map["transport"]] = "Mean_Transport_Total"
        if "slope_mean" in col_map:
            rename[col_map["slope_mean"]] = "Mean_Slope_mean"

        # Transmission distances
        for canon, out_name in cls._OUTPUT_DIST_COLS.items():
            if canon in col_map:
                rename[col_map[canon]] = out_name

        # Mode-specific
        if project_type == "Solar":
            if "solar_mean" in col_map:
                rename[col_map["solar_mean"]] = "Solar_irradiation_rate"
            if "temperature_mean" in col_map:
                rename[col_map["temperature_mean"]] = "Mean_Temperature_mean"
        else:
            if "altitude" in col_map:
                rename[col_map["altitude"]] = "Mean_Altitude"
            if "wind_mean" in col_map:
                rename[col_map["wind_mean"]] = "Mean_Wind_mean"

        return rename

    @classmethod
    def _compute_connection_scores(cls, cluster_df, scoring_rules, col_map):
        """
        For each cluster, evaluate all eligible transmission assets against
        the scoring rules. Pick the best scoring connection (highest score,
        then shortest distance as tiebreaker).

        Returns dict of Series keyed by output column name.
        """
        n = len(cluster_df)
        nearest_type = pd.Series([""] * n, index=cluster_df.index)
        nearest_kv = pd.Series([0] * n, index=cluster_df.index, dtype=int)
        nearest_dist = pd.Series([np.nan] * n, index=cluster_df.index)
        nearest_source = pd.Series([""] * n, index=cluster_df.index)
        nearest_score = pd.Series([0] * n, index=cluster_df.index, dtype=int)
        nearest_weight = pd.Series([0.0] * n, index=cluster_df.index)

        for idx in cluster_df.index:
            row = cluster_df.loc[idx]
            capacity = row.get("Installed_Capacity_MW", 0)

            best_score = -1
            best_dist = float("inf")
            best_kind = ""
            best_kv = 0
            best_source = ""
            best_weight = 0.0

            for canon, (kind, kv) in cls._ASSET_MAP.items():
                out_col = cls._OUTPUT_DIST_COLS[canon]
                if out_col not in cluster_df.columns:
                    continue

                dist_val = row.get(out_col, np.nan)
                if pd.isna(dist_val):
                    continue

                # Find matching rules for this asset type
                matching_rules = [
                    r for r in scoring_rules
                    if r.get("kind", "").lower() == kind.lower()
                    and r.get("kv", 0) == kv
                ]

                for rule in matching_rules:
                    score = _score_distance(dist_val, capacity, rule)
                    if score is None:
                        continue

                    # Better score wins; on tie, shorter distance wins
                    if (score > best_score) or (score == best_score and dist_val < best_dist):
                        best_score = score
                        best_dist = dist_val
                        best_kind = kind
                        best_kv = kv
                        best_source = cls._DISPLAY_NAMES.get(canon, canon)
                        best_weight = rule.get("weight_frac", 0.2) * 100  # as percentage

            if best_score >= 0:
                nearest_type.at[idx] = best_kind
                nearest_kv.at[idx] = best_kv
                nearest_dist.at[idx] = best_dist
                nearest_source.at[idx] = best_source
                nearest_score.at[idx] = best_score
                nearest_weight.at[idx] = best_weight

        return {
            "Nearest_Connection_Type": nearest_type,
            "Nearest_Connection_kV": nearest_kv,
            "Nearest_Connection_Distance_km": nearest_dist,
            "Nearest_Connection_SourceColumn": nearest_source,
            "Nearest_Connection_Score": nearest_score,
            "Nearest_Weight_%": nearest_weight,
        }
