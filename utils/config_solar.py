"""
Configuration profile for Solar PV Zoning.
Contains specific layers, modes, and scoring defaults for Solar projects.
"""

class SolarConfig:
    PROJECT_TYPE = "Solar"
    APP_TITLE = "Solar PV Zoning Dashboard"
    THEME_COLOR = "orange"  # Streamlit primary color or theme hint
    ICON = "/Solar.png"
    
    # -------------------------------------------------------------------------
    # LAYER CONFIGURATION (Step 2)
    # -------------------------------------------------------------------------
    
    LAYER_CATEGORIES = {
        "Infrastructure - Transmission Lines": [
            "110kV Lines",
            "220kV Lines",
            "400kV Lines"
        ],
        "Infrastructure - Substations": [
            "110kV Substations",
            "220kV Substations",
            "400kV Substations"
        ],
        "Land Use & Environment": [
            "Agricultural Areas",
            "Forest",
            "Land Use (Urban, Residential, Industrial)",
            "Military Areas",
            "Protected Areas (Habitats)"
        ],
        "Natural Resources": [
            "Energy Sources",
            "Hydrography",
            "Mineral Resources"
        ],
        "Risk & Climate": [
            "Natural Risk Zones",
            "Slope (%)",
            "Solar Irradiation (kWh/m²)",
            "Temperature (°C)"
        ],
        "Transportation": [
            "Transport Networks"
        ]
    }

    PREDEFINED_LAYER_MODES = {
        "Agricultural Areas": ['distance', 'coverage'],
        "110kV Lines": ['distance'],
        "220kV Lines": ['distance'],
        "400kV Lines": ['distance'],
        "110kV Substations": ['distance'],
        "220kV Substations": ['distance'],
        "400kV Substations": ['distance'],
        "Energy Sources": ['distance'],
        "Forest": ['distance', 'coverage'],
        "Hydrography": ['distance'],
        "Land Use (Urban, Residential, Industrial)": ['distance', 'coverage'],
        "Military Areas": ['distance'],
        "Mineral Resources": ['distance'],
        "Natural Risk Zones": ['distance'],
        "Protected Areas (Habitats)": ['distance'],
        "Slope (%)": ['min', 'max', 'mean'],
        "Solar Irradiation (kWh/m²)": ['min', 'max', 'mean'],
        "Temperature (°C)": ['min', 'max', 'mean'],
        "Transport Networks": ['distance']
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
                {'max': 99999, 'min': 10, 'score': 100},
                {'max': 10,    'min': 5,  'score': 70},
                {'max': 5,     'min': 2,  'score': 40},
                {'max': 2,     'min': 0,  'score': 10},
            ]
        },
        'coverage': {
            'levels': [
                {'max': 100, 'min': 80, 'score': 10},
                {'max': 80,  'min': 50, 'score': 40},
                {'max': 50,  'min': 20, 'score': 70},
                {'max': 20,  'min': 0,  'score': 100},
            ]
        },
        'default': {
            'levels': [
                {'max': 99999, 'min': 75, 'score': 100},
                {'max': 75,    'min': 50, 'score': 70},
                {'max': 50,    'min': 25, 'score': 40},
                {'max': 25,    'min': 0,  'score': 10},
            ]
        },
        # ── kV connection layers (Tab 4 weight defaults) ──────────────────
        '110kV Lines':       {'weight': 20, 'levels': [{'max': 10,    'min': 0.3, 'score': 100}, {'max': 15,    'min': 10,  'score': 70}, {'max': 20,    'min': 15,  'score': 40}, {'max': 99999, 'min': 20,  'score': 10}]},
        '220kV Lines':       {'weight': 20, 'levels': [{'max': 10,    'min': 0.3, 'score': 100}, {'max': 15,    'min': 10,  'score': 70}, {'max': 20,    'min': 15,  'score': 40}, {'max': 99999, 'min': 20,  'score': 10}]},
        '400kV Lines':       {'weight': 20, 'levels': [{'max': 5,     'min': 0.3, 'score': 100}, {'max': 10,    'min': 5,   'score': 70}, {'max': 15,    'min': 10,  'score': 40}, {'max': 99999, 'min': 15,  'score': 10}]},
        '110kV Substations': {'weight': 20, 'levels': [{'max': 10,    'min': 0.3, 'score': 100}, {'max': 20,    'min': 10,  'score': 70}, {'max': 30,    'min': 20,  'score': 40}, {'max': 99999, 'min': 30,  'score': 10}]},
        '220kV Substations': {'weight': 20, 'levels': [{'max': 10,    'min': 0.3, 'score': 100}, {'max': 20,    'min': 10,  'score': 70}, {'max': 40,    'min': 20,  'score': 40}, {'max': 99999, 'min': 40,  'score': 10}]},
        '400kV Substations': {'weight': 20, 'levels': [{'max': 15,    'min': 0.3, 'score': 100}, {'max': 30,    'min': 15,  'score': 70}, {'max': 50,    'min': 30,  'score': 40}, {'max': 99999, 'min': 50,  'score': 10}]},
        # ── Per-layer scoring defaults ─────────────────────────────────────
        'Agricultural Areas': {
            'weight': 1,
            'levels': [
                {'max': 99999, 'min': 0.5,  'score': 100},
                {'max': 0.5,   'min': 0.3,  'score': 70},
                {'max': 0.3,   'min': 0.01, 'score': 40},
                {'max': 0.01,  'min': 0,    'score': 0},
            ]
        },
        'Energy Sources': {
            'weight': 0.2,
            'levels': [
                {'max': 99999, 'min': 1,    'score': 100},
                {'max': 1,     'min': 0.5,  'score': 70},
                {'max': 0.5,   'min': 0.25, 'score': 40},
                {'max': 0.25,  'min': 0,    'score': 0},
            ]
        },
        'Forest': {
            'weight': 1,
            'levels': [
                {'max': 99999, 'min': 5,   'score': 100},
                {'max': 5,     'min': 3,   'score': 70},
                {'max': 3,     'min': 0.3, 'score': 40},
                {'max': 0.3,   'min': 0,   'score': 0},
            ]
        },
        'Hydrography': {
            'weight': 0.2,
            'levels': [
                {'max': 99999, 'min': 0.3,  'score': 100},
                {'max': 0.3,   'min': 0.15, 'score': 70},
                {'max': 0.15,  'min': 0.05, 'score': 40},
                {'max': 0.05,  'min': 0,    'score': 0},
            ]
        },
        'Land Use (Urban, Residential, Industrial)': {
            'weight': 3,
            'levels': [
                {'max': 99999, 'min': 1,   'score': 100},
                {'max': 1,     'min': 0.5, 'score': 70},
                {'max': 0.5,   'min': 0.3, 'score': 40},
                {'max': 0.3,   'min': 0,   'score': 0},
            ]
        },
        'Military Areas': {
            'weight': 0.2,
            'levels': [
                {'max': 99999, 'min': 10, 'score': 100},
                {'max': 10,    'min': 5,  'score': 70},
                {'max': 5,     'min': 2,  'score': 40},
                {'max': 2,     'min': 0,  'score': 0},
            ]
        },
        'Mineral Resources': {
            'weight': 0.2,
            'levels': [
                {'max': 99999, 'min': 0.5,  'score': 100},
                {'max': 0.5,   'min': 0.25, 'score': 70},
                {'max': 0.25,  'min': 0.01, 'score': 40},
                {'max': 0.01,  'min': 0,    'score': 0},
            ]
        },
        'Natural Risk Zones': {
            'weight': 0.5,
            'levels': [
                {'max': 99999, 'min': 3, 'score': 100},
                {'max': 3,     'min': 2, 'score': 70},
                {'max': 2,     'min': 1, 'score': 40},
                {'max': 1,     'min': 0, 'score': 0},
            ]
        },
        'Protected Areas (Habitats)': {
            'weight': 0.2,
            'levels': [
                {'max': 99999, 'min': 3, 'score': 100},
                {'max': 3,     'min': 2, 'score': 70},
                {'max': 2,     'min': 1, 'score': 40},
                {'max': 1,     'min': 0, 'score': 0},
            ]
        },
        'Slope (%)': {
            'weight': 9,
            'levels': [
                {'max': 5,     'min': 0,  'score': 100},
                {'max': 10,    'min': 5,  'score': 70},
                {'max': 15,    'min': 10, 'score': 40},
                {'max': 99999, 'min': 15, 'score': 0},
            ]
        },
        'Solar Irradiation (kWh/m²)': {
            'weight': 50,
            'levels': [
                {'max': 100, 'min': 85, 'score': 100},
                {'max': 85,  'min': 75, 'score': 70},
                {'max': 75,  'min': 65, 'score': 40},
                {'max': 65,  'min': 0,  'score': 0},
            ]
        },
        'Temperature (°C)': {
            'weight': 14,
            'levels': [
                {'max': 20, 'min': 10, 'score': 100},
                {'max': 25, 'min': 20, 'score': 70},
                {'max': 30, 'min': 25, 'score': 40},
                {'max': 99, 'min': 30, 'score': 0},
            ]
        },
        'Transport Networks': {
            'weight': 0.5,
            'levels': [
                {'max': 2,     'min': 0.25, 'score': 100},
                {'max': 10,    'min': 2,    'score': 70},
                {'max': 40,    'min': 10,   'score': 40},
                {'max': 99999, 'min': 40,   'score': 0},
            ]
        },
    }

    # -------------------------------------------------------------------------
    # CLUSTER CONNECTION SCORING RULES (Step 4)
    # Defines distance-based scoring rules for transmission infrastructure.
    # Each rule: criteria, weight, capacity range, 4 scoring levels, kind, kV
    # -------------------------------------------------------------------------

    CLUSTER_SCORING_RULES = [
        # 110kV Lines (cap 30-70 MW)
        {"criteria_norm": "110kV Line", "weight_frac": 0.2,
         "cap_min": 30, "cap_max": 70,
         "L1_max": 10, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 15, "L2_min": 10, "L2_score": 70,
         "L3_max": 20, "L3_min": 15, "L3_score": 40,
         "L4_max": 99999, "L4_min": 20, "L4_score": 10,
         "kind": "Line", "kv": 110},
        # 220kV Lines (cap 70-180 MW)
        {"criteria_norm": "220kV Line", "weight_frac": 0.2,
         "cap_min": 70, "cap_max": 180,
         "L1_max": 10, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 15, "L2_min": 10, "L2_score": 70,
         "L3_max": 20, "L3_min": 15, "L3_score": 40,
         "L4_max": 99999, "L4_min": 20, "L4_score": 10,
         "kind": "Line", "kv": 220},
        # 400kV Lines (cap 180-400 MW)
        {"criteria_norm": "400kV Line", "weight_frac": 0.2,
         "cap_min": 180, "cap_max": 400,
         "L1_max": 5, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 10, "L2_min": 5, "L2_score": 70,
         "L3_max": 15, "L3_min": 10, "L3_score": 40,
         "L4_max": 99999, "L4_min": 15, "L4_score": 10,
         "kind": "Line", "kv": 400},
        # 110kV Substation (cap 30-70 MW)
        {"criteria_norm": "110kV Substation", "weight_frac": 0.2,
         "cap_min": 30, "cap_max": 70,
         "L1_max": 10, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 20, "L2_min": 10, "L2_score": 70,
         "L3_max": 30, "L3_min": 20, "L3_score": 40,
         "L4_max": 99999, "L4_min": 30, "L4_score": 10,
         "kind": "Substation", "kv": 110},
        # 110kV Substation (cap 10-30 MW)
        {"criteria_norm": "110kV Substation", "weight_frac": 0.2,
         "cap_min": 10, "cap_max": 30,
         "L1_max": 5, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 10, "L2_min": 5, "L2_score": 70,
         "L3_max": 15, "L3_min": 10, "L3_score": 40,
         "L4_max": 99999, "L4_min": 15, "L4_score": 10,
         "kind": "Substation", "kv": 110},
        # 220kV Substation (cap 70-180 MW)
        {"criteria_norm": "220kV Substation", "weight_frac": 0.2,
         "cap_min": 70, "cap_max": 180,
         "L1_max": 10, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 20, "L2_min": 10, "L2_score": 70,
         "L3_max": 40, "L3_min": 20, "L3_score": 40,
         "L4_max": 99999, "L4_min": 40, "L4_score": 10,
         "kind": "Substation", "kv": 220},
        # 220kV Substation (cap 30-70 MW)
        {"criteria_norm": "220kV Substation", "weight_frac": 0.2,
         "cap_min": 30, "cap_max": 70,
         "L1_max": 10, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 20, "L2_min": 10, "L2_score": 70,
         "L3_max": 30, "L3_min": 20, "L3_score": 40,
         "L4_max": 99999, "L4_min": 30, "L4_score": 10,
         "kind": "Substation", "kv": 220},
        # 220kV Substation (cap 10-30 MW)
        {"criteria_norm": "220kV Substation", "weight_frac": 0.2,
         "cap_min": 10, "cap_max": 30,
         "L1_max": 5, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 10, "L2_min": 5, "L2_score": 70,
         "L3_max": 15, "L3_min": 10, "L3_score": 40,
         "L4_max": 99999, "L4_min": 15, "L4_score": 10,
         "kind": "Substation", "kv": 220},
        # 400kV Substation (cap 180-400 MW)
        {"criteria_norm": "400kV Substation", "weight_frac": 0.2,
         "cap_min": 180, "cap_max": 400,
         "L1_max": 15, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 30, "L2_min": 15, "L2_score": 70,
         "L3_max": 50, "L3_min": 30, "L3_score": 40,
         "L4_max": 99999, "L4_min": 50, "L4_score": 10,
         "kind": "Substation", "kv": 400},
        # 400kV Substation (cap 70-180 MW)
        {"criteria_norm": "400kV Substation", "weight_frac": 0.2,
         "cap_min": 70, "cap_max": 180,
         "L1_max": 10, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 20, "L2_min": 10, "L2_score": 70,
         "L3_max": 40, "L3_min": 20, "L3_score": 40,
         "L4_max": 99999, "L4_min": 40, "L4_score": 10,
         "kind": "Substation", "kv": 400},
        # 400kV Substation (cap 30-70 MW)
        {"criteria_norm": "400kV Substation", "weight_frac": 0.2,
         "cap_min": 30, "cap_max": 70,
         "L1_max": 10, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 20, "L2_min": 10, "L2_score": 70,
         "L3_max": 30, "L3_min": 20, "L3_score": 40,
         "L4_max": 99999, "L4_min": 30, "L4_score": 10,
         "kind": "Substation", "kv": 400},
        # 400kV Substation (cap 10-30 MW)
        {"criteria_norm": "400kV Substation", "weight_frac": 0.2,
         "cap_min": 10, "cap_max": 30,
         "L1_max": 5, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 10, "L2_min": 5, "L2_score": 70,
         "L3_max": 15, "L3_min": 10, "L3_score": 40,
         "L4_max": 99999, "L4_min": 15, "L4_score": 10,
         "kind": "Substation", "kv": 400},
    ]
