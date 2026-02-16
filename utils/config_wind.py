"""
Configuration profile for Wind Power Zoning.
Contains specific layers, modes, and scoring defaults for Wind projects.
"""

class WindConfig:
    PROJECT_TYPE = "Wind"
    APP_TITLE = "Wind Power Zoning Dashboard"
    THEME_COLOR = "blue"
    ICON = "🌬️"
    
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
            "Distance to Agriculture",
            "Distance to Airports",
            "Distance to Energy Sources",
            "Distance to Forest",
            "Distance to Hydrography",
            "Distance to Land Use",
            "Distance to Military Areas",
            "Distance to Mineral Resources",
            "Distance to Natural Risk Zones",
            "Distance to Protected Areas",
            
        ],
        "Terrain & Altitude": [
            "Slope (%)",
            "Altitude"
        ],
        "Access": [
            "Distance to Transport Networks"
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
        "Airport": ['distance'],
        "Hydrography": ['distance'],
        "Land Use": ['distance', 'coverage'],
        "Military Areas": ['distance'],
        "Mineral Resources": ['distance'],
        "Natural Risk Zones": ['distance'],
        "Protected Areas (Habitats)": ['distance'],
        
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
