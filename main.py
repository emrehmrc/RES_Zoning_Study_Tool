"""
Main application entry point - Grid & Scoring Dashboard
supports multiple project types (Solar/Wind) via Configuration Manager.
"""
import streamlit as st
import time
from config import Config
from utils.config_manager import ConfigManager
from ui.tab_gridization import GridizationTab
from ui.tab_scoring import ScoringTab
from ui.tab_level_scoring import LevelScoringTab

def initialize_session_state():
    """Initialize all session state variables"""
    
    # Core flags
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
    
    if 'project_type' not in st.session_state:
        st.session_state.project_type = None  # None, 'Solar', 'Wind'
    
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


def render_landing_page():
    """Renders the initial project selection screen."""
    st.markdown(
        """
        <style>
        .project-card {
            padding: 2rem;
            border-radius: 10px;
            border: 1px solid #ddd;
            text-align: center;
            transition: transform 0.2s;
            cursor: pointer;
            height: 100%;
        }
        .project-card:hover {
            transform: scale(1.02);
            border-color: #aaa;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        /* Solar Mode Button (Column 1) */
        div[data-testid="column"]:nth-of-type(1) button[kind="primary"] {
            background-color: #FF9F1C;
            border-color: #FF9F1C;
            color: white;
        }
        div[data-testid="column"]:nth-of-type(1) button[kind="primary"]:hover {
            background-color: #CC7A00;
            border-color: #CC7A00;
        }

        /* On-Shore Mode Button (Column 2) */
        div[data-testid="column"]:nth-of-type(2) button[kind="primary"] {
            background-color: #00008B;
            border-color: #00008B;
            color: white;
        }
        div[data-testid="column"]:nth-of-type(2) button[kind="primary"]:hover {
            background-color: #000060;
            border-color: #000060;
        }

        /* Off-Shore Mode Button (Column 3) */
        div[data-testid="column"]:nth-of-type(3) button[kind="primary"] {
            background-color: #1E90FF;
            border-color: #1E90FF;
            color: white;
        }
        div[data-testid="column"]:nth-of-type(3) button[kind="primary"]:hover {
            background-color: #104E8B;
            border-color: #104E8B;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.title("🌍 Renewable Energy Zoning Dashboard")
    st.markdown("### Select Project Mode")
    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    with col1:
        with st.container(border=True):
            st.markdown("## ☀️ Solar PV Project")
            st.markdown("Analysis for Photovoltaic Power Plants")
            st.markdown("- Solar Irradiation Analysis")
            st.markdown("- Slope & Terrain Constraints")
            st.markdown("- Proximity to Transmission Lines")
            st.markdown("\n")
            if st.button("Select Solar Mode", type="primary", use_container_width=True, key="btn_solar"):
                st.session_state.project_type = "Solar"
                st.rerun()

    with col2:
        with st.container(border=True):
            st.markdown("## 🌬️ On-Shore Wind")
            st.markdown("Analysis for On-Shore Wind Zoning")
            st.markdown("- Wind Speed & Density Analysis")
            st.markdown("- Turbine Constraints")
            st.markdown("- Environmental Exclusions")
            st.markdown("\n")
            if st.button("Select On-Shore Mode", type="primary", use_container_width=True, key="btn_onshore"):
                st.session_state.project_type = "OnShore"
                st.rerun()
                
    with col3:
        with st.container(border=True):
            st.markdown("## 🌊 Off-Shore Wind")
            st.markdown("Analysis for Off-Shore Wind Zoning")
            st.markdown("- Wind Speed & Density Analysis")
            st.markdown("- Exclusive Economic Zones")
            st.markdown("- Marine Constraints")
            st.markdown("\n")
            if st.button("Select Off-Shore Mode", type="primary", use_container_width=True, key="btn_offshore"):
                st.session_state.project_type = "OffShore"
                st.rerun()

    st.markdown("---")
    st.info("ℹ️ Select a mode to load specific analysis layers and scoring criteria.")


def main():
    # Initialize session state ONCE (before page config mostly, but some needs to persist)
    initialize_session_state()

    # Determine theme/title based on selection (or default)
    project_type = st.session_state.project_type
    
    if project_type == "Solar":
        page_title = "Solar PV Zoning Dashboard"
        page_icon = "☀️"
    elif project_type == "OnShore":
        page_title = "On-Shore Wind Zoning Dashboard"
        page_icon = "🌬️"
    elif project_type == "OffShore":
        page_title = "Off-Shore Wind Zoning Dashboard"
        page_icon = "🌊"
    else:
        page_title = Config.APP_NAME
        page_icon = "🌍"

    # Page configuration
    st.set_page_config(
        page_title=page_title,
        page_icon=page_icon,
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # DEBUG
    with open("debug_log.txt", "a") as f:
        f.write(f"DEBUG: project_type = {st.session_state.get('project_type')}\n")
    
    # Ensure directories exist
    Config.ensure_directories()
    
    # Logic: If no project selected, show Landing Page
    if project_type is None:
        render_landing_page()
        return

    # --- MAIN DASHBOARD (Only executes if project_type is set) ---
    
    # Get active config
    app_config = ConfigManager.get_active_config()
    
    # DEBUG
    with open("debug_log.txt", "a") as f:
        f.write(f"DEBUG: Config Title = {app_config.APP_TITLE}\n")
    
    # Color bar based on theme
    color = app_config.THEME_COLOR if hasattr(app_config, 'THEME_COLOR') else "gray"
    if color == "orange":
        st.markdown("""<div style='background-color: #ff9f1c; height: 5px; width: 100%; margin-bottom: 10px;'></div>""", unsafe_allow_html=True)
    elif color == "blue":
        st.markdown("""<div style='background-color: #2ec4b6; height: 5px; width: 100%; margin-bottom: 10px;'></div>""", unsafe_allow_html=True)
    elif color == "dark_blue":
        st.markdown("""<div style='background-color: #00008B; height: 5px; width: 100%; margin-bottom: 10px;'></div>""", unsafe_allow_html=True)

    # Header with Project Context
    col_head1, col_head2 = st.columns([3, 1])
    with col_head1:
        st.title(f"{app_config.ICON} {app_config.APP_TITLE}")
    with col_head2:
        st.markdown(f"**Current Mode:** {project_type}")
        if st.button("🔄 Switch Mode", type="secondary", use_container_width=True):
            st.session_state.project_type = None
            # Optional: Clear other state if switching modes?
            # For now, let's keep grid but maybe clear layers if incompatible. 
            # Ideally user should reset if changing mode entirely to avoid layer confusion.
            st.session_state.layer_configs = []
            st.session_state.scoring_results = None
            st.session_state.scoring_complete = False
            st.rerun()

    st.markdown("---")
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["1. Gridization", "2. Layer Calculation", "3. Scoring"])
    
    # Initialize tab objects - PASS Config to them!
    gridization_tab = GridizationTab(st.session_state)
    scoring_tab = ScoringTab(st.session_state, app_config)
    level_scoring_tab = LevelScoringTab(st.session_state, app_config)
    
    # Render tabs
    with tab1:
        gridization_tab.render()
    
    with tab2:
        scoring_tab.render()

    with tab3:
        level_scoring_tab.render()
    
    # Sidebar status
    with st.sidebar:
        st.header(f"📊 {project_type} Status")
        
        # Grid status
        if st.session_state.grid_created and st.session_state.grid_df is not None:
            st.success("✅ Grid Ready")
            st.metric("Grid Cells", f"{len(st.session_state.grid_df):,}")
            
            # Show grid info
            with st.expander("ℹ️ Grid Info"):
                if hasattr(st.session_state.grid_df, 'columns'):
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
        if st.button("🗑️ Reset Current Project", type="primary", use_container_width=True):
            # Clear all session state except project type maybe? 
            # Or assume full reset. 
            # Let's keep project type for convenience, but clear data.
            current_type = st.session_state.project_type
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            
            st.session_state.project_type = current_type # Restore project type
            st.session_state.initialized = True
            st.rerun()


if __name__ == "__main__":
    main()
