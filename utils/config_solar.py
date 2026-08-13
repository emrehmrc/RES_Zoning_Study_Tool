"""
Configuration profile for Solar PV Zoning.
Contains specific layers, modes, and scoring defaults for Solar projects.
"""
from copy import deepcopy
from pathlib import Path


SOLAR_SENSITIVITY_FILE = Path(
    r"C:\Users\Emre Hangul\MRC\MRC - 1.1.3_T&SI"
    r"\MRC2025-171_Syria_Renewable_Master_Plan\06_FREE WORK AREA"
    r"\Goktug\Zoning Study\Sensitivity Values\GES_Zoning_FINAL_sensitivity_yeni.xlsx"
)

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
        "Demand": [
            "Proximity to Load Centers"
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
            "Dust Concentration",
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
        "Proximity to Load Centers": ['distance'],
        "Energy Sources": ['distance'],
        "Forest": ['distance', 'coverage'],
        "Hydrography": ['distance'],
        "Land Use (Urban, Residential, Industrial)": ['distance', 'coverage'],
        "Military Areas": ['distance'],
        "Mineral Resources": ['distance'],
        "Natural Risk Zones": ['distance'],
        "Protected Areas (Habitats)": ['distance'],
        "Dust Concentration": ['mean', 'min', 'max'],
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
        '110kV Lines':       {'weight': 15, 'levels': [{'max': 10,    'min': 0.3, 'score': 100}, {'max': 20,    'min': 10,  'score': 70}, {'max': 30,    'min': 20,  'score': 40}, {'max': 99999, 'min': 30,  'score': 0}]},
        '220kV Lines':       {'weight': 15, 'levels': [{'max': 10,    'min': 0.3, 'score': 100}, {'max': 15,    'min': 10,  'score': 70}, {'max': 20,    'min': 15,  'score': 40}, {'max': 30,    'min': 20,  'score': 10}, {'max': 999999, 'min': 30, 'score': 0}]},
        '400kV Lines':       {'weight': 15, 'levels': [{'max': 10,    'min': 0.3, 'score': 100}, {'max': 15,    'min': 10,  'score': 70}, {'max': 20,    'min': 15,  'score': 40}, {'max': 30,    'min': 20,  'score': 10}, {'max': 999999, 'min': 30, 'score': 0}]},
        '110kV Substations': {'weight': 15, 'levels': [{'max': 10,    'min': 0.3, 'score': 100}, {'max': 20,    'min': 10,  'score': 70}, {'max': 30,    'min': 20,  'score': 40}, {'max': 99999, 'min': 30,  'score': 0}]},
        '220kV Substations': {'weight': 15, 'levels': [{'max': 10,    'min': 0.3, 'score': 100}, {'max': 15,    'min': 10,  'score': 70}, {'max': 20,    'min': 15,  'score': 40}, {'max': 50,    'min': 20,  'score': 10}, {'max': 999999, 'min': 50, 'score': 0}]},
        '400kV Substations': {'weight': 15, 'levels': [{'max': 10,    'min': 0.3, 'score': 100}, {'max': 15,    'min': 10,  'score': 70}, {'max': 30,    'min': 15,  'score': 40}, {'max': 50,    'min': 30,  'score': 10}, {'max': 999999, 'min': 50, 'score': 0}]},
        # ── Per-layer scoring defaults ─────────────────────────────────────
        'Agricultural Areas': {
            'weight': 1,
            'max_coverage_threshold': 0,
            'levels': [
                {'max': 99999, 'min': 1, 'score': 100},
                {'max': 1,     'min': 0, 'score': 0},
            ]
        },
        'Energy Sources': {
            'weight': 1,
            'levels': [
                {'max': 99999, 'min': 1,    'score': 100},
                {'max': 1,     'min': 0,    'score': 0},
            ]
        },
        'Forest': {
            'weight': 1,
            'levels': [
                {'max': 99999, 'min': 1, 'score': 100},
                {'max': 1,     'min': 0, 'score': 0},
            ]
        },
        'Hydrography': {
            'weight': 1,
            'levels': [
                {'max': 99999, 'min': 1, 'score': 100},
                {'max': 1,     'min': 0, 'score': 0},
            ]
        },
        'Land Use (Urban, Residential, Industrial)': {
            'weight': 3,
            'max_coverage_threshold': 0,
            'levels': [
                {'max': 99999, 'min': 2, 'score': 100},
                {'max': 2,     'min': 0, 'score': 0},
            ]
        },
        'Military Areas': {
            'weight': 1,
            'levels': [
                {'max': 99999, 'min': 3, 'score': 100},
                {'max': 3,     'min': 0, 'score': 0},
            ]
        },
        'Mineral Resources': {
            'weight': 0.2,
            'levels': [
                {'max': 99999, 'min': 1, 'score': 100},
                {'max': 1,     'min': 0, 'score': 0},
            ]
        },
        'Natural Risk Zones': {
            'weight': 0.3,
            'levels': [
                {'max': 99999, 'min': 1, 'score': 100},
                {'max': 1,     'min': 0, 'score': 0},
            ]
        },
        'Protected Areas (Habitats)': {
            'weight': 1,
            'levels': [
                {'max': 99999, 'min': 2, 'score': 100},
                {'max': 2,     'min': 0, 'score': 0},
            ]
        },
        'Dust Concentration': {
            'weight': 4,
            'levels': [
                {'max': 0.2, 'min': 0,   'score': 100},
                {'max': 0.35, 'min': 0.2, 'score': 70},
                {'max': 0.5, 'min': 0.3, 'score': 40},
                {'max': 1,   'min': 0.5, 'score': 0},
            ]
        },
        'Proximity to Load Centers': {
            'weight': 10,
            'levels': [
                {'max': 20,     'min': 0,   'score': 100},
                {'max': 30,     'min': 20,  'score': 70},
                {'max': 100,    'min': 30,  'score': 40},
                {'max': 999999, 'min': 100, 'score': 0},
            ]
        },
        'Slope (%)': {
            'weight': 8,
            'levels': [
                {'max': 5,     'min': 0,  'score': 100},
                {'max': 10,    'min': 5,  'score': 70},
                {'max': 15,    'min': 10, 'score': 40},
                {'max': 99999, 'min': 15, 'score': 0},
            ]
        },
        'Solar Irradiation (kWh/m²)': {
            'weight': 30,
            # Workbook levels use the annual 2917 kWh/m² peak, not the
            # maximum value found in a particular uploaded raster.
            'normalization_peak': 2917,
            'levels': [
                {'max': 1,    'min': 0.9,  'score': 100},
                {'max': 0.9,  'min': 0.75, 'score': 70},
                {'max': 0.75, 'min': 0.65, 'score': 40},
                {'max': 0.65, 'min': 0,    'score': 0},
            ]
        },
        'Temperature (°C)': {
            'weight': 23,
            'levels': [
                {'max': 15, 'min': 0,  'score': 100},
                {'max': 20, 'min': 15, 'score': 70},
                {'max': 25, 'min': 20, 'score': 40},
                {'max': 99, 'min': 25, 'score': 0},
            ]
        },
        'Transport Networks': {
            'weight': 0.5,
            'levels': [
                {'max': 2,     'min': 0.25, 'score': 100},
                {'max': 10,    'min': 2,    'score': 70},
                {'max': 30,    'min': 10,   'score': 40},
                {'max': 99999, 'min': 30,   'score': 0},
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
        {"criteria_norm": "110kV Line", "weight_frac": 0.15,
         "cap_min": 30, "cap_max": 70,
         "L1_max": 10, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 20, "L2_min": 10, "L2_score": 70,
         "L3_max": 30, "L3_min": 20, "L3_score": 40,
         "L4_max": 99999, "L4_min": 30, "L4_score": 0,
         "kind": "Line", "kv": 110},
        # 220kV Lines (cap 70-180 MW)
        {"criteria_norm": "220kV Line", "weight_frac": 0.15,
         "cap_min": 70, "cap_max": 180,
         "L1_max": 10, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 15, "L2_min": 10, "L2_score": 70,
         "L3_max": 20, "L3_min": 15, "L3_score": 40,
         "L4_max": 30, "L4_min": 20, "L4_score": 10,
         "L5_max": 999999, "L5_min": 30, "L5_score": 0,
         "kind": "Line", "kv": 220},
        # 400kV Lines (cap 180-400 MW)
        {"criteria_norm": "400kV Line", "weight_frac": 0.15,
         "cap_min": 180, "cap_max": 400,
         "L1_max": 10, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 15, "L2_min": 10, "L2_score": 70,
         "L3_max": 20, "L3_min": 15, "L3_score": 40,
         "L4_max": 30, "L4_min": 20, "L4_score": 10,
         "L5_max": 999999, "L5_min": 30, "L5_score": 0,
         "kind": "Line", "kv": 400},
        # 110kV Substation (cap 30-70 MW)
        {"criteria_norm": "110kV Substation", "weight_frac": 0.15,
         "cap_min": 30, "cap_max": 70,
         "L1_max": 10, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 20, "L2_min": 10, "L2_score": 70,
         "L3_max": 30, "L3_min": 20, "L3_score": 40,
         "L4_max": 99999, "L4_min": 30, "L4_score": 0,
         "kind": "Substation", "kv": 110},
        # 110kV Substation (cap 10-30 MW)
        {"criteria_norm": "110kV Substation", "weight_frac": 0.15,
         "cap_min": 10, "cap_max": 30,
         "L1_max": 5, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 10, "L2_min": 5, "L2_score": 70,
         "L3_max": 15, "L3_min": 10, "L3_score": 40,
         "L4_max": 99999, "L4_min": 15, "L4_score": 0,
         "kind": "Substation", "kv": 110},
        # 220kV Substation (cap 70-180 MW)
        {"criteria_norm": "220kV Substation", "weight_frac": 0.15,
         "cap_min": 70, "cap_max": 180,
         "L1_max": 10, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 15, "L2_min": 10, "L2_score": 70,
         "L3_max": 20, "L3_min": 15, "L3_score": 40,
         "L4_max": 50, "L4_min": 20, "L4_score": 10,
         "L5_max": 999999, "L5_min": 50, "L5_score": 0,
         "kind": "Substation", "kv": 220},
        # 220kV Substation (cap 30-70 MW)
        {"criteria_norm": "220kV Substation", "weight_frac": 0.15,
         "cap_min": 30, "cap_max": 70,
         "L1_max": 10, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 15, "L2_min": 10, "L2_score": 70,
         "L3_max": 30, "L3_min": 15, "L3_score": 40,
         "L4_max": 999999, "L4_min": 30, "L4_score": 0,
         "kind": "Substation", "kv": 220},
        # 220kV Substation (cap 10-30 MW)
        {"criteria_norm": "220kV Substation", "weight_frac": 0.15,
         "cap_min": 10, "cap_max": 30,
         "L1_max": 5, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 10, "L2_min": 5, "L2_score": 70,
         "L3_max": 15, "L3_min": 10, "L3_score": 40,
         "L4_max": 999999, "L4_min": 20, "L4_score": 0,
         "kind": "Substation", "kv": 220},
        # 400kV Substation (cap 180-400 MW)
        {"criteria_norm": "400kV Substation", "weight_frac": 0.15,
         "cap_min": 180, "cap_max": 400,
         "L1_max": 10, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 15, "L2_min": 10, "L2_score": 70,
         "L3_max": 30, "L3_min": 15, "L3_score": 40,
         "L4_max": 50, "L4_min": 30, "L4_score": 10,
         "L5_max": 999999, "L5_min": 50, "L5_score": 0,
         "kind": "Substation", "kv": 400},
        # 400kV Substation (cap 70-180 MW)
        {"criteria_norm": "400kV Substation", "weight_frac": 0.15,
         "cap_min": 70, "cap_max": 180,
         "L1_max": 10, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 15, "L2_min": 10, "L2_score": 70,
         "L3_max": 20, "L3_min": 15, "L3_score": 40,
         "L4_max": 50, "L4_min": 20, "L4_score": 10,
         "L5_max": 999999, "L5_min": 50, "L5_score": 0,
         "kind": "Substation", "kv": 400},
        # 400kV Substation (cap 30-70 MW)
        {"criteria_norm": "400kV Substation", "weight_frac": 0.15,
         "cap_min": 30, "cap_max": 70,
         "L1_max": 10, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 15, "L2_min": 10, "L2_score": 70,
         "L3_max": 30, "L3_min": 15, "L3_score": 40,
         "L4_max": 999999, "L4_min": 30, "L4_score": 0,
         "kind": "Substation", "kv": 400},
        # 400kV Substation (cap 10-30 MW)
        {"criteria_norm": "400kV Substation", "weight_frac": 0.15,
         "cap_min": 10, "cap_max": 30,
         "L1_max": 5, "L1_min": 0.3, "L1_score": 100,
         "L2_max": 10, "L2_min": 5, "L2_score": 70,
         "L3_max": 20, "L3_min": 10, "L3_score": 40,
         "L4_max": 999999, "L4_min": 20, "L4_score": 0,
         "kind": "Substation", "kv": 400},
    ]


def _to_float(value):
    try:
        if value != value:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _levels_from_sensitivity_row(row):
    levels = []
    for max_col, min_col, score_col in ((7, 8, 9), (10, 11, 12), (13, 14, 15), (16, 17, 18)):
        max_val = _to_float(row.iloc[max_col])
        min_val = _to_float(row.iloc[min_col])
        score = _to_float(row.iloc[score_col])
        if max_val is None or min_val is None or score is None:
            continue
        levels.append({"max": max_val, "min": min_val, "score": score})
    return levels


def _weight_from_sensitivity_row(row):
    weight = _to_float(row.iloc[3])
    if weight is None:
        return None
    return weight * 100 if weight <= 1 else weight


def _sensitivity_config(row, *, extra=None):
    levels = _levels_from_sensitivity_row(row)
    if not levels:
        return None

    cfg = {"levels": levels}
    weight = _weight_from_sensitivity_row(row)
    if weight is not None:
        cfg["weight"] = weight

    validity_threshold = _to_float(row.iloc[5])
    if validity_threshold is not None:
        cfg["max_coverage_threshold"] = validity_threshold

    if extra:
        cfg.update(extra)
    return cfg


def _apply_solar_sensitivity_values():
    if not SOLAR_SENSITIVITY_FILE.exists():
        return

    try:
        import pandas as pd

        df = pd.read_excel(SOLAR_SENSITIVITY_FILE, sheet_name="Sensitivity_Values", header=None)
    except Exception:
        return

    configs = deepcopy(SolarConfig.SCORING_CONFIGS)

    row_map = {
        "Agricultural Areas": 2,
        "66kV Lines": 3,
        "110kV Lines": 3,
        "66kV Substations": 4,
        "110kV Substations": 4,
        "220kV Lines": 6,
        "220kV Substations": 7,
        "400kV Lines": 10,
        "400kV Substations": 11,
        "Dust Concentration": 15,
        "Energy Sources": 16,
        "Forest": 17,
        "Hydrography": 18,
        "Land Use (Urban, Residential, Industrial)": 19,
        "Military Areas": 20,
        "Mineral Resources": 21,
        "Natural Risk Zones": 22,
        "Protected Areas (Habitats)": 23,
        "Proximity to Load Centers": 24,
        "Slope (%)": 25,
        "Solar Irradiation (kWh/m²)": 26,
        "Solar Irradiation (kWh/mÂ²)": 26,
        "Temperature (°C)": 27,
        "Temperature (Â°C)": 27,
        "Transport Networks": 28,
    }

    extras = {
        "Solar Irradiation (kWh/m²)": {"normalization_peak": 2917},
        "Solar Irradiation (kWh/mÂ²)": {"normalization_peak": 2917},
    }

    for layer_name, row_idx in row_map.items():
        if row_idx >= len(df):
            continue
        cfg = _sensitivity_config(df.iloc[row_idx], extra=extras.get(layer_name))
        if cfg:
            configs[layer_name] = cfg

    SolarConfig.SCORING_CONFIGS = configs

    for layer_name in ("66kV Lines", "66kV Substations"):
        if layer_name not in SolarConfig.PREDEFINED_LAYER_MODES:
            SolarConfig.PREDEFINED_LAYER_MODES[layer_name] = ["distance"]

    infra_lines = SolarConfig.LAYER_CATEGORIES.get("Infrastructure - Transmission Lines", [])
    if "66kV Lines" not in infra_lines:
        infra_lines.insert(0, "66kV Lines")

    infra_substations = SolarConfig.LAYER_CATEGORIES.get("Infrastructure - Substations", [])
    if "66kV Substations" not in infra_substations:
        infra_substations.insert(0, "66kV Substations")

    SolarConfig.ALL_LAYER_NAMES = [
        layer
        for category in SolarConfig.LAYER_CATEGORIES.values()
        for layer in category
    ]


_apply_solar_sensitivity_values()
