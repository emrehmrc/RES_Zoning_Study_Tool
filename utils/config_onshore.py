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
            "Distance to 110kV Lines",
            "Distance to 220kV Lines",
            "Distance to 400kV Lines",
            "Distance to 110kV Substations",
            "Distance to 220kV Substations",
            "Distance to 400kV Substations"
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
        
        
        
        "Distance to 110kV Lines": ['distance'],
        "Distance to 220kV Lines": ['distance'],
        "Distance to 400kV Lines": ['distance'],

        "Distance to 110kV Substations": ['distance'],
        "Distance to 220kV Substations": ['distance'],
        "Distance to 400kV Substations": ['distance'],
        
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
    # -------------------------------------------------------------------------

    CLUSTER_SCORING_RULES = [
        {"criteria_norm": "Distance to 110kV Line", "weight_frac": 0.2,
         "cap_min": 30, "cap_max": 70,
         "L1_max": 10, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 15, "L2_min": 10, "L2_score": 70,
         "L3_max": 20, "L3_min": 15, "L3_score": 40,
         "L4_max": 99999, "L4_min": 20, "L4_score": 10,
         "kind": "Line", "kv": 110},
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
        {"criteria_norm": "Distance to 110kV Substation", "weight_frac": 0.2,
         "cap_min": 30, "cap_max": 70,
         "L1_max": 10, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 20, "L2_min": 10, "L2_score": 70,
         "L3_max": 30, "L3_min": 20, "L3_score": 40,
         "L4_max": 99999, "L4_min": 30, "L4_score": 10,
         "kind": "Substation", "kv": 110},
        {"criteria_norm": "Distance to 110kV Substation", "weight_frac": 0.2,
         "cap_min": 10, "cap_max": 30,
         "L1_max": 5, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 10, "L2_min": 5, "L2_score": 70,
         "L3_max": 15, "L3_min": 10, "L3_score": 40,
         "L4_max": 99999, "L4_min": 15, "L4_score": 10,
         "kind": "Substation", "kv": 110},
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
        {"criteria_norm": "Distance to 220kV Substation", "weight_frac": 0.2,
         "cap_min": 10, "cap_max": 30,
         "L1_max": 5, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 10, "L2_min": 5, "L2_score": 70,
         "L3_max": 15, "L3_min": 10, "L3_score": 40,
         "L4_max": 99999, "L4_min": 15, "L4_score": 10,
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
        {"criteria_norm": "Distance to 400kV Substation", "weight_frac": 0.2,
         "cap_min": 10, "cap_max": 30,
         "L1_max": 5, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 10, "L2_min": 5, "L2_score": 70,
         "L3_max": 15, "L3_min": 10, "L3_score": 40,
         "L4_max": 99999, "L4_min": 15, "L4_score": 10,
         "kind": "Substation", "kv": 400},
    ]

