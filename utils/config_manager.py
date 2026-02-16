"""
Configuration Manager
Handles loading of specific project configurations (Solar/Wind).
"""
import streamlit as st
from utils.config_solar import SolarConfig
from utils.config_onshore import OnShoreConfig
from utils.config_offshore import OffShoreConfig

class ConfigManager:
    @staticmethod
    def get_config(project_type):
        """
        Factory method to return the correct configuration class based on project type.
        """
        # DEBUG LOGGING
        try:
            with open("debug_log.txt", "a") as f:
                f.write(f"DEBUG: ConfigManager.get_config received '{project_type}' (type: {type(project_type)})\n")
        except:
            pass
            
        if project_type == "Solar":
            return SolarConfig
        elif project_type == "OnShore":
            return OnShoreConfig
        elif project_type == "OffShore":
            return OffShoreConfig
        else:
            # Default to Solar if something goes wrong
            return SolarConfig

    @staticmethod
    def get_active_config():
        """
        Helper to get the currently active config from session state.
        """
        if 'project_type' in st.session_state:
            return ConfigManager.get_config(st.session_state.project_type)
        return None
