"""
Configuration profile for Solar PV Zoning.
Contains specific layers, modes, and scoring defaults for Solar projects.
"""

class SolarConfig:
    PROJECT_TYPE = "Solar"
    APP_TITLE = "Solar PV Zoning Dashboard"
    THEME_COLOR = "orange"  # Streamlit primary color or theme hint
    ICON = "☀️"
    
    # -------------------------------------------------------------------------
    # LAYER CONFIGURATION (Step 2)
    # -------------------------------------------------------------------------
    
    LAYER_CATEGORIES = {
        "Infrastructure - Transmission Lines": [
            "Distance to 110kV Lines",
            "Distance to 220kV Lines",
            "Distance to 400kV Lines"
        ],
        "Infrastructure - Substations": [
            "Distance to 110kV Substations",
            "Distance to 220kV Substations",
            "Distance to 400kV Substations"
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
        "Distance to 110kV Lines": ['distance'],
        "Distance to 220kV Lines": ['distance'],
        "Distance to 400kV Lines": ['distance'],
        "Distance to 110kV Substations": ['distance'],
        "Distance to 220kV Substations": ['distance'],
        "Distance to 400kV Substations": ['distance'],
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
        'distance': {
            'levels': [
                {'max': 99999, 'min': 10, 'score': 100},
                {'max': 10, 'min': 5, 'score': 70},
                {'max': 5, 'min': 2, 'score': 40},
                {'max': 2, 'min': 0, 'score': 10}
            ]
        },
        'coverage': {
            'levels': [
                {'max': 100, 'min': 80, 'score': 10},
                {'max': 80, 'min': 50, 'score': 40},
                {'max': 50, 'min': 20, 'score': 70},
                {'max': 20, 'min': 0, 'score': 100}
            ]
        },
        'slope': {
            'levels': [
                {'max': 5, 'min': 0, 'score': 100},
                {'max': 10, 'min': 5, 'score': 70},
                {'max': 20, 'min': 10, 'score': 40},
                {'max': 99999, 'min': 20, 'score': 10}
            ]
        },
        'solar': {
            'levels': [
                {'max': 99999, 'min': 1800, 'score': 100},
                {'max': 1800, 'min': 1600, 'score': 70},
                {'max': 1600, 'min': 1400, 'score': 40},
                {'max': 1400, 'min': 0, 'score': 10}
            ]
        },
        'default': {
            'levels': [
                {'max': 99999, 'min': 75, 'score': 100},
                {'max': 75, 'min': 50, 'score': 70},
                {'max': 50, 'min': 25, 'score': 40},
                {'max': 25, 'min': 0, 'score': 10}
            ]
        }
    }
