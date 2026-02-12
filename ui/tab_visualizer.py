"""
Visualizer Tab - QGIS-like map visualization with layer management
Displays analysis results with interactive controls for transparency, visibility, and styling
"""
import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely import wkt
import folium
from streamlit_folium import st_folium
from folium import plugins
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from ui.base_tab import BaseTab
import numpy as np


class VisualizerTab(BaseTab):
    """
    Interactive map visualizer with layer management
    """
    
    # Color schemes for different layer types
    COLOR_SCHEMES = {
        'Sequential': ['YlOrRd', 'YlGnBu', 'RdPu', 'Greens', 'Blues', 'Reds', 'Greys'],
        'Diverging': ['RdYlGn', 'RdYlBu', 'RdBu', 'PiYG', 'Spectral'],
        'Qualitative': ['Set1', 'Set2', 'Set3', 'Pastel1', 'Pastel2']
    }
    
    def render(self):
        st.header("🗺️ Step 4: Map Visualizer")
        st.markdown("---")
        
        # Check if we have data to visualize
        if not self._check_data_availability():
            return
        
        # Initialize layer states if not exists
        if 'layer_states' not in self.state:
            self.state.layer_states = {}
        
        # Main layout: Sidebar for controls, Main area for map
        col_controls, col_map = st.columns([1, 3])
        
        with col_controls:
            self._render_layer_controls()
        
        with col_map:
            self._render_map()
    
    def _check_data_availability(self):
        """Check if visualization data is available"""
        has_grid = hasattr(self.state, 'grid_created') and self.state.grid_created
        has_analysis = hasattr(self.state, 'scoring_results') and self.state.scoring_results is not None
        has_final = hasattr(self.state, 'final_scored_results') and self.state.final_scored_results is not None
        
        if not has_grid:
            st.warning("⚠️ No grid data available. Please complete Step 1 (Gridization).")
            return False
        
        if not has_analysis and not has_final:
            st.info("ℹ️ No analysis results available. Complete Step 2 or Step 3 to visualize results.")
            # Show grid only
            return True
        
        return True
    
    def _get_available_layers(self):
        """Get list of available layers from analysis results"""
        layers = {
            'Grid': {
                'type': 'base',
                'description': 'Base grid cells',
                'data_source': 'grid_df'
            }
        }
        
        # Add analysis layers
        if hasattr(self.state, 'scoring_results') and self.state.scoring_results is not None:
            df = self.state.scoring_results
            metadata_cols = ['cell_id', 'wkt', 'geometry', 'Center_X', 'Center_Y', 'Center_X_4326', 'Center_Y_4326']
            analysis_cols = [col for col in df.columns if col not in metadata_cols]
            
            for col in analysis_cols:
                layers[col] = {
                    'type': 'analysis',
                    'description': f'Analysis metric: {col}',
                    'data_source': 'scoring_results',
                    'column': col
                }
        
        # Add final score layer
        if hasattr(self.state, 'final_scored_results') and self.state.final_scored_results is not None:
            layers['FINAL_GRID_SCORE'] = {
                'type': 'final_score',
                'description': 'Final weighted score',
                'data_source': 'final_scored_results',
                'column': 'FINAL_GRID_SCORE'
            }
            
            # Add individual layer scores
            df = self.state.final_scored_results
            score_cols = [col for col in df.columns if col.endswith('_SCORE') and col != 'FINAL_GRID_SCORE']
            for col in score_cols:
                layers[col] = {
                    'type': 'layer_score',
                    'description': f'Layer score: {col}',
                    'data_source': 'final_scored_results',
                    'column': col
                }
        
        return layers
    
    def _render_layer_controls(self):
        """Render layer management controls (like QGIS layer panel)"""
        st.subheader("🗂️ Layer Manager")
        
        available_layers = self._get_available_layers()
        
        # Base map selection
        st.markdown("### 🗺️ Base Map")
        base_map = st.selectbox(
            "Select base map:",
            ['OpenStreetMap', 'CartoDB Positron', 'CartoDB Dark Matter', 'Stamen Terrain', 'Stamen Toner'],
            key='base_map_select'
        )
        
        st.markdown("---")
        st.markdown("### 📊 Data Layers")
        
        # Layer categories
        layer_categories = {
            'Final Score': [name for name, info in available_layers.items() if info['type'] == 'final_score'],
            'Layer Scores': [name for name, info in available_layers.items() if info['type'] == 'layer_score'],
            'Analysis Metrics': [name for name, info in available_layers.items() if info['type'] == 'analysis'],
            'Base Layers': [name for name, info in available_layers.items() if info['type'] == 'base']
        }
        
        for category, layer_names in layer_categories.items():
            if not layer_names:
                continue
            
            with st.expander(f"📁 {category} ({len(layer_names)})", expanded=(category in ['Final Score', 'Base Layers'])):
                for layer_name in layer_names:
                    self._render_layer_control_item(layer_name, available_layers[layer_name])
        
        st.markdown("---")
        
        # Global controls
        st.markdown("### ⚙️ Global Settings")
        
        if st.button("👁️ Show All Layers", use_container_width=True):
            for layer_name in available_layers.keys():
                if layer_name not in self.state.layer_states:
                    self.state.layer_states[layer_name] = {}
                self.state.layer_states[layer_name]['visible'] = True
            st.rerun()
        
        if st.button("🚫 Hide All Layers", use_container_width=True):
            for layer_name in available_layers.keys():
                if layer_name not in self.state.layer_states:
                    self.state.layer_states[layer_name] = {}
                self.state.layer_states[layer_name]['visible'] = False
            st.rerun()
        
        if st.button("🔄 Reset Settings", use_container_width=True):
            self.state.layer_states = {}
            st.rerun()
    
    def _render_layer_control_item(self, layer_name, layer_info):
        """Render individual layer control"""
        # Initialize layer state if not exists
        if layer_name not in self.state.layer_states:
            self.state.layer_states[layer_name] = {
                'visible': layer_name in ['Grid', 'FINAL_GRID_SCORE'],  # Default visibility
                'opacity': 0.7,
                'color_scheme': 'YlOrRd',
                'reverse_colors': False
            }
        
        layer_state = self.state.layer_states[layer_name]
        
        # Layer header with visibility toggle
        col1, col2 = st.columns([3, 1])
        
        with col1:
            visible = st.checkbox(
                layer_name,
                value=layer_state['visible'],
                key=f"vis_{layer_name}",
                help=layer_info['description']
            )
            layer_state['visible'] = visible
        
        with col2:
            if visible:
                st.markdown("👁️")
            else:
                st.markdown("🚫")
        
        # Expanded controls when visible
        if visible and layer_info['type'] != 'base':
            with st.container():
                # Opacity slider
                opacity = st.slider(
                    "Opacity",
                    min_value=0.0,
                    max_value=1.0,
                    value=layer_state['opacity'],
                    step=0.1,
                    key=f"opacity_{layer_name}",
                    label_visibility="collapsed"
                )
                layer_state['opacity'] = opacity
                
                # Color scheme (for data layers)
                if layer_info['type'] in ['analysis', 'final_score', 'layer_score']:
                    col_a, col_b = st.columns([2, 1])
                    
                    with col_a:
                        color_scheme = st.selectbox(
                            "Colors",
                            options=self.COLOR_SCHEMES['Sequential'] + self.COLOR_SCHEMES['Diverging'],
                            index=self.COLOR_SCHEMES['Sequential'].index(layer_state['color_scheme']),
                            key=f"color_{layer_name}",
                            label_visibility="collapsed"
                        )
                        layer_state['color_scheme'] = color_scheme
                    
                    with col_b:
                        reverse = st.checkbox(
                            "⇅",
                            value=layer_state['reverse_colors'],
                            key=f"reverse_{layer_name}",
                            help="Reverse color scheme"
                        )
                        layer_state['reverse_colors'] = reverse
                
                st.markdown("---")
    
    def _render_map(self):
        """Render the main map with all visible layers"""
        st.subheader("🗺️ Interactive Map")
        
        # Get visible layers
        visible_layers = {
            name: state for name, state in self.state.layer_states.items() 
            if state.get('visible', False)
        }
        
        if not visible_layers:
            st.info("ℹ️ No layers selected. Enable layers from the Layer Manager panel.")
            return
        
        # Create base map
        base_map_type = st.session_state.get('base_map_select', 'CartoDB Positron')
        m = self._create_base_map(base_map_type)
        
        # Add layers in order (base layers first, then analysis, then scores)
        layer_order = ['base', 'analysis', 'layer_score', 'final_score']
        available_layers = self._get_available_layers()
        
        for layer_type in layer_order:
            for layer_name, layer_state in visible_layers.items():
                if layer_name in available_layers and available_layers[layer_name]['type'] == layer_type:
                    self._add_layer_to_map(m, layer_name, available_layers[layer_name], layer_state)
        
        # Add layer control
        folium.LayerControl(collapsed=False).add_to(m)
        
        # Display map
        map_data = st_folium(m, width=1200, height=700, returned_objects=[])
        
        # Legend
        self._render_legend(visible_layers, available_layers)
    
    def _create_base_map(self, base_map_type):
        """Create folium base map"""
        # Get center from grid
        if hasattr(self.state, 'grid_df') and self.state.grid_df is not None:
            center_x = self.state.grid_df['Center_X_4326'].mean()
            center_y = self.state.grid_df['Center_Y_4326'].mean()
        else:
            center_x, center_y = 0, 0
        
        # Map tiles configuration
        tiles_map = {
            'OpenStreetMap': 'OpenStreetMap',
            'CartoDB Positron': 'CartoDB positron',
            'CartoDB Dark Matter': 'CartoDB dark_matter',
            'Stamen Terrain': 'Stamen Terrain',
            'Stamen Toner': 'Stamen Toner'
        }
        
        m = folium.Map(
            location=[center_y, center_x],
            zoom_start=8,
            tiles=tiles_map.get(base_map_type, 'CartoDB positron'),
            control_scale=True
        )
        
        # Add fullscreen option
        plugins.Fullscreen().add_to(m)
        
        return m
    
    def _add_layer_to_map(self, m, layer_name, layer_info, layer_state):
        """Add a data layer to the map"""
        # Get data
        data_source = layer_info['data_source']
        
        if data_source == 'grid_df':
            df = self.state.grid_df.copy()
            value_column = None
        elif data_source == 'scoring_results':
            df = self.state.scoring_results.copy()
            value_column = layer_info['column']
        elif data_source == 'final_scored_results':
            df = self.state.final_scored_results.copy()
            value_column = layer_info['column']
        else:
            return
        
        # Add geometry if not present
        if 'geometry' not in df.columns:
            df['geometry'] = df['wkt'].apply(wkt.loads)
        
        # Convert to GeoDataFrame
        gdf = gpd.GeoDataFrame(df, geometry='geometry', crs='EPSG:3857')
        gdf = gdf.to_crs('EPSG:4326')
        
        # Create color mapping if value column exists
        if value_column:
            # Filter out NaN values for color mapping
            valid_gdf = gdf[gdf[value_column].notna()].copy()
            
            if len(valid_gdf) == 0:
                return
            
            # Get color scheme
            cmap_name = layer_state['color_scheme']
            if layer_state['reverse_colors']:
                cmap_name = cmap_name + '_r'
            
            # Create colormap
            vmin = valid_gdf[value_column].min()
            vmax = valid_gdf[value_column].max()
            
            # Handle case where all values are the same
            if vmin == vmax:
                vmax = vmin + 1
            
            cmap = plt.cm.get_cmap(cmap_name)
            norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
            
            # Add to map with colors
            feature_group = folium.FeatureGroup(name=layer_name, show=True)
            
            for idx, row in valid_gdf.iterrows():
                value = row[value_column]
                color_rgba = cmap(norm(value))
                color_hex = mcolors.rgb2hex(color_rgba[:3])
                
                # Create popup content
                popup_content = f"""
                <b>{layer_name}</b><br>
                Cell ID: {row.get('cell_id', 'N/A')}<br>
                Value: {value:.2f}
                """
                
                folium.GeoJson(
                    row.geometry.__geo_interface__,
                    style_function=lambda x, color=color_hex, opacity=layer_state['opacity']: {
                        'fillColor': color,
                        'color': color,
                        'weight': 1,
                        'fillOpacity': opacity,
                        'opacity': opacity * 0.8
                    },
                    tooltip=f"{layer_name}: {value:.2f}",
                    popup=folium.Popup(popup_content, max_width=300)
                ).add_to(feature_group)
            
            feature_group.add_to(m)
        
        else:
            # No value column - just show geometry (like grid)
            feature_group = folium.FeatureGroup(name=layer_name, show=True)
            
            folium.GeoJson(
                gdf,
                style_function=lambda x, opacity=layer_state['opacity']: {
                    'fillColor': 'blue',
                    'color': 'black',
                    'weight': 1,
                    'fillOpacity': opacity * 0.3,
                    'opacity': opacity
                },
                tooltip=layer_name
            ).add_to(feature_group)
            
            feature_group.add_to(m)
    
    def _render_legend(self, visible_layers, available_layers):
        """Render legend for visible layers"""
        st.markdown("### 📊 Legend")
        
        for layer_name, layer_state in visible_layers.items():
            if layer_name not in available_layers:
                continue
            
            layer_info = available_layers[layer_name]
            
            if layer_info['type'] in ['analysis', 'final_score', 'layer_score']:
                # Get data statistics
                data_source = layer_info['data_source']
                value_column = layer_info['column']
                
                if data_source == 'scoring_results':
                    df = self.state.scoring_results
                elif data_source == 'final_scored_results':
                    df = self.state.final_scored_results
                else:
                    continue
                
                values = df[value_column].dropna()
                
                if len(values) == 0:
                    continue
                
                with st.expander(f"📈 {layer_name}", expanded=True):
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Min", f"{values.min():.2f}")
                    with col2:
                        st.metric("Max", f"{values.max():.2f}")
                    with col3:
                        st.metric("Mean", f"{values.mean():.2f}")
                    with col4:
                        st.metric("Std", f"{values.std():.2f}")
                    
                    # Color gradient preview
                    st.markdown(f"**Color Scheme:** {layer_state['color_scheme']}")
                    
                    # Create color bar
                    fig, ax = plt.subplots(figsize=(6, 0.5))
                    cmap_name = layer_state['color_scheme']
                    if layer_state['reverse_colors']:
                        cmap_name = cmap_name + '_r'
                    
                    cmap = plt.cm.get_cmap(cmap_name)
                    norm = mcolors.Normalize(vmin=values.min(), vmax=values.max())
                    
                    cb = plt.colorbar(
                        plt.cm.ScalarMappable(norm=norm, cmap=cmap),
                        cax=ax,
                        orientation='horizontal'
                    )
                    cb.set_label(value_column)
                    
                    st.pyplot(fig)
                    plt.close()
    
    def validate(self):
        """Validation - always allow access to visualizer"""
        return True