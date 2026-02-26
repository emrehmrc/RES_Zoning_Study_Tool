"""
Cluster Analysis Tab - Groups adjacent valid grid cells into clusters,
computes transmission connection scoring, and generates enriched output.

Integrates with ClusterEngine for spatial clustering and ClusterScorer
for post-clustering transmission/connection scoring (matching Excel reference).
"""
import streamlit as st
import pandas as pd
import numpy as np
import io
import copy
from ui.base_tab import BaseTab
from engines.cluster_engine import ClusterEngine
from engines.cluster_scorer import ClusterScorer
import tempfile
import os


class ClusterAnalysisTab(BaseTab):
    """
    Standalone tab for grouping adjacent valid grid cells into clusters
    while respecting a maximum capacity constraint, then enriching each
    cluster with transmission connection scoring columns.
    """

    def __init__(self, session_state, config):
        super().__init__(session_state)
        self.config = config

    def render(self):
        st.header("🧩 Step 4: Cluster & Aggregation")
        st.markdown("---")
        st.markdown(
            "Upload the **final scored CSV** (from Step 3). This engine will find all spatially adjacent "
            "valid cells and group them into contiguous clusters. If a cluster exceeds the maximum "
            "capacity threshold, it will be automatically sub-divided. After clustering, **connection scoring** "
            "is applied based on configurable rules for transmission infrastructure."
        )

        # ── Section 1: Input Data ─────────────────────────────────────
        with st.container(border=True):
            st.subheader("1. Input Data")
            uploaded_file = st.file_uploader(
                "Upload Scored Results CSV",
                type=['csv'],
                key="cluster_csv_upload"
            )

        if not uploaded_file:
            st.info("ℹ️ Please upload a scored CSV file to proceed.")
            return

        # ── Section 2: Capacity Constraints ───────────────────────────
        with st.container(border=True):
            st.subheader("2. Capacity Constraints & Logic")

            col1, col2 = st.columns(2)
            with col1:
                nominal_capacity_mw = st.number_input(
                    "Cell Nominal Capacity (MW):",
                    min_value=0.1, max_value=1000.0, value=13.0, step=0.1,
                    help="Default maximum capacity a single grid cell can produce (e.g., 13 MW for a standard cell)."
                )

            with col2:
                max_capacity_mw = st.number_input(
                    "Max Cluster Capacity Threshold (MW):",
                    min_value=10.0, max_value=10000.0, value=250.0, step=10.0,
                    help="If a cluster of adjacent cells exceeds this threshold, it will be split."
                )

            adjust_for_coverage = st.checkbox(
                "Adjust capacity based on existing layers (Covered Area Exclusion)",
                value=True,
                help="If checked, the cell capacity is reduced proportionally by the sum of `_coverage_pct` layers within the cell."
            )

        # ── Section 3: Connection Scoring Rules ───────────────────────
        with st.container(border=True):
            self._render_scoring_rules_section()

        # ── Action Button ──────────────────────────────────────────────
        run_clustering = st.button("🚀 Run Clustering & Scoring", type="primary", use_container_width=True)

        if run_clustering:
            self._execute_pipeline(
                uploaded_file, nominal_capacity_mw, max_capacity_mw, adjust_for_coverage
            )

        # ── Display Results ───────────────────────────────────────────
        self._render_results()

    # ─────────────────────────────────────────────────────────────────────
    # Scoring Rules UI
    # ─────────────────────────────────────────────────────────────────────

    def _render_scoring_rules_section(self):
        """Render the editable scoring rules table for the active mode."""
        project_type = st.session_state.get("project_type", "Solar")
        mode_label = "Solar (GES)" if project_type == "Solar" else f"Wind ({project_type})"

        st.subheader(f"3. Connection Scoring Rules — {mode_label}")
        st.markdown(
            "Configure distance-based scoring rules for transmission infrastructure. "
            "Each rule defines thresholds for 4 scoring levels (L1=best to L4=worst) "
            "based on the cluster's distance to a specific transmission asset and its capacity range."
        )

        # Initialize rules in session state from config defaults
        rules_key = "cluster_scoring_rules"
        if rules_key not in st.session_state:
            default_rules = getattr(self.config, 'CLUSTER_SCORING_RULES', [])
            st.session_state[rules_key] = copy.deepcopy(default_rules)

        rules = st.session_state[rules_key]

        if not rules:
            st.warning("⚠️ No scoring rules configured. Connection scoring will be skipped.")
            return

        # Convert to DataFrame for display / editing
        rules_df = pd.DataFrame(rules)

        # Column display order
        display_cols = [
            "criteria_norm", "kind", "kv", "weight_frac",
            "cap_min", "cap_max",
            "L1_min", "L1_max", "L1_score",
            "L2_min", "L2_max", "L2_score",
            "L3_min", "L3_max", "L3_score",
            "L4_min", "L4_max", "L4_score",
        ]
        # Only show columns that exist
        display_cols = [c for c in display_cols if c in rules_df.columns]

        # Column configuration for better labels
        column_config = {
            "criteria_norm": st.column_config.TextColumn("Criteria", width="medium"),
            "kind": st.column_config.SelectboxColumn("Type", options=["Line", "Substation"], width="small"),
            "kv": st.column_config.SelectboxColumn("kV", options=[110, 220, 400], width="small"),
            "weight_frac": st.column_config.NumberColumn("Weight", min_value=0.0, max_value=1.0, step=0.05, format="%.2f"),
            "cap_min": st.column_config.NumberColumn("Cap Min (MW)", min_value=0, step=5),
            "cap_max": st.column_config.NumberColumn("Cap Max (MW)", min_value=0, step=5),
            "L1_min": st.column_config.NumberColumn("L1 Min (km)", min_value=0.0, step=0.5, format="%.1f"),
            "L1_max": st.column_config.NumberColumn("L1 Max (km)", min_value=0.0, step=1.0, format="%.1f"),
            "L1_score": st.column_config.NumberColumn("L1 Score", min_value=0, max_value=100, step=5),
            "L2_min": st.column_config.NumberColumn("L2 Min", min_value=0.0, step=1.0, format="%.1f"),
            "L2_max": st.column_config.NumberColumn("L2 Max", min_value=0.0, step=1.0, format="%.1f"),
            "L2_score": st.column_config.NumberColumn("L2 Score", min_value=0, max_value=100, step=5),
            "L3_min": st.column_config.NumberColumn("L3 Min", min_value=0.0, step=1.0, format="%.1f"),
            "L3_max": st.column_config.NumberColumn("L3 Max", min_value=0.0, step=1.0, format="%.1f"),
            "L3_score": st.column_config.NumberColumn("L3 Score", min_value=0, max_value=100, step=5),
            "L4_min": st.column_config.NumberColumn("L4 Min", min_value=0.0, step=1.0, format="%.1f"),
            "L4_max": st.column_config.NumberColumn("L4 Max", min_value=0.0, step=5.0, format="%.0f"),
            "L4_score": st.column_config.NumberColumn("L4 Score", min_value=0, max_value=100, step=5),
        }

        with st.expander("📋 View / Edit Scoring Rules", expanded=False):
            edited_df = st.data_editor(
                rules_df[display_cols],
                column_config=column_config,
                num_rows="dynamic",
                use_container_width=True,
                key="rules_editor",
                hide_index=True
            )

            # Update session state with edits
            st.session_state[rules_key] = edited_df.to_dict('records')

            # Reset button
            col_r1, col_r2 = st.columns([3, 1])
            with col_r2:
                if st.button("🔄 Reset to Defaults", key="reset_rules_btn"):
                    default_rules = getattr(self.config, 'CLUSTER_SCORING_RULES', [])
                    st.session_state[rules_key] = copy.deepcopy(default_rules)
                    st.rerun()

        # Summary info
        st.caption(f"📊 {len(rules)} rules configured | Mode: {mode_label}")

    # ─────────────────────────────────────────────────────────────────────
    # Pipeline Execution
    # ─────────────────────────────────────────────────────────────────────

    def _execute_pipeline(self, uploaded_file, nominal_capacity_mw, max_capacity_mw, adjust_for_coverage):
        """Run the complete clustering + scoring pipeline."""
        project_type = st.session_state.get("project_type", "Solar")

        with st.spinner("Processing spatial topologies, clustering, and scoring... this may take a moment."):
            try:
                # Save uploaded file to temp
                with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp:
                    tmp.write(uploaded_file.getvalue())
                    temp_path = tmp.name

                try:
                    # ── Step A: Clustering ─────────────────────
                    # Load data for cell-level reference
                    cell_gdf = ClusterEngine.load_and_prepare_data(temp_path)
                    cell_gdf = ClusterEngine.calculate_cell_capacities(
                        cell_gdf, nominal_capacity_mw, adjust_for_coverage
                    )
                    cell_gdf, G, components = ClusterEngine.build_adjacency_components(cell_gdf)
                    cell_gdf = ClusterEngine.enforce_capacity_limits(
                        cell_gdf, G, components, max_capacity_mw
                    )
                    cluster_gdf = ClusterEngine.dissolve_and_aggregate(cell_gdf)

                    # ── Step B: Connection Scoring ─────────────
                    scoring_rules = st.session_state.get("cluster_scoring_rules", [])

                    if scoring_rules:
                        cluster_gdf = ClusterScorer.score_clusters(
                            cluster_gdf=cluster_gdf,
                            cell_gdf=cell_gdf,
                            scoring_rules=scoring_rules,
                            project_type=project_type
                        )

                finally:
                    os.unlink(temp_path)

                self.state.cluster_results = cluster_gdf
                st.success("✅ Clustering & scoring complete!")

            except Exception as e:
                st.error(f"❌ Pipeline failed: {e}")
                import traceback
                st.code(traceback.format_exc())

    # ─────────────────────────────────────────────────────────────────────
    # Results Display
    # ─────────────────────────────────────────────────────────────────────

    def _render_results(self):
        """Render the clustering + scoring results if available."""
        if not hasattr(self.state, 'cluster_results') or self.state.cluster_results is None:
            return

        results_gdf = self.state.cluster_results

        st.markdown("---")
        st.subheader("📊 Clustering & Scoring Summary")

        # ── Summary metrics ─────────────────────────────────────
        summary_cols = st.columns(4)
        with summary_cols[0]:
            st.metric("Total Clusters", f"{len(results_gdf):,}")
        with summary_cols[1]:
            cap_col = "Installed_Capacity_MW" if "Installed_Capacity_MW" in results_gdf.columns else "Calculated_Capacity_MW"
            if cap_col in results_gdf.columns:
                avg_cap = results_gdf[cap_col].mean()
                st.metric("Avg Capacity (MW)", f"{avg_cap:.2f}")
        with summary_cols[2]:
            if "Overall_Score" in results_gdf.columns:
                avg_score = results_gdf["Overall_Score"].mean()
                st.metric("Avg Overall Score", f"{avg_score:.2f}")
            elif "FINAL_GRID_SCORE" in results_gdf.columns:
                avg_score = results_gdf["FINAL_GRID_SCORE"].mean()
                st.metric("Avg Grid Score", f"{avg_score:.2f}")
        with summary_cols[3]:
            if "Within_Cells_Count" in results_gdf.columns:
                total_cells = results_gdf["Within_Cells_Count"].sum()
                st.metric("Total Cells in Clusters", f"{int(total_cells):,}")

        # ── Connection scoring breakdown ─────────────────────────
        if "Nearest_Connection_Type" in results_gdf.columns:
            with st.expander("🔌 Connection Scoring Breakdown", expanded=True):
                conn_col1, conn_col2 = st.columns(2)

                with conn_col1:
                    type_counts = results_gdf["Nearest_Connection_Type"].value_counts()
                    st.markdown("**Connection Types:**")
                    for conn_type, count in type_counts.items():
                        if conn_type:
                            st.write(f"• {conn_type}: {count} clusters")

                with conn_col2:
                    if "Nearest_Connection_kV" in results_gdf.columns:
                        kv_counts = results_gdf["Nearest_Connection_kV"].value_counts()
                        st.markdown("**Voltage Levels:**")
                        for kv, count in kv_counts.items():
                            if kv > 0:
                                st.write(f"• {kv} kV: {count} clusters")

                if "Nearest_Connection_Score" in results_gdf.columns:
                    avg_conn_score = results_gdf["Nearest_Connection_Score"].mean()
                    st.metric("Average Connection Score", f"{avg_conn_score:.1f}")

        # ── Results Preview ──────────────────────────────────────
        st.subheader("📋 Results Preview")

        # Build a smart column order for preview
        priority_cols = [
            'final_cluster_id', 'Within_Cells_Count',
            'Installed_Capacity_MW', 'Mean_Cell_OverallScore',
            'Nearest_Connection_Type', 'Nearest_Connection_kV',
            'Nearest_Connection_Distance_km', 'Nearest_Connection_Score',
            'Nearest_Weight_%', 'Overall_Score',
            'Mean_Transport_Total', 'Mean_Slope_mean',
        ]

        # Add mode-specific columns
        project_type = st.session_state.get("project_type", "Solar")
        if project_type == "Solar":
            priority_cols.extend(['Solar_irradiation_rate', 'Mean_Temperature_mean'])
        else:
            priority_cols.extend(['Connection_Grid', 'Mean_Altitude', 'Mean_Wind_mean'])

        # Add transmission distance columns
        priority_cols.extend([
            'Min_Dist_110kV_Line', 'Min_Dist_220kV_Line', 'Min_Dist_400kV_Line',
            'Min_Dist_110kV_Substation', 'Min_Dist_220kV_Substation', 'Min_Dist_400kV_Substation'
        ])

        # Filter to existing columns
        valid_cols = [c for c in priority_cols if c in results_gdf.columns]

        # Add remaining columns not in priority list (except geometry/wkt)
        remaining = [c for c in results_gdf.columns
                     if c not in valid_cols and c not in ('geometry', 'wkt', 'original_index')]
        valid_cols.extend(remaining)

        st.dataframe(results_gdf[valid_cols].head(30), use_container_width=True)

        # ── Download ────────────────────────────────────────────
        st.markdown("### 📥 Download Output")

        # Prepare CSV (exclude geometry column for clean export)
        export_cols = [c for c in results_gdf.columns if c != 'geometry']
        csv_data = results_gdf[export_cols].to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')

        st.download_button(
            label="Download Clustered & Scored Results (CSV)",
            data=csv_data,
            file_name="clustered_scored_results.csv",
            mime="text/csv",
            use_container_width=True
        )

    def validate(self):
        """Validates that scoring data or clustering data is available."""
        return True
