"""
Gridization tab - Create or upload grid
"""
import streamlit as st
import geopandas as gpd
import pandas as pd
from shapely import wkt
from pathlib import Path
from ui.base_tab import BaseTab
from engines.grid_engine import FastGridEngine
from config import Config
import folium
from streamlit_folium import st_folium


class GridizationTab(BaseTab):
    """
    Tab for grid creation or upload
    """
    
    def render(self):
        st.header("📐 Step 1: Gridization")
        st.markdown("---")
        
        # Ana kaynak seçimi: Yeni mi oluşturulacak yoksa mevcut CSV mi yüklenecek?
        grid_option = st.radio(
            "Choose Grid Option:",
            ["Yeni Grid Oluştur", "Mevcut Grid CSV Yükle"],
            key="grid_option",
            horizontal=True
        )
        
        if grid_option == "Yeni Grid Oluştur":
            self._render_grid_creation()
        else:
            self._render_grid_upload()
    
    def _render_grid_creation(self):
        """Grid oluşturma arayüzünü oluşturur"""
        st.subheader("🌍 Generate a Grid")
        
        # Sınır belirleme yöntemi
        boundary_method = st.radio(
            "Boundary Definition Method:",
            ["Upload File (GeoJSON/SHP)", "Select Country"],
            key="boundary_method",
            horizontal=True
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            if boundary_method == "Upload File (GeoJSON/SHP)":
                boundary_file = st.file_uploader(
                    "Upload Boundary File",
                    type=['geojson', 'shp', 'gpkg'],
                    key="boundary_file"
                )
                
                if boundary_file:
                    try:
                        boundary_gdf = gpd.read_file(boundary_file)
                        st.success(f"✅ Uploaded: {len(boundary_gdf)} features")
                        st.map(boundary_gdf.to_crs("EPSG:4326"))
                        self.state.boundary_gdf = boundary_gdf
                    except Exception as e:
                        st.error(f"❌ File upload error: {e}")
            
            else:
                try:
                    @st.cache_data
                    def load_nuts_data(path):
                        gdf = gpd.read_file(path)
                        # NUTS 0 seviyesi ülkeleri filtrele
                        countries_only = gdf[gdf['LEVL_CODE'] == 0].copy()
                        return countries_only

                    world_countries = load_nuts_data(Config.NUTS_PATH)
                    
                    country_column = 'NAME_LATN' 
                    country_list = sorted(world_countries[country_column].unique())

                    selected_country_name = st.selectbox("Select a Country", country_list, key="country_select")

                    if selected_country_name:
                        # Seçilen ülkenin verisini filtrele
                        boundary_gdf = world_countries[world_countries[country_column] == selected_country_name]
                        
                        st.success(f"✅ Selected Country: {selected_country_name}")

                        # --- FOLIUM HARİTASI OLUŞTURMA ---
                        # Haritayı seçilen ülkenin merkezine odakla
                        centroid = boundary_gdf.to_crs(epsg=3857).centroid.to_crs(epsg=4326).iloc[0]
                        m = folium.Map(location=[centroid.y, centroid.x], zoom_start=5, tiles="CartoDB positron")

                        # Ülke sınırlarını haritaya ekle
                        folium.GeoJson(boundary_gdf).add_to(m)

                        # Haritayı Streamlit'te göster
                        st_folium(m, width=700, height=500)
                        # ---------------------------------
                        
                        # State'e kaydetme
                        self.state.boundary_gdf = boundary_gdf

                except Exception as e:
                    st.error(f"Error: {e}")
        
        with col2:
            st.markdown("**Grid Parameters**")
            
            grid_size_x = st.number_input(
                "Grid Width (meters)",
                min_value=100,
                max_value=10000,
                value=Config.DEFAULT_GRID_SIZE_X,
                step=100,
                key="grid_size_x"
            )
            
            grid_size_y = st.number_input(
                "Grid Height (meters)",
                min_value=100,
                max_value=10000,
                value=Config.DEFAULT_GRID_SIZE_Y,
                step=100,
                key="grid_size_y"
            )
        
        # Grid oluşturma butonu
        if st.button("Create Grid", type="primary", use_container_width=True):
            if not hasattr(self.state, 'boundary_gdf'):
                st.error("⚠️ Please define a boundary first (file or country)")
                return
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def progress_callback(pct, msg):
                progress_bar.progress(pct)
                status_text.text(msg)
            
            try:
                engine = FastGridEngine(self.state.boundary_gdf)
                grid_df = engine.create_rectangular_grid(
                    dx=grid_size_x,
                    dy=grid_size_y,
                    progress_callback=progress_callback
                )
                
                self.state.grid_df = grid_df
                self.state.grid_created = True
                
                st.success(f"✅ Grid successfully created: {len(grid_df):,} cells")
                st.dataframe(grid_df.head())
                
                csv = grid_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Grid CSV",
                    data=csv,
                    file_name="grid.csv",
                    mime="text/csv"
                )
                
            except Exception as e:
                st.error(f"❌ Grid creation error: {e}")
    
    def _render_grid_upload(self):
        """Upload existing CSV grid interface"""
        st.subheader("📤 Upload Existing Grid")
        
        uploaded_file = st.file_uploader(
            "Select Grid CSV File",
            type=['csv'],
            key="grid_csv_upload"
        )
        
        if uploaded_file:
            try:
                grid_df = pd.read_csv(uploaded_file)
                
                # Check for required columns
                required_cols = ['cell_id', 'wkt']
                missing_cols = [col for col in required_cols if col not in grid_df.columns]
                
                if missing_cols:
                    st.error(f"❌ Missing columns: {missing_cols}")
                    return
                
                self.state.grid_df = grid_df
                self.state.grid_created = True
                
                st.success(f"✅ Grid loaded: {len(grid_df):,} cells")
                st.dataframe(grid_df.head())
                
                # Preview on map
                try:
                    grid_df['geometry'] = grid_df['wkt'].apply(wkt.loads)
                    grid_gdf = gpd.GeoDataFrame(grid_df, geometry='geometry', crs='EPSG:3857')
                    st.map(grid_gdf.to_crs("EPSG:4326"))
                except:
                    pass
                
            except Exception as e:
                st.error(f"❌ CSV upload error: {e}")
    
    def validate(self):
        """Check if the grid is ready"""
        return hasattr(self.state, 'grid_created') and self.state.grid_created