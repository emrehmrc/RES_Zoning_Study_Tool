"""
Level Scoring Tab - Performs multi-criteria weighted scoring with Hard Exclusion Constraints.
Enhanced to handle multi-mode analysis layers intelligently.
"""
import streamlit as st
import pandas as pd
import numpy as np
from ui.base_tab import BaseTab

class LevelScoringTab(BaseTab):
    """
    Handles weighted scoring and hard exclusion constraints with smart mode selection.
    """
    
    # Default scoring configurations for common layer types
    DEFAULT_SCORING_CONFIGS = {
        'distance': {
            'levels': [
                {'max': 99999, 'min': 10, 'score': 100},
                {'max': 10, 'min': 5, 'score': 70},
                {'max': 5, 'min': 2, 'score': 40},
                {'max': 2, 'min': 0, 'score': 10}
            ]
        },
        'coverage': {
            'levels': [
                {'max': 100, 'min': 80, 'score': 10},
                {'max': 80, 'min': 50, 'score': 40},
                {'max': 50, 'min': 20, 'score': 70},
                {'max': 20, 'min': 0, 'score': 100}
            ]
        },
        'slope': {
            'levels': [
                {'max': 5, 'min': 0, 'score': 100},
                {'max': 10, 'min': 5, 'score': 70},
                {'max': 20, 'min': 10, 'score': 40},
                {'max': 99999, 'min': 20, 'score': 10}
            ]
        },
        'solar': {
            'levels': [
                {'max': 99999, 'min': 1800, 'score': 100},
                {'max': 1800, 'min': 1600, 'score': 70},
                {'max': 1600, 'min': 1400, 'score': 40},
                {'max': 1400, 'min': 0, 'score': 10}
            ]
        },
        'default': {
            'levels': [
                {'max': 99999, 'min': 75, 'score': 100},
                {'max': 75, 'min': 50, 'score': 70},
                {'max': 50, 'min': 25, 'score': 40},
                {'max': 25, 'min': 0, 'score': 10}
            ]
        }
    }

    def render(self):
        st.header("📈 Step 3: Level-Based Scoring & Constraints")
        st.markdown("---")

        # Data Source Selection
        source_option = st.radio(
            "Select Data Source for Scoring:",
            ["Use Results from Step 2", "Import Analysis CSV"],
            horizontal=True,
            key="scoring_source_selection"
        )

        if source_option == "Import Analysis CSV":
            self._render_csv_import()

        if not self.state.get('scoring_complete') or self.state.get('scoring_results') is None:
            st.warning("⚠️ No analysis data found. Please complete Step 2 or import a CSV.")
            return

        df = self.state.scoring_results
        metadata_cols = ['cell_id', 'wkt', 'geometry', 'Center_X', 'Center_Y', 'Center_X_4326', 'Center_Y_4326']
        analysis_cols = [col for col in df.columns if col not in metadata_cols]

        if not analysis_cols:
            st.error("❌ No processable analysis metrics found.")
            return

        st.success(f"✅ Data Ready: {len(df):,} cells available.")

        # Group columns by layer
        layer_groups = self._group_columns_by_layer(analysis_cols)
        
        st.subheader("⚙️ Scoring & Exclusion Configuration")
        st.info(f"📊 Found {len(layer_groups)} unique layers with analysis results")

        scoring_config = {}
        constraint_config = {}

        with st.form("scoring_and_constraints_form"):
            for layer_name, columns_info in layer_groups.items():
                self._render_layer_configuration(
                    layer_name, 
                    columns_info, 
                    scoring_config, 
                    constraint_config
                )

            st.markdown("---")
            run_calc = st.form_submit_button(
                "🚀 Run Comprehensive Scoring", 
                type="primary", 
                use_container_width=True
            )

        if run_calc:
            self._run_calculation(df, scoring_config, constraint_config)

    def _group_columns_by_layer(self, analysis_cols):
        """
        Groups analysis columns by their base layer name.
        Returns: {layer_name: {'modes': {...}, 'columns': [...]}}
        """
        layer_groups = {}
        
        for col in analysis_cols:
            # Extract layer name and mode
            if '_dist_km' in col:
                layer_name = col.replace('_dist_km', '')
                mode = 'distance'
            elif '_coverage_pct' in col:
                layer_name = col.replace('_coverage_pct', '')
                mode = 'coverage'
            elif '_mean' in col:
                layer_name = col.replace('_mean', '')
                mode = 'mean'
            elif '_max' in col:
                layer_name = col.replace('_max', '')
                mode = 'max'
            elif '_min' in col:
                layer_name = col.replace('_min', '')
                mode = 'min'
            elif '_median' in col:
                layer_name = col.replace('_median', '')
                mode = 'median'
            elif '_std' in col:
                layer_name = col.replace('_std', '')
                mode = 'std'
            elif '_categories' in col:
                layer_name = col.replace('_categories', '')
                mode = 'categorical'
            else:
                # Unknown format, treat as standalone
                layer_name = col
                mode = 'unknown'
            
            if layer_name not in layer_groups:
                layer_groups[layer_name] = {
                    'modes': {},
                    'columns': []
                }
            
            layer_groups[layer_name]['modes'][mode] = col
            layer_groups[layer_name]['columns'].append(col)
        
        return layer_groups

    def _render_layer_configuration(self, layer_name, columns_info, scoring_config, constraint_config):
        """
        Renders configuration UI for a single layer with intelligent mode handling.
        """
        modes = columns_info['modes']
        columns = columns_info['columns']
        
        with st.expander(f"📊 Layer: {layer_name}", expanded=True):
            st.markdown(f"**Available modes:** {', '.join(modes.keys())}")
            
            # Step 1: Choose between Scoring or Exclusion
            logic_type = st.radio(
                "Logic Type:",
                ["Weighted Scoring", "Exclusion Constraint (Max Threshold)"],
                index=0,
                horizontal=True,
                key=f"logic_{layer_name}"
            )
            
            if logic_type == "Exclusion Constraint (Max Threshold)":
                self._render_exclusion_constraint(layer_name, modes, constraint_config)
            else:
                self._render_weighted_scoring(layer_name, modes, scoring_config)

    def _render_exclusion_constraint(self, layer_name, modes, constraint_config):
        """
        Renders exclusion constraint configuration.
        """
        st.info(f"🚫 Cells exceeding the maximum threshold will have final score = 0")
        
        # Step 1: Select which mode to use for constraint
        if len(modes) > 1:
            mode_options = list(modes.keys())
            selected_mode = st.selectbox(
                "Select metric for constraint:",
                options=mode_options,
                key=f"constraint_mode_{layer_name}"
            )
        else:
            selected_mode = list(modes.keys())[0]
            st.caption(f"Using: **{selected_mode}**")
        
        selected_column = modes[selected_mode]
        
        # Step 2: Set threshold value
        col1, col2 = st.columns([2, 3])
        with col1:
            if selected_mode == 'coverage':
                default_threshold = 50.0
                help_text = "Maximum allowed coverage percentage"
            elif selected_mode == 'distance':
                default_threshold = 10.0
                help_text = "Maximum allowed distance in km"
            else:
                default_threshold = 100.0
                help_text = f"Maximum allowed {selected_mode} value"
            
            threshold = st.number_input(
                "Maximum Allowed Value:",
                value=default_threshold,
                help=help_text,
                key=f"threshold_{layer_name}"
            )
        
        with col2:
            st.metric("Selected Column", selected_column)
            st.caption(f"Constraint: {selected_column} ≤ {threshold}")
        
        constraint_config[layer_name] = {
            'column': selected_column,
            'threshold': threshold,
            'mode': selected_mode
        }

    def _render_weighted_scoring(self, layer_name, modes, scoring_config):
        """
        Renders weighted scoring configuration with intelligent defaults.
        """
        # Step 1: Mode Selection (if multiple modes available)
        if len(modes) > 1:
            # Check if it's distance + coverage combination
            has_distance = 'distance' in modes
            has_coverage = 'coverage' in modes
            has_stats = any(m in modes for m in ['mean', 'max', 'min', 'median', 'std'])
            
            if has_distance and has_coverage:
                self._render_distance_coverage_scoring(layer_name, modes, scoring_config)
            elif has_stats:
                self._render_statistical_scoring(layer_name, modes, scoring_config)
            else:
                self._render_simple_mode_selection(layer_name, modes, scoring_config)
        else:
            # Single mode - straightforward scoring
            mode = list(modes.keys())[0]
            column = modes[mode]
            self._render_single_mode_scoring(layer_name, mode, column, scoring_config)

    def _render_distance_coverage_scoring(self, layer_name, modes, scoring_config):
        """
        Special handling for layers with both distance and coverage.
        """
        st.markdown("#### 🎯 Distance + Coverage Scoring")
        st.info("This layer has both distance and coverage metrics. Configure both scoring components.")
        
        col1, col2 = st.columns(2)
        
        # Weight input
        with col1:
            weight = st.number_input(
                "Layer Weight (%):",
                min_value=0,
                max_value=100,
                value=10,
                key=f"weight_{layer_name}"
            )
        
        with col2:
            max_coverage = st.number_input(
                "Max Coverage for Distance Scoring (%):",
                min_value=0.0,
                max_value=100.0,
                value=5.0,
                help="If coverage > this value, distance scoring will be skipped",
                key=f"max_cov_{layer_name}"
            )
        
        # Distance scoring levels
        st.markdown("**📏 Distance Scoring Levels** (used when coverage ≤ max)")
        default_config = self.DEFAULT_SCORING_CONFIGS.get('distance')
        distance_levels = self._render_level_inputs(layer_name, 'distance', default_config['levels'])
        
        scoring_config[layer_name] = {
            'type': 'distance_coverage',
            'weight': weight / 100.0,
            'distance_column': modes['distance'],
            'coverage_column': modes['coverage'],
            'max_coverage_threshold': max_coverage,
            'distance_levels': distance_levels
        }

    def _render_statistical_scoring(self, layer_name, modes, scoring_config):
        """
        Handles layers with statistical modes (mean, max, min, median, std).
        """
        st.markdown("#### 📊 Statistical Mode Selection")
        
        stat_modes = [m for m in modes.keys() if m in ['mean', 'max', 'min', 'median', 'std']]
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            weight = st.number_input(
                "Layer Weight (%):",
                min_value=0,
                max_value=100,
                value=10,
                key=f"weight_{layer_name}"
            )
        
        with col2:
            selected_mode = st.selectbox(
                "Select Statistical Metric:",
                options=stat_modes,
                key=f"stat_mode_{layer_name}"
            )
        
        selected_column = modes[selected_mode]
        
        # Determine default config based on layer name
        default_config = self._get_default_config_for_layer(layer_name)
        
        st.markdown(f"**📈 Scoring Levels for {selected_mode.upper()}**")
        levels = self._render_level_inputs(layer_name, selected_mode, default_config['levels'])
        
        scoring_config[layer_name] = {
            'type': 'single_mode',
            'weight': weight / 100.0,
            'column': selected_column,
            'mode': selected_mode,
            'levels': levels
        }

    def _render_simple_mode_selection(self, layer_name, modes, scoring_config):
        """
        Simple mode selection for other combinations.
        """
        mode_options = list(modes.keys())
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            weight = st.number_input(
                "Layer Weight (%):",
                min_value=0,
                max_value=100,
                value=10,
                key=f"weight_{layer_name}"
            )
        
        with col2:
            selected_mode = st.selectbox(
                "Select Metric:",
                options=mode_options,
                key=f"mode_select_{layer_name}"
            )
        
        selected_column = modes[selected_mode]
        default_config = self._get_default_config_for_layer(layer_name)
        
        st.markdown(f"**📈 Scoring Levels for {selected_mode.upper()}**")
        levels = self._render_level_inputs(layer_name, selected_mode, default_config['levels'])
        
        scoring_config[layer_name] = {
            'type': 'single_mode',
            'weight': weight / 100.0,
            'column': selected_column,
            'mode': selected_mode,
            'levels': levels
        }

    def _render_single_mode_scoring(self, layer_name, mode, column, scoring_config):
        """
        Renders scoring for a single mode layer.
        """
        col1, col2 = st.columns([1, 3])
        
        with col1:
            weight = st.number_input(
                "Weight (%):",
                min_value=0,
                max_value=100,
                value=10,
                key=f"weight_{layer_name}"
            )
        
        with col2:
            st.caption(f"Scoring metric: **{mode}** ({column})")
        
        default_config = self._get_default_config_for_layer(layer_name)
        
        st.markdown(f"**📈 Scoring Levels**")
        levels = self._render_level_inputs(layer_name, mode, default_config['levels'])
        
        scoring_config[layer_name] = {
            'type': 'single_mode',
            'weight': weight / 100.0,
            'column': column,
            'mode': mode,
            'levels': levels
        }

    def _render_level_inputs(self, layer_name, mode, default_levels):
        """
        Renders the 4-level scoring inputs.
        """
        levels_cols = st.columns(4)
        levels = []
        
        for i in range(4):
            with levels_cols[i]:
                st.caption(f"**Level {i+1}**")
                
                default = default_levels[i] if i < len(default_levels) else {'max': 0, 'min': 0, 'score': 0}
                
                l_max = st.number_input(
                    "Max",
                    value=float(default['max']),
                    key=f"max_{layer_name}_{mode}_{i}"
                )
                l_min = st.number_input(
                    "Min",
                    value=float(default['min']),
                    key=f"min_{layer_name}_{mode}_{i}"
                )
                l_score = st.number_input(
                    "Score",
                    value=int(default['score']),
                    key=f"score_{layer_name}_{mode}_{i}"
                )
                
                levels.append({'max': l_max, 'min': l_min, 'score': l_score})
        
        return levels

    def _get_default_config_for_layer(self, layer_name):
        """
        Returns appropriate default configuration based on layer name.
        """
        layer_lower = layer_name.lower()
        
        if 'slope' in layer_lower:
            return self.DEFAULT_SCORING_CONFIGS['slope']
        elif 'solar' in layer_lower or 'irradiation' in layer_lower:
            return self.DEFAULT_SCORING_CONFIGS['solar']
        elif 'distance' in layer_lower:
            return self.DEFAULT_SCORING_CONFIGS['distance']
        elif 'coverage' in layer_lower:
            return self.DEFAULT_SCORING_CONFIGS['coverage']
        else:
            return self.DEFAULT_SCORING_CONFIGS['default']

    def _run_calculation(self, df, scoring_config, constraint_config):
        """
        Applies scoring weights and then overlays exclusion constraints.
        """
        try:
            results_df = df.copy()
            # Remove any duplicate columns from the source to prevent issues
            results_df = results_df.loc[:, ~results_df.columns.duplicated()]
            
            total_weighted_score = np.zeros(len(results_df))
            
            # 1. Calculate Weighted Scores
            for layer_name, config in scoring_config.items():
                if config['type'] == 'distance_coverage':
                    # Special logic for distance + coverage
                    distance_col = config['distance_column']
                    coverage_col = config['coverage_column']
                    max_cov = config['max_coverage_threshold']
                    
                    # If coverage > threshold, score = 0, else use distance scoring
                    def get_distance_coverage_score(row):
                        if row[coverage_col] > max_cov:
                            return 0
                        else:
                            dist_val = row[distance_col]
                            for lv in config['distance_levels']:
                                if lv['min'] <= dist_val <= lv['max']:
                                    return lv['score']
                            return 0
                    
                    layer_scores = results_df.apply(get_distance_coverage_score, axis=1)
                    results_df[f"{layer_name}_SCORE"] = layer_scores
                    total_weighted_score += layer_scores * config['weight']
                
                elif config['type'] == 'single_mode':
                    # Standard single mode scoring
                    column = config['column']
                    
                    def get_level_score(val):
                        for lv in config['levels']:
                            if lv['min'] <= val <= lv['max']:
                                return lv['score']
                        return 0
                    
                    layer_scores = results_df[column].apply(get_level_score)
                    results_df[f"{layer_name}_SCORE"] = layer_scores
                    total_weighted_score += layer_scores * config['weight']

            results_df['FINAL_GRID_SCORE'] = total_weighted_score

            # 2. Apply Hard Exclusion Constraints
            exclusion_tracking = []
            for layer_name, config in constraint_config.items():
                column = config['column']
                threshold = config['threshold']
                
                exclusion_mask = results_df[column] > threshold
                excluded_count = exclusion_mask.sum()
                
                results_df.loc[exclusion_mask, 'FINAL_GRID_SCORE'] = 0
                
                if 'EXCLUSION_REASONS' not in results_df.columns:
                    results_df['EXCLUSION_REASONS'] = ''
                
                results_df.loc[exclusion_mask, 'EXCLUSION_REASONS'] += f"{layer_name}; "
                
                exclusion_tracking.append({
                    'Layer': layer_name,
                    'Column': column,
                    'Threshold': threshold,
                    'Excluded Cells': excluded_count
                })

            st.success("✅ Scoring Complete!")
            
            # Display Summary Statistics
            st.subheader("📊 Scoring Summary")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Cells", len(results_df))
            with col2:
                excluded = (results_df['FINAL_GRID_SCORE'] == 0).sum()
                st.metric("Excluded Cells", excluded)
            with col3:
                st.metric("Avg Score", f"{results_df['FINAL_GRID_SCORE'].mean():.2f}")
            
            # Exclusion breakdown
            if exclusion_tracking:
                st.subheader("🚫 Exclusion Summary")
                exclusion_df = pd.DataFrame(exclusion_tracking)
                st.dataframe(exclusion_df, use_container_width=True)
            
            # Score distribution
            st.subheader("📈 Score Distribution")
            score_ranges = [
                ('Excellent (80-100)', (results_df['FINAL_GRID_SCORE'] >= 80).sum()),
                ('Good (60-80)', ((results_df['FINAL_GRID_SCORE'] >= 60) & (results_df['FINAL_GRID_SCORE'] < 80)).sum()),
                ('Fair (40-60)', ((results_df['FINAL_GRID_SCORE'] >= 40) & (results_df['FINAL_GRID_SCORE'] < 60)).sum()),
                ('Poor (20-40)', ((results_df['FINAL_GRID_SCORE'] >= 20) & (results_df['FINAL_GRID_SCORE'] < 40)).sum()),
                ('Very Poor (0-20)', ((results_df['FINAL_GRID_SCORE'] > 0) & (results_df['FINAL_GRID_SCORE'] < 20)).sum()),
                ('Excluded (0)', (results_df['FINAL_GRID_SCORE'] == 0).sum())
            ]
            
            dist_df = pd.DataFrame(score_ranges, columns=['Range', 'Count'])
            st.dataframe(dist_df, use_container_width=True)
            
            # Results Preview
            st.subheader("📋 Results Preview")
            # Deduplicate columns for preview
            preview_cols = ['cell_id', 'FINAL_GRID_SCORE'] + [col for col in results_df.columns if '_SCORE' in col and col != 'FINAL_GRID_SCORE']
            
            # Ensure unique columns (preserve order)
            seen = set()
            unique_preview_cols = [x for x in preview_cols if not (x in seen or seen.add(x))]
            
            if 'EXCLUSION_REASONS' in results_df.columns:
                unique_preview_cols.append('EXCLUSION_REASONS')
            
            st.dataframe(results_df[unique_preview_cols].head(20), use_container_width=True)
            
            # Download
            csv = results_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download Complete Results",
                csv,
                "final_scored_analysis.csv",
                "text/csv",
                use_container_width=True
            )
            
            # Store results
            self.state.final_scored_results = results_df

        except Exception as e:
            st.error(f"❌ Calculation failed: {e}")
            import traceback
            st.code(traceback.format_exc())

    def _render_csv_import(self):
        """Renders CSV import interface."""
        uploaded_file = st.file_uploader(
            "Upload Analysis Results CSV",
            type=['csv'],
            key="manual_import"
        )
        
        if uploaded_file:
            try:
                imported_df = pd.read_csv(uploaded_file)
                if 'cell_id' in imported_df.columns:
                    self.state.scoring_results = imported_df
                    self.state.scoring_complete = True
                    st.success(f"✅ CSV Loaded: {len(imported_df):,} rows")
                else:
                    st.error("❌ 'cell_id' column not found in uploaded CSV.")
            except Exception as e:
                st.error(f"❌ Failed to load CSV: {e}")

    def validate(self):
        """Validates that scoring data is available."""
        return self.state.get('scoring_complete', False)