"""
Configuration Manager
Handles loading of specific project configurations (Solar/Wind).
"""
from utils.config_solar import SolarConfig
from utils.config_onshore import OnShoreConfig
from utils.config_offshore import OffShoreConfig

class ConfigManager:
    @staticmethod
    def get_config(project_type):
        """
        Factory method to return the correct configuration class based on project type.
        """
        if project_type == "Solar":
            return SolarConfig
        elif project_type == "OnShore":
            return OnShoreConfig
        elif project_type == "OffShore":
            return OffShoreConfig
        else:
            return SolarConfig
