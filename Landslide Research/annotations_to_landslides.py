"""
Extract Sentinel-1 and Sentinel-2 data based on landslide annotations.

This script reads a GeoJSON file with landslide annotations and extracts
satellite data for the region of interest during the specified time period.
"""

import ee
import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from gui.data_retrival import *


# Initialize Earth Engine
ee.Initialize(project="geog761-peag224")


def load_annotations(geojson_path):
    """
    Load landslide annotations from GeoJSON file.

    Parameters:
    -----------
    geojson_path : str
        Path to the GeoJSON file

    Returns:
    --------
    dict : Dictionary containing metadata, ROI geometry, and landslide geometries
    """
    with open(geojson_path, "r") as f:
        data = json.load(f)

    metadata = data.get("metadata", {})
    features = data.get("features", [])

    # Extract ROI and landslides
    roi_geometry = None
    landslide_geometries = []

    for feature in features:
        props = feature.get("properties", {})
        geom = feature.get("geometry")

        if props.get("class") == "region_of_interest":
            roi_geometry = geom
        elif props.get("class") == "landslide":
            landslide_geometries.append(
                {"id": props.get("landslide_id"), "geometry": geom}
            )

    return {
        "metadata": metadata,
        "roi_geometry": roi_geometry,
        "landslide_geometries": landslide_geometries,
        "start_date": metadata.get("start_date"),
        "end_date": metadata.get("end_date"),
    }


# Example usage
if __name__ == "__main__":
    # Path to your annotations file
    geojson_path = r"Landslide Research/landslide_annotations.geojson"

    # Load annotations
    result = load_annotations(geojson_path)

    # Convert GeoJSON geometry to Earth Engine geometry
    roi_geom = result["roi_geometry"]
    geometry = ee.Geometry(roi_geom)

    # Extract dates
    start_date = result["start_date"]
    end_date = result["end_date"]

    # Get Sentinel-2 mosaic
    s_2_mosaic = get_s2_image(geometry, start_date, end_date, max_cloud_percent=20)

    s_1_mosiac = get_s1_image(geometry, start_date, end_date)

    print(f"Successfully created mosaic for ROI from {start_date} to {end_date}")
