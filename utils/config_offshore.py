"""
Configuration profile for Off-Shore Wind Power Zoning.
Contains specific layers, modes, and scoring defaults for Off-Shore Wind projects.
"""

class OffShoreConfig:
    PROJECT_TYPE = "OffShore"
    APP_TITLE = "Off-Shore Wind Zoning Dashboard"
    THEME_COLOR = "blue"
    ICON = "🌊"
    
    # -------------------------------------------------------------------------
    # LAYER CONFIGURATION (Step 2)
    # -------------------------------------------------------------------------
    
    LAYER_CATEGORIES = {
        "Wind Resources": [
            "Wind Speed (m/s) - bottom fixed",
            "Wind Speed (m/s) - floating"
        ],
        "Infrastructure & Logistics": [
            "Distance to Ports (km)",
            "Subsea Cables, pipe lines (km)"
        ],
        "Restrictions & Exclusion": [
            "Fishing areas (km)",
            "Military Areas (km)",
            "Natural Risk Zones (km)",
            "Protected Areas (Habitats) (km)",
            "Shipping (Route Density: count/year/km2)",
            "Touristic Places (km)"
        ],
        "Marine & Terrain": [
            "Sea bed (only for bottom fixed)",
            "Slope of the Bottom of Sea (for bottom fixed) (%)",
            "Slope of the Bottom of Sea (for floating) (%)"
        ]
    }

    PREDEFINED_LAYER_MODES = {
        "Distance to Ports (km)": ['min'],
        "Fishing areas (km)": ['max'],
        "Military Areas (km)": ['max'],
        "Natural Risk Zones (km)": ['min'],
        "Protected Areas (Habitats) (km)": ['min'],
        "Sea bed (only for bottom fixed)": ['min'],
        "Shipping (Route Density: count/year/km2)": ['min'],
        "Slope of the Bottom of Sea (for bottom fixed) (%)": ['min'],
        "Slope of the Bottom of Sea (for floating) (%)": ['min'],
        "Subsea Cables, pipe lines (km)": ['max'],
        "Touristic Places (km)": ['mean'],
        "Wind Speed (m/s) - bottom fixed": ['max', 'min', 'mean'],
        "Wind Speed (m/s) - floating": ['max', 'min', 'mean']
    }

    ALL_LAYER_NAMES = [
        layer for category in LAYER_CATEGORIES.values() 
        for layer in category
    ]

    # -------------------------------------------------------------------------
    # SCORING CONFIGURATION (Step 3)
    # -------------------------------------------------------------------------
    
    SCORING_CONFIGS = {
        'distance': {
            'levels': [
                {'max': 99999, 'min': 15, 'score': 100},
                {'max': 15, 'min': 10, 'score': 80},
                {'max': 10, 'min': 5, 'score': 50},
                {'max': 5, 'min': 0, 'score': 20}
            ]
        },
        'coverage': {
            'levels': [
                {'max': 100, 'min': 90, 'score': 0},
                {'max': 90, 'min': 50, 'score': 30},
                {'max': 50, 'min': 10, 'score': 80},
                {'max': 10, 'min': 0, 'score': 100}
            ]
        },
        'slope': {
            # Wind turbines need flatter terrain for installation, but ridges can be good for wind
            'levels': [
                {'max': 10, 'min': 0, 'score': 100},
                {'max': 15, 'min': 10, 'score': 80},
                {'max': 25, 'min': 15, 'score': 40},
                {'max': 99999, 'min': 25, 'score': 0}
            ]
        },
        'wind_speed': {
            'levels': [
                {'max': 999, 'min': 8.5, 'score': 100},
                {'max': 8.5, 'min': 7.5, 'score': 80},
                {'max': 7.5, 'min': 6.0, 'score': 50},
                {'max': 6.0, 'min': 0, 'score': 0}
            ]
        },
        'default': {
            'levels': [
                {'max': 99999, 'min': 80, 'score': 100},
                {'max': 80, 'min': 60, 'score': 80},
                {'max': 60, 'min': 40, 'score': 50},
                {'max': 40, 'min': 0, 'score': 20}
            ]
        }
    }
