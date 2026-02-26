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
            "Subsea Cables, pipe lines (km)",
            "Distance to 220kV Lines",
            "Distance to 400kV Lines",
            "Distance to 220kV Substations",
            "Distance to 400kV Substations"
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
            "Bathymetry (for bottom fixed) (m)",
            "Bathymetry (for floating) (m)",
            "Slope (%)"
        ]
    }

    PREDEFINED_LAYER_MODES = {
        
        "Distance to 220kV Lines": ['distance'],
        "Distance to 400kV Lines": ['distance'],
        "Distance to 220kV Substations": ['distance'],
        "Distance to 400kV Substations": ['distance'],
        "Distance to Ports (km)": ['distance'],
        "Fishing areas (km)": ['distance'],
        "Military Areas (km)": ['distance'],
        "Natural Risk Zones (km)": ['distance'],
        "Protected Areas (Habitats) (km)": ['distance'],
        "Sea bed": ['min'],
        "Shipping": ['distance'],
        "Bathymetry (for bottom fixed) (m)": ['max'],
        "Bathymetry (for floating) (m)": ['max'],
        "Subsea Cables (km)": ['distance'],
        "Touristic Places (km)": ['distance'],
        "Wind Speed (m/s) - bottom fixed": ['max', 'min', 'mean'],
        "Wind Speed (m/s) - floating": ['max', 'min', 'mean'],
        "Slope (%)": ['max', 'mean', 'min']
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

    # -------------------------------------------------------------------------
    # CLUSTER CONNECTION SCORING RULES (Step 4)
    # OffShore typically uses only 220kV and 400kV infrastructure
    # -------------------------------------------------------------------------

    CLUSTER_SCORING_RULES = [
        {"criteria_norm": "Distance to 220kV Line", "weight_frac": 0.2,
         "cap_min": 70, "cap_max": 180,
         "L1_max": 10, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 15, "L2_min": 10, "L2_score": 70,
         "L3_max": 20, "L3_min": 15, "L3_score": 40,
         "L4_max": 99999, "L4_min": 20, "L4_score": 10,
         "kind": "Line", "kv": 220},
        {"criteria_norm": "Distance to 400kV Line", "weight_frac": 0.2,
         "cap_min": 180, "cap_max": 400,
         "L1_max": 5, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 10, "L2_min": 5, "L2_score": 70,
         "L3_max": 15, "L3_min": 10, "L3_score": 40,
         "L4_max": 99999, "L4_min": 15, "L4_score": 10,
         "kind": "Line", "kv": 400},
        {"criteria_norm": "Distance to 220kV Substation", "weight_frac": 0.2,
         "cap_min": 70, "cap_max": 180,
         "L1_max": 10, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 20, "L2_min": 10, "L2_score": 70,
         "L3_max": 40, "L3_min": 20, "L3_score": 40,
         "L4_max": 99999, "L4_min": 40, "L4_score": 10,
         "kind": "Substation", "kv": 220},
        {"criteria_norm": "Distance to 220kV Substation", "weight_frac": 0.2,
         "cap_min": 30, "cap_max": 70,
         "L1_max": 10, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 20, "L2_min": 10, "L2_score": 70,
         "L3_max": 30, "L3_min": 20, "L3_score": 40,
         "L4_max": 99999, "L4_min": 30, "L4_score": 10,
         "kind": "Substation", "kv": 220},
        {"criteria_norm": "Distance to 400kV Substation", "weight_frac": 0.2,
         "cap_min": 180, "cap_max": 400,
         "L1_max": 15, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 30, "L2_min": 15, "L2_score": 70,
         "L3_max": 50, "L3_min": 30, "L3_score": 40,
         "L4_max": 99999, "L4_min": 50, "L4_score": 10,
         "kind": "Substation", "kv": 400},
        {"criteria_norm": "Distance to 400kV Substation", "weight_frac": 0.2,
         "cap_min": 70, "cap_max": 180,
         "L1_max": 10, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 20, "L2_min": 10, "L2_score": 70,
         "L3_max": 40, "L3_min": 20, "L3_score": 40,
         "L4_max": 99999, "L4_min": 40, "L4_score": 10,
         "kind": "Substation", "kv": 400},
        {"criteria_norm": "Distance to 400kV Substation", "weight_frac": 0.2,
         "cap_min": 30, "cap_max": 70,
         "L1_max": 10, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 20, "L2_min": 10, "L2_score": 70,
         "L3_max": 30, "L3_min": 20, "L3_score": 40,
         "L4_max": 99999, "L4_min": 30, "L4_score": 10,
         "kind": "Substation", "kv": 400},
    ]

