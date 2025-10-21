import ee
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd

AUCKLAND_GEOMETRY = ee.Geometry.Rectangle([174.5, -37.0, 175.3, -36.6])


# Initialize Earth Engine (you need to authenticate first)
ee.Authenticate()
user = "Sam"
if user == "Peter":
    ee.Initialize(project="geog761-peag224")
elif user == "Someone":
    pass
else:
    print("MUST INTIALISE PLEASE ADD YOUR INITIALISATION")
    # PLEASE ADD YOUR INITIALISATIONS IN AN ELIF

# Auckland area of interest


import ee
from datetime import datetime, timedelta


import ee
from datetime import datetime, timedelta


def get_most_recent_sentinel2_auckland_ee(
    geometry: ee.Geometry,
    days_back: int = 100,
    cloud_cover_max: float = 30.0,
    collection: str = "COPERNICUS/S2_SR_HARMONIZED",
    require_full_coverage: bool = True,
    coverage_threshold: float = 0.95,
    max_days_to_composite: int = 14,
) -> ee.Image:
    """
    Get the most recent Sentinel-2 mosaic that fully covers the input region.

    This version builds a composite by progressively adding tiles from older dates
    until full coverage is achieved, filling in cloud gaps.

    Parameters:
        geometry: ee.Geometry
            Region of interest (e.g., Auckland boundary)
        days_back: int
            Number of days to search back from today.
        cloud_cover_max: float
            Maximum cloud cover percentage for filtering.
        collection: str
            Sentinel-2 collection ID (default: "COPERNICUS/S2_SR_HARMONIZED")
        require_full_coverage: bool
            If True, keep adding tiles from earlier dates until full coverage is achieved.
        coverage_threshold: float
            Minimum fraction of geometry that must be covered (0.0-1.0).
        max_days_to_composite: int
            Maximum number of unique dates to combine in the composite.

    Returns:
        ee.Image mosaic covering at least the entire geometry region, or None if not found.
    """

    # Define time range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days_back)
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")

    print(f"Searching Sentinel-2 images from {start_date_str} to {end_date_str}")

    # Filter Sentinel-2 collection
    s2 = (
        ee.ImageCollection(collection)
        .filterBounds(geometry)
        .filterDate(start_date_str, end_date_str)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_cover_max))
        .sort("system:time_start", False)
    )

    collection_size = s2.size().getInfo()
    print(f"Found {collection_size} images matching criteria")

    if collection_size == 0:
        print("No images found. Try increasing days_back or cloud_cover_max.")
        return None

    # Add a date-only property (strip time component)
    def add_date_property(img):
        date = ee.Date(img.get("system:time_start"))
        date_str = date.format("YYYY-MM-dd")
        return img.set("date_only", date_str)

    s2_with_dates = s2.map(add_date_property)

    # Get unique dates (date strings, not timestamps)
    unique_dates = (
        s2_with_dates.aggregate_array("date_only").distinct().sort().reverse()
    )
    num_dates = unique_dates.size().getInfo()
    print(f"Found {num_dates} unique acquisition dates")

    # Build composite progressively
    dates_list = unique_dates.getInfo()
    composite = None
    dates_used = []
    tiles_used = 0

    for i, date_str in enumerate(dates_list):
        if i >= max_days_to_composite:
            print(f"\n⚠ Reached maximum of {max_days_to_composite} dates to composite")
            break

        # Get all images from this calendar date
        same_day_images = s2_with_dates.filter(ee.Filter.eq("date_only", date_str))
        same_day_count = same_day_images.size().getInfo()
        tiles_used += same_day_count

        # Mosaic tiles from this date
        day_mosaic = same_day_images.mosaic()

        # Add to composite (newest on top)
        if composite is None:
            composite = day_mosaic
            print(
                f"\nDate {i+1}/{num_dates}: {date_str} ({same_day_count} tiles) - Starting composite"
            )
        else:
            # Use mosaic to overlay: newer data on top, older fills gaps
            composite = ee.ImageCollection([day_mosaic, composite]).mosaic()
            print(
                f"Date {i+1}/{num_dates}: {date_str} ({same_day_count} tiles) - Adding to composite"
            )

        dates_used.append(date_str)

        # Check coverage
        coverage = check_coverage(composite, geometry)
        print(
            f"  Cumulative coverage: {coverage*100:.1f}% (tiles: {tiles_used}, dates: {len(dates_used)})"
        )

        if require_full_coverage and coverage >= coverage_threshold:
            print(f"\n✓ Full coverage achieved!")
            print(f"  Total tiles used: {tiles_used}")
            print(f"  Date range: {dates_used[-1]} to {dates_used[0]}")
            print(f"  Days spanned: {len(dates_used)}")

            # Log info for the most recent image
            most_recent = s2_with_dates.filter(
                ee.Filter.eq("date_only", dates_used[0])
            ).first()
            log_image_info(most_recent, dates_used)

            return composite

    # If we exit the loop without meeting threshold
    if composite is not None:
        final_coverage = check_coverage(composite, geometry)

        if not require_full_coverage:
            print(f"\n✓ Returning composite with {final_coverage*100:.1f}% coverage")
            print(f"  Total tiles used: {tiles_used}")
            print(f"  Date range: {dates_used[-1]} to {dates_used[0]}")

            most_recent = s2_with_dates.filter(
                ee.Filter.eq("date_only", dates_used[0])
            ).first()
            log_image_info(most_recent, dates_used)
            return composite
        else:
            print(f"\n⚠ Could not achieve {coverage_threshold*100:.1f}% coverage")
            print(f"  Best achieved: {final_coverage*100:.1f}%")
            print(f"  Tiles used: {tiles_used} across {len(dates_used)} dates")
            print(
                "Try: increasing days_back, cloud_cover_max, or max_days_to_composite"
            )

    return None


def check_coverage(image: ee.Image, geometry: ee.Geometry) -> float:
    """
    Calculate what fraction of the geometry is covered by valid (non-masked) pixels.

    Returns:
        float between 0.0 and 1.0 representing coverage fraction
    """
    # Create a binary mask: 1 where image has valid data, 0 where masked
    valid_mask = image.select(0).mask()

    # Calculate area of valid pixels within geometry
    valid_area = (
        valid_mask.multiply(ee.Image.pixelArea())
        .reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geometry,
            scale=10,  # Sentinel-2 native resolution
            maxPixels=1e10,
            bestEffort=True,
        )
        .values()
        .get(0)
    )

    # Calculate total geometry area
    total_area = geometry.area(maxError=10)

    # Return coverage fraction
    coverage = ee.Number(valid_area).divide(total_area).getInfo()
    return coverage


def log_image_info(image: ee.Image, dates_used: list = None) -> None:
    """Log metadata information about an image."""
    image_info = image.getInfo()
    props = image_info["properties"]

    print("\n=== COMPOSITE INFO ===")
    if dates_used and len(dates_used) > 1:
        print(f"Multi-date composite using {len(dates_used)} dates")
        print(f"Most recent date: {dates_used[0]}")
        print(f"Oldest date: {dates_used[-1]}")
    else:
        print(f"Single-date mosaic")

    print(f"\nMost recent tile ID: {image_info['id']}")
    print(
        f"Most recent date: {datetime.fromtimestamp(props['system:time_start']/1000).strftime('%Y-%m-%d %H:%M:%S')}"
    )
    print(f"Cloud Cover (most recent): {props.get('CLOUDY_PIXEL_PERCENTAGE', 'N/A')}%")
    print(f"Satellite: {props.get('SPACECRAFT_NAME', 'N/A')}")
    print(f"Processing Level: {props.get('PROCESSING_BASELINE', 'N/A')}")


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
