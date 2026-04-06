"""
Configuration profile for On-Shore Wind Power Zoning.
Contains specific layers, modes, and scoring defaults for On-Shore Wind projects.
"""

class OnShoreConfig:
    PROJECT_TYPE = "OnShore"
    APP_TITLE = "On-Shore Wind Zoning Dashboard"
    THEME_COLOR = "dark_blue"
    ICON = "/Onshore.jpeg"
    
    # -------------------------------------------------------------------------
    # LAYER CONFIGURATION (Step 2)
    # -------------------------------------------------------------------------
    
    LAYER_CATEGORIES = {
        "Wind Resources": [
            "Wind"     
        ],
        "Infrastructure - Grid": [
            "110kV Lines",
            "220kV Lines",
            "400kV Lines",
            "110kV Substations",
            "220kV Substations",
            "400kV Substations"
        ],
        "Restrictions & Exclusion": [
            "Agriculture",
            "Airports",
            "Energy Sources",
            "Forest",
            "Hydrography",
            "Land Use",
            "Military Areas",
            "Mineral Resources",
            "Natural Risk Zones",
            "Protected Areas",
            
        ],
        "Terrain & Altitude": [
            "Slope (%)",
            "Altitude"
        ],
        "Access": [
            "Transport Networks"
        ]
    }

    PREDEFINED_LAYER_MODES = {
        
        
        
        "110kV Lines": ['distance'],
        "220kV Lines": ['distance'],
        "400kV Lines": ['distance'],

        "110kV Substations": ['distance'],
        "220kV Substations": ['distance'],
        "400kV Substations": ['distance'],
        
        "Altitude": ['max'],
        "Energy Sources": ['distance'],
        "Agriculture": ['distance', 'coverage'],
        "Forest": ['distance', 'coverage'],
        "Airports": ['distance'],
        "Hydrography": ['distance'],
        "Land Use": ['distance', 'coverage'],
        "Military Areas": ['distance'],
        "Mineral Resources": ['distance'],
        "Natural Risk Zones": ['distance'],
        "Protected Areas": ['distance'],
        
        "Slope (%)": ['max', 'mean', 'min'],
        "Transport Networks": ['distance'],
        "Wind": ['max', 'mean', 'min']
        
        
 
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
        # ── kV connection layers (Tab 4 weight defaults) ──────────────────
        '110kV Lines':       {'weight': 20, 'levels': [{'max': 10,    'min': 0.3, 'score': 100}, {'max': 15,    'min': 10,  'score': 70}, {'max': 20,    'min': 15,  'score': 40}, {'max': 99999, 'min': 20,  'score': 10}]},
        '220kV Lines':       {'weight': 20, 'levels': [{'max': 10,    'min': 0.3, 'score': 100}, {'max': 15,    'min': 10,  'score': 70}, {'max': 20,    'min': 15,  'score': 40}, {'max': 9999,  'min': 20,  'score': 10}]},
        '400kV Lines':       {'weight': 20, 'levels': [{'max': 5,     'min': 0.3, 'score': 100}, {'max': 10,    'min': 5,   'score': 70}, {'max': 15,    'min': 10,  'score': 40}, {'max': 99999, 'min': 15,  'score': 10}]},
        '110kV Substations': {'weight': 20, 'levels': [{'max': 10,    'min': 0.3, 'score': 100}, {'max': 20,    'min': 10,  'score': 70}, {'max': 30,    'min': 20,  'score': 40}, {'max': 99999, 'min': 30,  'score': 10}]},
        '220kV Substations': {'weight': 20, 'levels': [{'max': 10,    'min': 0.3, 'score': 100}, {'max': 20,    'min': 10,  'score': 70}, {'max': 40,    'min': 20,  'score': 40}, {'max': 9999,  'min': 40,  'score': 10}]},
        '400kV Substations': {'weight': 20, 'levels': [{'max': 15,    'min': 0.3, 'score': 100}, {'max': 30,    'min': 15,  'score': 70}, {'max': 50,    'min': 30,  'score': 40}, {'max': 99999, 'min': 50,  'score': 10}]},
        # ── Per-layer scoring defaults ─────────────────────────────────────
        'Agriculture': {
            'weight': 0.8,
            'levels': [
                {'max': 99999, 'min': 1,    'score': 100},
                {'max': 1,     'min': 0.5,  'score': 70},
                {'max': 0.5,   'min': 0.25, 'score': 40},
                {'max': 0.25,  'min': 0,    'score': 0},
            ]
        },
        'Airports': {
            'weight': 1,
            'levels': [
                {'max': 99999, 'min': 10, 'score': 100},
                {'max': 10,    'min': 8,  'score': 70},
                {'max': 8,     'min': 5,  'score': 40},
                {'max': 5,     'min': 0,  'score': 0},
            ]
        },
        'Altitude': {
            'weight': 15,
            'levels': [
                {'max': 500,   'min': 0,    'score': 100},
                {'max': 1500,  'min': 500,  'score': 70},
                {'max': 2000,  'min': 1500, 'score': 40},
                {'max': 99999, 'min': 2000, 'score': 0},
            ]
        },
        'Energy Sources': {
            'weight': 0.2,
            'levels': [
                {'max': 99999, 'min': 5,   'score': 100},
                {'max': 5,     'min': 2,   'score': 70},
                {'max': 2,     'min': 0.5, 'score': 40},
                {'max': 0.5,   'min': 0,   'score': 0},
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
            'weight': 2,
            'levels': [
                {'max': 99999, 'min': 0.5, 'score': 100},
                {'max': 0.5,   'min': 0.3, 'score': 70},
                {'max': 0.3,   'min': 0.1, 'score': 40},
                {'max': 0.1,   'min': 0,   'score': 0},
            ]
        },
        'Land Use': {
            'weight': 0.5,
            'levels': [
                {'max': 99999, 'min': 2,   'score': 100},
                {'max': 2,     'min': 1,   'score': 70},
                {'max': 1,     'min': 0.5, 'score': 40},
                {'max': 0.5,   'min': 0,   'score': 0},
            ]
        },
        'Military Areas': {
            'weight': 1,
            'levels': [
                {'max': 99999, 'min': 10, 'score': 100},
                {'max': 10,    'min': 5,  'score': 70},
                {'max': 5,     'min': 3,  'score': 40},
                {'max': 3,     'min': 0,  'score': 0},
            ]
        },
        'Mineral Resources': {
            'weight': 0.3,
            'levels': [
                {'max': 99999, 'min': 3,   'score': 100},
                {'max': 3,     'min': 2,   'score': 70},
                {'max': 2,     'min': 0.5, 'score': 40},
                {'max': 0.5,   'min': 0,   'score': 0},
            ]
        },
        'Natural Risk Zones': {
            'weight': 1,
            'levels': [
                {'max': 99999, 'min': 5, 'score': 100},
                {'max': 5,     'min': 4, 'score': 70},
                {'max': 4,     'min': 2, 'score': 40},
                {'max': 2,     'min': 0, 'score': 0},
            ]
        },
        'Protected Areas': {
            'weight': 0.2,
            'levels': [
                {'max': 99999, 'min': 5, 'score': 100},
                {'max': 5,     'min': 2, 'score': 70},
                {'max': 2,     'min': 1, 'score': 40},
                {'max': 1,     'min': 0, 'score': 0},
            ]
        },
        'Slope (%)': {
            'weight': 7,
            'levels': [
                {'max': 10,    'min': 0,  'score': 100},
                {'max': 20,    'min': 10, 'score': 70},
                {'max': 30,    'min': 20, 'score': 40},
                {'max': 99999, 'min': 30, 'score': 0},
            ]
        },
        'Transport Networks': {
            'weight': 10,
            'levels': [
                {'max': 10,    'min': 0.3, 'score': 100},
                {'max': 20,    'min': 10,  'score': 70},
                {'max': 40,    'min': 20,  'score': 40},
                {'max': 99999, 'min': 40,  'score': 0},
            ]
        },
        'Wind': {
            'weight': 40,
            'levels': [
                {'max': 99999, 'min': 7,   'score': 100},
                {'max': 7,     'min': 6,   'score': 70},
                {'max': 6,     'min': 5.5, 'score': 40},
                {'max': 5.5,   'min': 0,   'score': 0},
            ]
        },
    }

    # -------------------------------------------------------------------------
    # CLUSTER CONNECTION SCORING RULES (Step 4)
    # -------------------------------------------------------------------------

    CLUSTER_SCORING_RULES = [
        {"criteria_norm": "110kV Line", "weight_frac": 0.2,
         "cap_min": 30, "cap_max": 70,
         "L1_max": 10, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 15, "L2_min": 10, "L2_score": 70,
         "L3_max": 20, "L3_min": 15, "L3_score": 40,
         "L4_max": 99999, "L4_min": 20, "L4_score": 10,
         "kind": "Line", "kv": 110},
        {"criteria_norm": "220kV Line", "weight_frac": 0.2,
         "cap_min": 70, "cap_max": 180,
         "L1_max": 10, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 15, "L2_min": 10, "L2_score": 70,
         "L3_max": 20, "L3_min": 15, "L3_score": 40,
         "L4_max": 99999, "L4_min": 20, "L4_score": 10,
         "kind": "Line", "kv": 220},
        {"criteria_norm": "400kV Line", "weight_frac": 0.2,
         "cap_min": 180, "cap_max": 400,
         "L1_max": 5, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 10, "L2_min": 5, "L2_score": 70,
         "L3_max": 15, "L3_min": 10, "L3_score": 40,
         "L4_max": 99999, "L4_min": 15, "L4_score": 10,
         "kind": "Line", "kv": 400},
        {"criteria_norm": "110kV Substation", "weight_frac": 0.2,
         "cap_min": 30, "cap_max": 70,
         "L1_max": 10, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 20, "L2_min": 10, "L2_score": 70,
         "L3_max": 30, "L3_min": 20, "L3_score": 40,
         "L4_max": 99999, "L4_min": 30, "L4_score": 10,
         "kind": "Substation", "kv": 110},
        {"criteria_norm": "110kV Substation", "weight_frac": 0.2,
         "cap_min": 10, "cap_max": 30,
         "L1_max": 5, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 10, "L2_min": 5, "L2_score": 70,
         "L3_max": 15, "L3_min": 10, "L3_score": 40,
         "L4_max": 99999, "L4_min": 15, "L4_score": 10,
         "kind": "Substation", "kv": 110},
        {"criteria_norm": "220kV Substation", "weight_frac": 0.2,
         "cap_min": 70, "cap_max": 180,
         "L1_max": 10, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 20, "L2_min": 10, "L2_score": 70,
         "L3_max": 40, "L3_min": 20, "L3_score": 40,
         "L4_max": 99999, "L4_min": 40, "L4_score": 10,
         "kind": "Substation", "kv": 220},
        {"criteria_norm": "220kV Substation", "weight_frac": 0.2,
         "cap_min": 30, "cap_max": 70,
         "L1_max": 10, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 20, "L2_min": 10, "L2_score": 70,
         "L3_max": 30, "L3_min": 20, "L3_score": 40,
         "L4_max": 99999, "L4_min": 30, "L4_score": 10,
         "kind": "Substation", "kv": 220},
        {"criteria_norm": "220kV Substation", "weight_frac": 0.2,
         "cap_min": 10, "cap_max": 30,
         "L1_max": 5, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 10, "L2_min": 5, "L2_score": 70,
         "L3_max": 15, "L3_min": 10, "L3_score": 40,
         "L4_max": 99999, "L4_min": 15, "L4_score": 10,
         "kind": "Substation", "kv": 220},
        {"criteria_norm": "400kV Substation", "weight_frac": 0.2,
         "cap_min": 180, "cap_max": 400,
         "L1_max": 15, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 30, "L2_min": 15, "L2_score": 70,
         "L3_max": 50, "L3_min": 30, "L3_score": 40,
         "L4_max": 99999, "L4_min": 50, "L4_score": 10,
         "kind": "Substation", "kv": 400},
        {"criteria_norm": "400kV Substation", "weight_frac": 0.2,
         "cap_min": 70, "cap_max": 180,
         "L1_max": 10, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 20, "L2_min": 10, "L2_score": 70,
         "L3_max": 40, "L3_min": 20, "L3_score": 40,
         "L4_max": 99999, "L4_min": 40, "L4_score": 10,
         "kind": "Substation", "kv": 400},
        {"criteria_norm": "400kV Substation", "weight_frac": 0.2,
         "cap_min": 30, "cap_max": 70,
         "L1_max": 10, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 20, "L2_min": 10, "L2_score": 70,
         "L3_max": 30, "L3_min": 20, "L3_score": 40,
         "L4_max": 99999, "L4_min": 30, "L4_score": 10,
         "kind": "Substation", "kv": 400},
        {"criteria_norm": "400kV Substation", "weight_frac": 0.2,
         "cap_min": 10, "cap_max": 30,
         "L1_max": 5, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 10, "L2_min": 5, "L2_score": 70,
         "L3_max": 15, "L3_min": 10, "L3_score": 40,
         "L4_max": 99999, "L4_min": 15, "L4_score": 10,
         "kind": "Substation", "kv": 400},
    ]

