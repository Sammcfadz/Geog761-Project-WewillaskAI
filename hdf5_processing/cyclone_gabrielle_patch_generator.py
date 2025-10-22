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

# Example usage
if __name__ == "__main__":
    # Path to your annotations file

    # Convert GeoJSON geometry to Earth Engine geometry
    geometry = ee.Geometry(roi_geom)

    start_date = ""
    end_date = ""

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
        output_path="Training Data/manual_landslides/image_1.h5",
        region=geometry,
        scale=10,
        s1_bands=["VV"],
        s2_bands=["B2", "B3", "B4", "B8"],
        use_export_method=False,  # Fallback method
    )
