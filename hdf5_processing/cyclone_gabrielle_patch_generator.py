import ee
import json
import os
import sys
import h5py
import numpy as np
from typing import Optional, Dict, List
import requests
from PIL import Image
from io import BytesIO
from hdf5_creator import *

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from gui.data_retrival import *


# Initialize Earth Engine
ee.Initialize(project="geog761-peag224")


def get_coordinates(geojson_path):
    with open(geojson_path, "r") as f:
        data = json.load(f)

    features = data.get("features", [])
    return features


# Example usage
if __name__ == "__main__":
    # Path to your annotations file
    geojson_path = r"aklshp\auckland_grid_5000m_wgs84.geojson"

    # date in 'YYYY-MM-DD' format
    start_date = "2023-02-15"
    end_date = "2023-04-15"

    # Load annotations
    features = get_coordinates(geojson_path)
    for i, feature in enumerate(features):
        if i <= 3:
            continue
        coordinates = feature["geometry"]["coordinates"][0]
        # feature = features[0]
        # coordinates = feature["geometry"]["coordinates"][0]
        # Convert GeoJSON geometry to Earth Engine geometry
        geometry = ee.Geometry.Polygon([coordinates])

        print(f"Processing period: {start_date} to {end_date}")
        print(f"Region type: {geometry.type().getInfo()}")
        print(f"Region bounds: {geometry.bounds().getInfo()}")

        # Get Sentinel-2 mosaic
        print("\nRetrieving Sentinel-2 data...")
        s_2_mosaic = get_s2_image(geometry, start_date, end_date, max_cloud_percent=50)

        print("\nRetrieving Sentinel-1 data...")
        s_1_mosiac = get_s1_image(geometry, start_date, end_date)

        print("\nTrying sampleRectangle method...")
        ee_images_to_hdf5(
            s1_image=s_1_mosiac,
            s2_image=s_2_mosaic,
            output_path=f"Training Data/cyclone_gabriella_patches/image_{i}.h5",
            region=geometry,
            scale=10,
            s1_bands=["VV"],
            s2_bands=[
                "B1",
                "B2",
                "B3",
                "B4",
                "B5",
                "B6",
                "B7",
                "B8",
                "B8A",
                "B9",
                "B11",
                "B12",
            ],
            use_export_method=False,  # Fallback method
        )
