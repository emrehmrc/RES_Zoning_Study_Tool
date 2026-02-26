import os
from pathlib import Path

class Config:
    APP_NAME = "GIS Grid & Scoring Dashboard"
    VERSION = "2.0.0"
    
    BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
    OUTPUT_DIR = BASE_DIR / "outputs"
    DATA_DIR = BASE_DIR / "data"
    TEMP_DIR = BASE_DIR / "temp"

    # Default path for NUTS data
    NUTS_PATH = r"C:\Users\boray.guvenc\OneDrive - MRC\Masaüstü\yedek_final_final\Dashboard\Input\NUTS_RG_01M_2021_4326.geojson"

    # Default path for EEZ (Exclusive Economic Zone) data - used for Off-Shore mode
    EEZ_PATH = BASE_DIR / "Off_shore_shapes" / "EEZ_Europe.shp"

    # Grid Varsayılanları (Eksik olan kısım)
    DEFAULT_GRID_SIZE_X = 1000
    DEFAULT_GRID_SIZE_Y = 1000

    # Scoring Engine Defaults
    DEFAULT_CHUNK_SIZE = 5000
    DEFAULT_N_WORKERS = 4

    @classmethod
    def ensure_directories(cls):
        """Gerekli klasörlerin var olduğundan emin olur."""
        for directory in [cls.OUTPUT_DIR, cls.DATA_DIR, cls.TEMP_DIR]:
            directory.mkdir(parents=True, exist_ok=True)