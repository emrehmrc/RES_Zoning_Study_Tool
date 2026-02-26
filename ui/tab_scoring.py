"""
Scoring tab - Configure and run raster distance/coverage calculation - ENHANCED
Now supports multiple analysis modes per layer with predefined defaults
"""
import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely import wkt
from pathlib import Path
import os
from ui.base_tab import BaseTab
from engines.raster_scorer import UniversalRasterScorer
from config import Config

class ScoringTab(BaseTab):
    """
    Enhanced tab for raster layer analysis with multiple modes
    """
    
    def __init__(self, session_state, config):
        """
        Initialize with session state and configuration
        """
        super().__init__(session_state)
        self.config = config

    def render(self):
        st.header("🎯 Step 2: Distance & Coverage Analysis")
        st.markdown("---")
        
        if not self.validate():
            st.warning("⚠️ Please complete Step 1 (Gridization) first!")
            return
        
        st.success(f"✅ Grid loaded: {len(self.state.grid_df):,} cells")
        
        self._render_layer_configuration()
        
        if st.button("🚀 Run Analysis", type="primary", use_container_width=True):
            self._run_analysis()
    
    def _render_layer_configuration(self):
        """Render enhanced layer configuration interface"""
        st.subheader("📋 Configure Analysis Layers")
        

        # Add new layer
        with st.expander("➕ Add New Layer", expanded=len(self.state.layer_configs) == 0):
            
            # MOVE layer_mode OUTSIDE the form
            layer_mode = st.radio(
                "Layer Configuration Method:",
                ["Select from Predefined List", "Custom Layer Name"],
                horizontal=True,
                key="layer_mode"
            )

            st.markdown("### 📁 Select Raster File")
            
            # File selection method
            selection_source = st.radio(
                "File Selection Method",
                ["Browse Directory", "Direct File Path"],
                horizontal=True,
                label_visibility="collapsed",
                key="file_selection_source"
            )
            
            selected_raster_path = None
            suggested_name = ""
            
            if selection_source == "Browse Directory":
                # Directory browser
                default_dir = str(Config.DATA_DIR)
                if not os.path.exists(default_dir):
                    default_dir = os.getcwd()
                    
                col_dir, col_reload = st.columns([6, 1])
                with col_dir:
                    scan_dir = st.text_input("Directory Path", value=default_dir, key="scan_dir_path")
                with col_reload:
                    st.write("") # Spacer
                    st.write("") 
                    scan_reload = st.button("🔄", help="Refresh Directory")
                
                if os.path.isdir(scan_dir):
                    try:
                        # Find tif files
                        files = self._scan_directory_for_rasters(scan_dir)
                        if files:
                            selected_file = st.selectbox("Select File", options=files, key="file_selector_box")
                            selected_raster_path = str(Path(scan_dir) / selected_file)
                            suggested_name = Path(selected_file).stem
                        else:
                            st.warning(f"No .tif files found in {scan_dir}")
                    except Exception as e:
                        st.error(f"Error reading directory: {e}")
                else:
                    st.error("Invalid directory path")
                    
            else:
                # Direct path input
                path_input = st.text_input(
                    "Full File Path", 
                    placeholder="C:/path/to/large_raster.tif",
                    key="direct_path_input",
                    help="Paste the absolute path to your local .tif file"
                )
                if path_input:
                    # Remove quotes if user pasted them
                    path_input = path_input.strip('"').strip("'")
                    if os.path.isfile(path_input) and path_input.lower().endswith(('.tif', '.tiff')):
                        selected_raster_path = path_input
                        suggested_name = Path(path_input).stem
                    else:
                        st.error("File not found or not a TIF file")
            
            # Display selected file confirmation
            if selected_raster_path:
                st.success(f"Selected: {Path(selected_raster_path).name}")
            
            # Now create form with different content based on layer_mode
            with st.form("add_layer_form", clear_on_submit=False): # Changed clear_on_submit to False to keep path
                
                # Layer name based on mode
                if layer_mode == "Select from Predefined List":
                    used_layers = [cfg['prefix'] for cfg in self.state.layer_configs]
                    available_layers = [l for l in self.config.ALL_LAYER_NAMES if l not in used_layers]
                    
                    if available_layers:
                        layer_name = st.selectbox(
                            "🏷️ Layer Name",
                            options=available_layers,
                            index=None,
                            placeholder="Select a layer...",
                            key="new_layer_name_select"
                        )
                        
                        # Show predefined modes (non-editable)
                        if layer_name:
                            predefined_modes = self.config.PREDEFINED_LAYER_MODES.get(layer_name, [])
                            st.info(f"ℹ️ This layer will use the following analysis modes: **{', '.join(predefined_modes)}**")
                    else:
                        st.warning("⚠️ All predefined layers have been added!")
                        layer_name = None
                else:
                    # Custom layer name
                    layer_name = st.text_input(
                        "🏷️ Custom Layer Name",
                        value=suggested_name,
                        placeholder="e.g., My Custom Layer",
                        key="new_layer_name_custom"
                    )
                    
                    # Analysis modes selection (only for custom layers)
                    st.markdown("### 📊 Analysis Modes")
                    st.caption("Select one or more analysis modes for this custom layer")
                    
                    col1, col2 = st.columns([3, 2])
                    
                    with col1:
                        col_mode1, col_mode2 = st.columns(2)
                        
                        with col_mode1:
                            mode_distance = st.checkbox(
                                "Distance (km)",
                                value=False,
                                help="Calculate minimum distance to target value",
                                key="mode_distance"
                            )
                            mode_coverage = st.checkbox(
                                "Coverage (%)",
                                value=False,
                                help="Calculate percentage of target value",
                                key="mode_coverage"
                            )
                            mode_mean = st.checkbox(
                                "Mean",
                                value=True,
                                help="Calculate mean of pixel values",
                                key="mode_mean"
                            )
                            mode_median = st.checkbox(
                                "Median",
                                value=False,
                                help="Calculate median of pixel values",
                                key="mode_median"
                            )
                        
                        with col_mode2:
                            mode_max = st.checkbox(
                                "Maximum",
                                value=False,
                                help="Calculate maximum pixel value",
                                key="mode_max"
                            )
                            mode_min = st.checkbox(
                                "Minimum",
                                value=False,
                                help="Calculate minimum pixel value",
                                key="mode_min"
                            )
                            mode_std = st.checkbox(
                                "Std Dev",
                                value=False,
                                help="Calculate standard deviation",
                                key="mode_std"
                            )
                            mode_categorical = st.checkbox(
                                "Categorical",
                                value=False,
                                help="Get distribution of all values",
                                key="mode_categorical"
                            )
                        
                        # Target value (only needed for distance/coverage)
                        if mode_distance or mode_coverage:
                            target_value = st.number_input(
                                "🎯 Target Pixel Value (for Distance/Coverage)",
                                min_value=0,
                                max_value=255,
                                value=1,
                                help="Pixel value to calculate distance/coverage from",
                                key="new_target_value"
                            )
                        else:
                            target_value = 1
                    
                    with col2:
                        st.markdown("### 📚 Mode Descriptions")
                        
                        st.markdown("""
                        **Distance**: Minimum distance in km to cells with target value
                        
                        **Coverage**: Percentage of pixels with target value
                        
                        **Mean**: Average of all pixel values in each cell
                        
                        **Maximum**: Highest pixel value in each cell
                        
                        **Minimum**: Lowest pixel value in each cell
                        
                        **Median**: Middle value of pixels in each cell
                        
                        **Std Dev**: Variability of pixel values
                        
                        **Categorical**: Distribution of all unique values
                        """)
                
                submit_button = st.form_submit_button("➕ Add Layer", type="primary", use_container_width=True)

                if submit_button:
                    # Validation
                    if not selected_raster_path or not layer_name:
                        st.error("⚠️ Please select a file and provide a layer name!")
                    elif layer_name in [cfg['prefix'] for cfg in self.state.layer_configs]:
                        st.error(f"⚠️ Layer '{layer_name}' already exists!")
                    else:
                        # Use local path directly
                        full_raster_path = selected_raster_path
                        
                        # Determine modes based on layer type
                        if layer_mode == "Select from Predefined List":
                            # Use predefined modes
                            selected_modes = self.config.PREDEFINED_LAYER_MODES.get(layer_name, ['mean'])
                            is_predefined = True
                            target_value = 1  # Default for predefined
                        else:
                            # Collect selected modes for custom layer
                            selected_modes = []
                            if mode_distance:
                                selected_modes.append('distance')
                            if mode_coverage:
                                selected_modes.append('coverage')
                            if mode_mean:
                                selected_modes.append('mean')
                            if mode_max:
                                selected_modes.append('max')
                            if mode_min:
                                selected_modes.append('min')
                            if mode_median:
                                selected_modes.append('median')
                            if mode_std:
                                selected_modes.append('std')
                            if mode_categorical:
                                selected_modes.append('categorical')
                            is_predefined = False
                            
                            # Validate custom layer has modes
                            if not selected_modes:
                                st.error("⚠️ Please select at least one analysis mode!")
                                st.stop()
                        
                        # Add to configs
                        layer_config = {
                            'path': full_raster_path,
                            'prefix': layer_name,
                            'analysis_modes': selected_modes,
                            'target_value': target_value,
                            'config': {},
                            'is_predefined': is_predefined
                        }
                        
                        self.state.layer_configs.append(layer_config)
                        st.success(f"✅ Layer '{layer_name}' added with {len(selected_modes)} mode(s)!")
                        st.rerun()

        # Show existing layers
        if self.state.layer_configs:
            st.markdown("### 🗂️ Configured Layers")
            
            # Group layers by category
            categorized_layers = {cat: [] for cat in self.config.LAYER_CATEGORIES.keys()}
            uncategorized_layers = []
            
            for config in self.state.layer_configs:
                layer_name = config['prefix']
                found = False
                for category, layers in self.config.LAYER_CATEGORIES.items():
                    if layer_name in layers:
                        categorized_layers[category].append(config)
                        found = True
                        break
                if not found:
                    uncategorized_layers.append(config)
            
            # Display categorized layers
            for category, layers in categorized_layers.items():
                if layers:
                    with st.expander(f"📂 {category} ({len(layers)} layers)", expanded=True):
                        for config in layers:
                            self._render_layer_card(config)
            
            # Display uncategorized layers
            if uncategorized_layers:
                with st.expander(f"📂 Custom Layers ({len(uncategorized_layers)} layers)", expanded=True):
                    for config in uncategorized_layers:
                        self._render_layer_card(config)
            
            # Summary
            total_modes = sum(len(cfg.get('analysis_modes', [])) for cfg in self.state.layer_configs)
            predefined_count = sum(1 for cfg in self.state.layer_configs if cfg.get('is_predefined', False))
            custom_count = len(self.state.layer_configs) - predefined_count
            
            st.info(f"📊 **Total:** {len(self.state.layer_configs)} layers ({predefined_count} predefined, {custom_count} custom), {total_modes} analysis modes")
    
    def _render_layer_card(self, config):
        """Render enhanced layer configuration card"""
        col1, col2, col3 = st.columns([3, 2, 1])
        
        with col1:
            layer_type_badge = "🏷️" if config.get('is_predefined', False) else "🔧"
            st.markdown(f"{layer_type_badge} **{config['prefix']}**")
            st.caption(f"📍 {Path(config['path']).name}")
        
        with col2:
            # Display analysis modes
            modes = config.get('analysis_modes', [])
            mode_icons = {
                'distance': '',
                'coverage': '',
                'mean': '',
                'max': '',
                'min': '',
                'median': '',
                'std': '',
                'categorical': ''
            }
            
            mode_display = ' '.join([f"{mode_icons.get(m, '•')}{m}" for m in modes])
            st.caption(f"**Modes:** {mode_display}")
            
            if 'distance' in modes or 'coverage' in modes:
                st.caption(f"Target: {config.get('target_value', 1)}")
        
        with col3:
            idx = self.state.layer_configs.index(config)
            if st.button("🗑️", key=f"remove_{idx}", help=f"Remove {config['prefix']}"):
                self.state.layer_configs.pop(idx)
                st.rerun()
    
    def _run_analysis(self):
        """Execute the enhanced raster analysis"""
        if not self.state.layer_configs:
            st.error("⚠️ Please add at least one layer!")
            return
        
        try:
            # Prepare grid
            grid_df = self.state.grid_df.copy()
            grid_df['geometry'] = grid_df['wkt'].apply(wkt.loads)
            grid_gdf = gpd.GeoDataFrame(grid_df, geometry='geometry', crs='EPSG:3857')
            
            if 'cell_id' not in grid_gdf.columns:
                grid_gdf['cell_id'] = range(len(grid_gdf))
            
            # Run analysis
            st.info("Working on multi-mode analysis...")
            
            scorer = UniversalRasterScorer()

            result = scorer.calculate_layers_adaptive(
                grid_gdf=grid_gdf,
                layer_configs=self.state.layer_configs,
                chunk_size=Config.DEFAULT_CHUNK_SIZE, 
                n_workers=Config.DEFAULT_N_WORKERS
            )
                        
            # Store results
            self.state.scoring_results = result
            self.state.scoring_complete = True
            
            st.success(f"✅ Analysis complete! {len(result):,} cells processed")
            
            # Show summary statistics
            st.subheader("📊 Summary Statistics")
            
            for category, layer_names in self.config.LAYER_CATEGORIES.items():
                category_configs = [
                    cfg for cfg in self.state.layer_configs 
                    if cfg['prefix'] in layer_names
                ]
                
                if category_configs:
                    with st.expander(f"📂 {category} ({len(category_configs)} layers)", expanded=True):
                        for config in category_configs:
                            self._render_layer_statistics(result, config)
            
            # Uncategorized layers
            uncategorized = [
                cfg for cfg in self.state.layer_configs 
                if cfg['prefix'] not in self.config.ALL_LAYER_NAMES
            ]
            
            if uncategorized:
                with st.expander(f"📂 Custom Layers ({len(uncategorized)} layers)", expanded=True):
                    for config in uncategorized:
                        self._render_layer_statistics(result, config)
            
            # Show data preview
            st.subheader("📋 Data Preview")
            st.dataframe(result.head(20), use_container_width=True)
            
            # Download button
            csv = result.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
            st.download_button(
                label="📥 Download Results CSV",
                data=csv,
                file_name="raster_analysis_results.csv",
                mime="text/csv",
                use_container_width=True
            )
            
        except Exception as e:
            st.error(f"❌ Analysis failed: {e}")
            import traceback
            st.code(traceback.format_exc())
    
    def _render_layer_statistics(self, result, config):
        """Render statistics for all modes in a layer"""
        prefix = config['prefix']
        modes = config.get('analysis_modes', [])
        
        layer_type = "Predefined" if config.get('is_predefined', False) else "Custom"
        st.markdown(f"**{prefix}** *({layer_type})*")
        st.caption(f"Analysis Modes: {', '.join(modes)}")
        
        # Create columns based on number of modes
        n_cols = min(4, len(modes))
        cols = st.columns(n_cols)
        
        col_idx = 0
        for mode in modes:
            if mode == 'distance':
                col_name = f"{prefix}_dist_km"
                if col_name in result.columns:
                    with cols[col_idx % n_cols]:
                        st.metric("Avg Distance", f"{result[col_name].mean():.2f} km")
                    col_idx += 1
            
            elif mode == 'coverage':
                col_name = f"{prefix}_coverage_pct"
                if col_name in result.columns:
                    with cols[col_idx % n_cols]:
                        st.metric("Avg Coverage", f"{result[col_name].mean():.1f}%")
                    col_idx += 1
            
            elif mode == 'mean':
                col_name = f"{prefix}_mean"
                if col_name in result.columns:
                    with cols[col_idx % n_cols]:
                        st.metric("Mean Value", f"{result[col_name].mean():.2f}")
                    col_idx += 1
            
            elif mode == 'max':
                col_name = f"{prefix}_max"
                if col_name in result.columns:
                    with cols[col_idx % n_cols]:
                        st.metric("Max Value", f"{result[col_name].max():.2f}")
                    col_idx += 1
            
            elif mode == 'min':
                col_name = f"{prefix}_min"
                if col_name in result.columns:
                    with cols[col_idx % n_cols]:
                        st.metric("Min Value", f"{result[col_name].min():.2f}")
                    col_idx += 1
            
            elif mode == 'median':
                col_name = f"{prefix}_median"
                if col_name in result.columns:
                    with cols[col_idx % n_cols]:
                        st.metric("Median", f"{result[col_name].median():.2f}")
                    col_idx += 1
            
            elif mode == 'std':
                col_name = f"{prefix}_std"
                if col_name in result.columns:
                    with cols[col_idx % n_cols]:
                        st.metric("Avg Std Dev", f"{result[col_name].mean():.2f}")
                    col_idx += 1
        
        st.markdown("---")
    
    def _scan_directory_for_rasters(self, directory):
        """Scan directory for .tif and .tiff files"""
        if not os.path.isdir(directory):
            return []
        
        return [f for f in os.listdir(directory) if f.lower().endswith(('.tif', '.tiff'))]

    def validate(self):
        """Validate that grid is ready"""
        return hasattr(self.state, 'grid_created') and self.state.grid_created