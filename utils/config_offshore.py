"""
Configuration profile for Off-Shore Wind Power Zoning.
Contains specific layers, modes, and scoring defaults for Off-Shore Wind projects.
"""

class OffShoreConfig:
    PROJECT_TYPE = "OffShore"
    APP_TITLE = "Off-Shore Wind Zoning Dashboard"
    THEME_COLOR = "blue"
    ICON = "/Offshore.png"
    
    # -------------------------------------------------------------------------
    # LAYER CONFIGURATION (Step 2)
    # -------------------------------------------------------------------------
    
    LAYER_CATEGORIES = {
        "Wind Resources": [
            "Wind Speed (m/s) - bottom fixed",
            "Wind Speed (m/s) - floating"
        ],
    
        "Infrastructure & Logistics": [
            "Airport (km)",
            "Distance to Ports (km)",
            "Subsea Cables, pipe lines (km)",
            "220kV Lines",
            "400kV Lines",
            "220kV Substations",
            "400kV Substations"
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
            "Slope (%) - bottom fixed",
            "Slope (%) - floating"
        ]
    }

    PREDEFINED_LAYER_MODES = {
        
        "Airport (km)": ['distance'],
        "220kV Lines": ['distance'],
        "400kV Lines": ['distance'],
        "220kV Substations": ['distance'],
        "400kV Substations": ['distance'],
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
        "Slope (%) - bottom fixed": ['max', 'min', 'mean'],
        "Slope (%) - floating": ['max', 'min', 'mean'],
    }

    ALL_LAYER_NAMES = [
        layer for category in LAYER_CATEGORIES.values() 
        for layer in category
    ]

    # -------------------------------------------------------------------------
    # SCORING CONFIGURATION (Step 3)
    # -------------------------------------------------------------------------
    
    SCORING_CONFIGS = {
        # ── Generic fallbacks ──────────────────────────────────────────────
        'distance': {
            'levels': [
                {'max': 99999, 'min': 15, 'score': 100},
                {'max': 15,    'min': 10, 'score': 80},
                {'max': 10,    'min': 5,  'score': 50},
                {'max': 5,     'min': 0,  'score': 20},
            ]
        },
        'coverage': {
            'levels': [
                {'max': 100, 'min': 90, 'score': 0},
                {'max': 90,  'min': 50, 'score': 30},
                {'max': 50,  'min': 10, 'score': 80},
                {'max': 10,  'min': 0,  'score': 100},
            ]
        },
        'default': {
            'levels': [
                {'max': 99999, 'min': 80, 'score': 100},
                {'max': 80,    'min': 60, 'score': 80},
                {'max': 60,    'min': 40, 'score': 50},
                {'max': 40,    'min': 0,  'score': 20},
            ]
        },
        # ── Airport ────────────────────────────────────────────────────────
        'Airport (km)': {
            'weight': 1,
            'levels': [
                {'max': 99999, 'min': 30, 'score': 100},
                {'max': 30,    'min': 20, 'score': 70},
                {'max': 20,    'min': 10, 'score': 40},
                {'max': 10,    'min': 0,  'score': 0},
            ]
        },
        # ── kV connection layers (Tab 4 weight defaults) ──────────────────
        '220kV Lines':       {'weight': 25, 'levels': [{'max': 20,    'min': 0,  'score': 100}, {'max': 30,    'min': 20, 'score': 70}, {'max': 40,    'min': 30, 'score': 40}, {'max': 9999,  'min': 40, 'score': 10}]},
        '400kV Lines':       {'weight': 25, 'levels': [{'max': 20,    'min': 0,  'score': 100}, {'max': 40,    'min': 20, 'score': 70}, {'max': 60,    'min': 40, 'score': 40}, {'max': 99999, 'min': 60, 'score': 10}]},
        '220kV Substations': {'weight': 25, 'levels': [{'max': 20,    'min': 0,  'score': 100}, {'max': 30,    'min': 20, 'score': 70}, {'max': 40,    'min': 30, 'score': 40}, {'max': 9999,  'min': 40, 'score': 10}]},
        '400kV Substations': {'weight': 25, 'levels': [{'max': 20,    'min': 0,  'score': 100}, {'max': 30,    'min': 20, 'score': 70}, {'max': 40,    'min': 30, 'score': 40}, {'max': 99999, 'min': 40, 'score': 10}]},
        # ── Per-layer scoring defaults ─────────────────────────────────────
        'Bathymetry (for bottom fixed) (m)': {
            'weight': 10,
            'levels': [
                {'max': 20,    'min': 0,  'score': 100},
                {'max': 40,    'min': 20, 'score': 70},
                {'max': 60,    'min': 40, 'score': 40},
                {'max': 99999, 'min': 60, 'score': 0},
            ]
        },
        'Bathymetry (for floating) (m)': {
            'weight': 15,
            'levels': [
                {'max': 200,  'min': 60,   'score': 100},
                {'max': 500,  'min': 200,  'score': 70},
                {'max': 1000, 'min': 500,  'score': 40},
                {'max': 9999, 'min': 1000, 'score': 0},
            ]
        },
        'Distance to Ports (km)': {
            'weight': 2,
            'levels': [
                {'max': 75,    'min': 5,   'score': 100},
                {'max': 150,   'min': 75,  'score': 70},
                {'max': 250,   'min': 150, 'score': 40},
                {'max': 99999, 'min': 250, 'score': 0},
            ]
        },
        'Fishing areas (km)': {
            'weight': 0.2,
            'levels': [
                {'max': 99999, 'min': 5, 'score': 100},
                {'max': 5,     'min': 3, 'score': 70},
                {'max': 3,     'min': 1, 'score': 40},
                {'max': 1,     'min': 0, 'score': 0},
            ]
        },
        'Military Areas (km)': {
            'weight': 0.2,
            'levels': [
                {'max': 99999, 'min': 20, 'score': 100},
                {'max': 20,    'min': 15, 'score': 70},
                {'max': 15,    'min': 5,  'score': 40},
                {'max': 5,     'min': 0,  'score': 0},
            ]
        },
        'Natural Risk Zones (km)': {
            'weight': 1,
            'levels': [
                {'max': 99999, 'min': 5, 'score': 100},
                {'max': 5,     'min': 4, 'score': 70},
                {'max': 4,     'min': 2, 'score': 40},
                {'max': 2,     'min': 0, 'score': 0},
            ]
        },
        'Protected Areas (Habitats) (km)': {
            'weight': 0.2,
            'levels': [
                {'max': 99999, 'min': 4, 'score': 100},
                {'max': 4,     'min': 2, 'score': 70},
                {'max': 2,     'min': 1, 'score': 40},
                {'max': 1,     'min': 0, 'score': 0},
            ]
        },
        'Shipping': {
            'weight': 5,
            'levels': [
                {'max': 10,    'min': 0,   'score': 100},
                {'max': 50,    'min': 10,  'score': 70},
                {'max': 200,   'min': 50,  'score': 40},
                {'max': 99999, 'min': 200, 'score': 0},
            ]
        },
        'Slope (%) - bottom fixed': {
            'weight': 10,
            'levels': [
                {'max': 2,    'min': 0,  'score': 100},
                {'max': 5,    'min': 2,  'score': 70},
                {'max': 10,   'min': 5,  'score': 40},
                {'max': 9999, 'min': 10, 'score': 0},
            ]
        },
        'Slope (%) - floating': {
            'weight': 5,
            'levels': [
                {'max': 5,    'min': 0,  'score': 100},
                {'max': 10,   'min': 5,  'score': 70},
                {'max': 15,   'min': 10, 'score': 40},
                {'max': 9999, 'min': 15, 'score': 0},
            ]
        },
        'Subsea Cables (km)': {
            'weight': 0.2,
            'levels': [
                {'max': 99999, 'min': 2,   'score': 100},
                {'max': 2,     'min': 1,   'score': 70},
                {'max': 1,     'min': 0.5, 'score': 40},
                {'max': 0.5,   'min': 0,   'score': 0},
            ]
        },
        'Touristic Places (km)': {
            'weight': 0.2,
            'levels': [
                {'max': 99999, 'min': 30, 'score': 100},
                {'max': 30,    'min': 15, 'score': 70},
                {'max': 15,    'min': 5,  'score': 40},
                {'max': 5,     'min': 0,  'score': 0},
            ]
        },
        'Wind Speed (m/s) - bottom fixed': {
            'weight': 35,
            'levels': [
                {'max': 99999, 'min': 8.5, 'score': 100},
                {'max': 8.5,   'min': 8,   'score': 70},
                {'max': 8,     'min': 7.5, 'score': 40},
                {'max': 7.5,   'min': 0,   'score': 0},
            ]
        },
        'Wind Speed (m/s) - floating': {
            'weight': 35,
            'levels': [
                {'max': 99999, 'min': 8.5, 'score': 100},
                {'max': 8.5,   'min': 8,   'score': 70},
                {'max': 8,     'min': 7.5, 'score': 40},
                {'max': 7.5,   'min': 0,   'score': 0},
            ]
        },
    }

    # -------------------------------------------------------------------------
    # CLUSTER CONNECTION SCORING RULES (Step 4)
    # OffShore typically uses only 220kV and 400kV infrastructure
    # -------------------------------------------------------------------------

    CLUSTER_SCORING_RULES = [
        # 220kV Lines (cap 150–180 MW, shallow <60 m)
        {"criteria_norm": "220kV Line", "weight_frac": 0.25,
         "cap_min": 150, "cap_max": 180,
         "L1_max": 20,    "L1_min": 0,  "L1_score": 100,
         "L2_max": 30,    "L2_min": 20, "L2_score": 70,
         "L3_max": 40,    "L3_min": 30, "L3_score": 40,
         "L4_max": 9999,  "L4_min": 40, "L4_score": 10,
         "kind": "Line", "kv": 220},
        # 400kV Lines (cap 180–400 MW)
        {"criteria_norm": "400kV Line", "weight_frac": 0.25,
         "cap_min": 180, "cap_max": 400,
         "L1_max": 20,    "L1_min": 0,  "L1_score": 100,
         "L2_max": 40,    "L2_min": 20, "L2_score": 70,
         "L3_max": 60,    "L3_min": 40, "L3_score": 40,
         "L4_max": 99999, "L4_min": 60, "L4_score": 10,
         "kind": "Line", "kv": 400},
        # 220kV Substation (cap 150–180 MW, shallow <60 m)
        {"criteria_norm": "220kV Substation", "weight_frac": 0.25,
         "cap_min": 150, "cap_max": 180,
         "L1_max": 20,    "L1_min": 0,  "L1_score": 100,
         "L2_max": 30,    "L2_min": 20, "L2_score": 70,
         "L3_max": 40,    "L3_min": 30, "L3_score": 40,
         "L4_max": 9999,  "L4_min": 40, "L4_score": 10,
         "kind": "Substation", "kv": 220},
        # 400kV Substation (cap 150–180 MW, shallow <60 m)
        {"criteria_norm": "400kV Substation", "weight_frac": 0.25,
         "cap_min": 150, "cap_max": 180,
         "L1_max": 20,    "L1_min": 0,  "L1_score": 100,
         "L2_max": 30,    "L2_min": 20, "L2_score": 70,
         "L3_max": 40,    "L3_min": 30, "L3_score": 40,
         "L4_max": 99999, "L4_min": 40, "L4_score": 10,
         "kind": "Substation", "kv": 400},
        # 400kV Substation (cap 180–400 MW)
        {"criteria_norm": "400kV Substation", "weight_frac": 0.25,
         "cap_min": 180, "cap_max": 400,
         "L1_max": 20,    "L1_min": 0,  "L1_score": 100,
         "L2_max": 40,    "L2_min": 20, "L2_score": 70,
         "L3_max": 60,    "L3_min": 40, "L3_score": 40,
         "L4_max": 99999, "L4_min": 60, "L4_score": 10,
         "kind": "Substation", "kv": 400},
    ]

