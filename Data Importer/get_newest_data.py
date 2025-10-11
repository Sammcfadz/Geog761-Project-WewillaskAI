import ee
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd

AUCKLAND_GEOMETRY = ee.Geometry.Rectangle([174.5, -37.0, 175.3, -36.6])


# Initialize Earth Engine (you need to authenticate first)
ee.Authenticate()
user = "Peter"
if user == "Peter":
    ee.Initialize(project="geog761-peag224")
elif user == "Someone":
    pass
else:
    print("MUST INTIALISE PLEASE ADD YOUR INITIALISATION")
    # PLEASE ADD YOUR INITIALISATIONS IN AN ELIF

# Auckland area of interest


def get_most_recent_sentinel2_auckland_ee(
    geometry: ee.geometry = AUCKLAND_GEOMETRY,
    days_back: int = 30,
    cloud_cover_max: float = 20.0,
    collection: str = "COPERNICUS/S2_SR_HARMONIZED",
) -> ee.Image:
    """
    Get the most recent Sentinel-2 image over Auckland using Google Earth Engine

    Args:
        days_back: Number of days to search back from today
        cloud_cover_max: Maximum cloud cover percentage
        collection: Sentinel-2 collection to use
                   - 'COPERNICUS/S2_SR_HARMONIZED' (Surface Reflectance, recommended)
                   - 'COPERNICUS/S2_SR' (Surface Reflectance, older)
                   - 'COPERNICUS/S2' (Top of Atmosphere)

    Returns:
        Earth Engine Image object of most recent scene
    """

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    # Format dates for Earth Engine
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")

    print(
        f"Searching for Sentinel-2 data over Auckland from {start_date_str} to {end_date_str}"
    )

    # Get Sentinel-2 collection
    collection = (
        ee.ImageCollection(collection)
        .filterBounds(geometry)
        .filterDate(start_date_str, end_date_str)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_cover_max))
        .sort("system:time_start", False)
    )  # Most recent first

    # Get collection size
    collection_size = collection.size()
    print(f"Found {collection_size.getInfo()} images matching criteria")

    if collection_size.getInfo() == 0:
        print("No images found. Try increasing days_back or cloud_cover_max")
        return None

    # Get the most recent image
    most_recent = collection.first()

    # Get image properties
    image_info = most_recent.getInfo()
    props = image_info["properties"]

    print("\n=== MOST RECENT IMAGE ===")
    print(f"Image ID: {image_info['id']}")
    print(
        f"Date: {datetime.fromtimestamp(props['system:time_start']/1000).strftime('%Y-%m-%d %H:%M:%S')}"
    )
    print(f"Cloud Cover: {props.get('CLOUDY_PIXEL_PERCENTAGE', 'N/A')}%")
    print(f"Satellite: {props.get('SPACECRAFT_NAME', 'N/A')}")
    print(f"Processing Level: {props.get('PROCESSING_BASELINE', 'N/A')}")

    return most_recent


# Example usage functions
def quick_get_auckland_sentinel2():
    """
    Quick function to get most recent Sentinel-2 data over Auckland
    """
    try:
        # Initialize Earth Engine (make sure you've authenticated first)
        # Uncomment the next two lines if not already initialized
        # ee.Authenticate()  # Only needed once
        # ee.Initialize()

        print("Getting most recent Sentinel-2 data over Auckland...")

        # Get most recent image
        recent_image = get_most_recent_sentinel2_auckland_ee(
            days_back=21, cloud_cover_max=25.0
        )

        if recent_image:
            print("\nSuccess! Image retrieved.")
            return recent_image
        else:
            print("No suitable images found. Try increasing the search parameters.")
            return None

    except Exception as e:
        print(f"Error: {e}")
        print("Make sure Earth Engine is properly authenticated and initialized.")
        return None


def get_most_recent_sentinel1_auckland_ee(
    geometry: ee.geometry = AUCKLAND_GEOMETRY,
    days_back: int = 30,
    orbit_direction: str = "BOTH",
    instrument_mode: str = "IW",
    collection: str = "COPERNICUS/S1_GRD",
) -> ee.Image:
    """
    Get the most recent Sentinel-1 image over Auckland using Google Earth Engine

    Args:
        days_back: Number of days to search back from today
        orbit_direction: Orbit direction ('ASCENDING', 'DESCENDING', or 'BOTH')
        instrument_mode: Instrument mode ('IW', 'EW', 'SM', or 'WV')
                        - 'IW' (Interferometric Wide swath, most common)
                        - 'EW' (Extra Wide swath)
                        - 'SM' (Strip Map)
                        - 'WV' (Wave)
        collection: Sentinel-1 collection to use
                   - 'COPERNICUS/S1_GRD' (Ground Range Detected, recommended)
                   - 'COPERNICUS/S1_GRD_FLOAT' (Ground Range Detected, float)

    Returns:
        Earth Engine Image object of most recent scene
    """

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    # Format dates for Earth Engine
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")

    print(
        f"Searching for Sentinel-1 data over Auckland from {start_date_str} to {end_date_str}"
    )

    # Get Sentinel-1 collection
    s1_collection = (
        ee.ImageCollection(collection)
        .filterBounds(geometry)
        .filterDate(start_date_str, end_date_str)
        .filter(ee.Filter.eq("instrumentMode", instrument_mode))
        .sort("system:time_start", False)
    )  # Most recent first

    # Filter by orbit direction if specified
    if orbit_direction != "BOTH":
        s1_collection = s1_collection.filter(
            ee.Filter.eq("orbitProperties_pass", orbit_direction)
        )

    # Get collection size
    collection_size = s1_collection.size()
    print(f"Found {collection_size.getInfo()} images matching criteria")

    if collection_size.getInfo() == 0:
        print("No images found. Try increasing days_back or changing orbit_direction")
        return None

    # Get the most recent image
    most_recent = s1_collection.first()

    # Get image properties
    image_info = most_recent.getInfo()
    props = image_info["properties"]

    print("\n=== MOST RECENT IMAGE ===")
    print(f"Image ID: {image_info['id']}")
    print(
        f"Date: {datetime.fromtimestamp(props['system:time_start']/1000).strftime('%Y-%m-%d %H:%M:%S')}"
    )
    # print(f"Satellite: {props.get('platform_number', 'N/A')}")
    # print(f"Orbit Direction: {props.get('orbitProperties_pass', 'N/A')}")
    # print(f"Instrument Mode: {props.get('instrumentMode', 'N/A')}")
    # print(f"Polarization: {props.get('transmitterReceiverPolarisation', 'N/A')}")
    # print(f"Resolution: {props.get('resolution_meters', 'N/A')}m")

    # Print available bands
    bands = most_recent.bandNames().getInfo()
    print(f"Available bands: {bands}")

    return most_recent


def check_sentinel1_polarization(image: ee.Image) -> Dict[str, any]:
    """
    Check the polarization(s) available in a Sentinel-1 image

    Args:
        image: Sentinel-1 Earth Engine Image

    Returns:
        Dictionary with polarization information
    """

    # Get band names
    band_names = image.bandNames().getInfo()

    # Get image properties
    image_info = image.getInfo()
    props = image_info["properties"]

    # Check which polarizations are available
    has_vv = "VV" in band_names
    has_vh = "VH" in band_names
    has_hh = "HH" in band_names
    has_hv = "HV" in band_names

    polarization_info = {
        "band_names": band_names,
        "has_vv": has_vv,
        "has_vh": has_vh,
        "has_hh": has_hh,
        "has_hv": has_hv,
        "is_dual_pol": len(band_names) >= 2,
        "polarization_from_metadata": props.get(
            "transmitterReceiverPolarisation", "N/A"
        ),
    }

    # print("=== POLARIZATION CHECK ===")
    # print(f"Available bands: {band_names}")
    # print(f"VV polarization: {'✓' if has_vv else '✗'}")
    # print(f"VH polarization: {'✓' if has_vh else '✗'}")
    # print(f"HH polarization: {'✓' if has_hh else '✗'}")
    # print(f"HV polarization: {'✓' if has_hv else '✗'}")
    # print(f"Dual polarization: {'✓' if polarization_info['is_dual_pol'] else '✗'}")
    # print(f"Metadata polarization: {polarization_info['polarization_from_metadata']}")

    return polarization_info
