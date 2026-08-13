"""
One-time setup script: downloads Natural Earth 110m admin-0 countries GeoJSON
and saves it to data/Country_Region_Data/world_admin0.geojson

Run from the project root:
    python setup_world_countries.py
"""

import json
import sys
import urllib.request
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "data" / "Country_Region_Data"
OUTPUT_FILE = OUTPUT_DIR / "world_admin0.geojson"

# Natural Earth 110m countries from the official GitHub mirror (same data geopandas shipped)
URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector"
    "/master/geojson/ne_110m_admin_0_countries.geojson"
)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if OUTPUT_FILE.exists():
        # Validate it is readable and non-empty
        try:
            with open(OUTPUT_FILE, encoding="utf-8") as f:
                data = json.load(f)
            names = [
                f["properties"].get("NAME") or f["properties"].get("name", "")
                for f in data.get("features", [])
            ]
            names = [n for n in names if n]
            print(f"world_admin0.geojson already exists with {len(names)} countries. Nothing to do.")
            return
        except Exception:
            print("Existing file is corrupt — re-downloading.")

    print(f"Downloading Natural Earth 110m countries from GitHub …")
    try:
        req = urllib.request.Request(
            URL,
            headers={"User-Agent": "Mozilla/5.0 (setup_world_countries.py)"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
    except Exception as e:
        print(f"Download failed: {e}")
        print("Please download manually:")
        print(f"  {URL}")
        print(f"  Save as: {OUTPUT_FILE}")
        sys.exit(1)

    # Parse and re-serialise to validate + normalise field name to NAME
    try:
        data = json.loads(raw)
    except Exception as e:
        print(f"JSON parse error: {e}")
        sys.exit(1)

    # Normalise: ensure every feature has a NAME property
    for feat in data.get("features", []):
        props = feat.get("properties", {})
        if "NAME" not in props:
            # Try common aliases
            for alias in ("name", "ADMIN", "NAME_EN", "ADM0_EN"):
                if alias in props and props[alias]:
                    props["NAME"] = props[alias]
                    break

    # Write
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

    names = sorted(
        {
            f["properties"].get("NAME", "")
            for f in data.get("features", [])
            if f["properties"].get("NAME")
        }
    )
    print(f"Saved {len(names)} countries to {OUTPUT_FILE}")
    print("\nCountry names loaded:")
    for n in names:
        print(f"  {n}")


if __name__ == "__main__":
    main()
