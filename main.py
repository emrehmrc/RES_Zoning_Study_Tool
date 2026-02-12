"""
Main application entry point
"""
import streamlit as st
from config import Config
from ui.tab_gridization import GridizationTab
from ui.tab_scoring import ScoringTab
from ui.tab_level_scoring import LevelScoringTab

def initialize_session_state():
    """Initialize all session state variables"""
    
    # Core flags
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
    
    if 'grid_created' not in st.session_state:
        st.session_state.grid_created = False
    
    if 'scoring_complete' not in st.session_state:
        st.session_state.scoring_complete = False
    
    # Grid data
    if 'grid_df' not in st.session_state:
        st.session_state.grid_df = None
    
    if 'boundary_gdf' not in st.session_state:
        st.session_state.boundary_gdf = None
    
    # Layer configurations
    if 'layer_configs' not in st.session_state:
        st.session_state.layer_configs = []
    
    # Results
    if 'scoring_results' not in st.session_state:
        st.session_state.scoring_results = None


def main():
    # Page configuration
    st.set_page_config(
        page_title=Config.APP_NAME,
        page_icon="🌞",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state ONCE
    initialize_session_state()
    
    # Ensure directories exist
    Config.ensure_directories()
    
    # Header
    st.title(f"🌞 {Config.APP_NAME}")
    st.markdown(f"*Version {Config.VERSION}*")
    st.markdown("---")
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["1. Gridization", "2. Layer Calculation", "3. Scoring"])
    
    # Initialize tab objects
    gridization_tab = GridizationTab(st.session_state)
    scoring_tab = ScoringTab(st.session_state)
    level_scoring_tab = LevelScoringTab(st.session_state)
    
    # Render tabs
    with tab1:
        gridization_tab.render()
    
    with tab2:
        scoring_tab.render()

    with tab3:
        level_scoring_tab.render()
    
    # Sidebar status
    with st.sidebar:
        st.header("📊 Status")
        
        # Grid status
        if st.session_state.grid_created and st.session_state.grid_df is not None:
            st.success("✅ Grid Ready")
            st.metric("Grid Cells", f"{len(st.session_state.grid_df):,}")
            
            # Show grid info
            with st.expander("ℹ️ Grid Info"):
                st.write(f"**Columns:** {', '.join(st.session_state.grid_df.columns.tolist())}")
        else:
            st.warning("⏳ Grid Not Created")
        
        st.markdown("---")
        
        # Layer configurations status
        if st.session_state.layer_configs:
            st.success(f"✅ {len(st.session_state.layer_configs)} Layer(s) Configured")
            with st.expander("📋 Configured Layers"):
                for config in st.session_state.layer_configs:
                    st.write(f"• **{config['prefix']}**")
        else:
            st.info("⏳ No Layers Configured")
        
        st.markdown("---")
        
        # Analysis status
        if st.session_state.scoring_complete and st.session_state.scoring_results is not None:
            st.success("✅ Analysis Complete")
            st.metric("Processed Cells", f"{len(st.session_state.scoring_results):,}")
        else:
            st.info("⏳ Analysis Pending")
        
        st.markdown("---")
        
        # Reset button
        if st.button("🔄 Reset All", type="secondary", use_container_width=True):
            # Clear all session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


if __name__ == "__main__":
    main()