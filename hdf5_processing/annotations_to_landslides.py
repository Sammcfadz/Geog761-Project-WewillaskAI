"""
Extract Sentinel-1 and Sentinel-2 data based on landslide annotations.

This script reads a GeoJSON file with landslide annotations and extracts
satellite data for the region of interest during the specified time period.
"""

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


def calculate_dimensions(geometry, scale):
    """
    Calculate the expected dimensions of the output image.

    Parameters:
    -----------
    geometry : ee.Geometry
        The region geometry
    scale : int
        Scale in meters

    Returns:
    --------
    tuple : (width, height) in pixels
    """
    bounds = geometry.bounds().getInfo()["coordinates"][0]

    # Calculate approximate dimensions
    min_lon = min(coord[0] for coord in bounds)
    max_lon = max(coord[0] for coord in bounds)
    min_lat = min(coord[1] for coord in bounds)
    max_lat = max(coord[1] for coord in bounds)

    # Rough conversion (1 degree ~= 111 km)
    width_km = (max_lon - min_lon) * 111 * np.cos(np.radians((min_lat + max_lat) / 2))
    height_km = (max_lat - min_lat) * 111

    width_px = int(width_km * 1000 / scale)
    height_px = int(height_km * 1000 / scale)

    return width_px, height_px


def ee_image_to_numpy_export(
    image: ee.Image, region: ee.Geometry, scale: int, crs: str = "EPSG:4326"
) -> np.ndarray:
    """
    Convert Earth Engine image to numpy using getDownloadURL method.
    More reliable than sampleRectangle for larger regions.

    Parameters:
    -----------
    image : ee.Image
        Earth Engine image to convert
    region : ee.Geometry
        Region of interest
    scale : int
        Scale in meters
    crs : str
        Coordinate reference system

    Returns:
    --------
    np.ndarray : 3D numpy array (height, width, bands)
    """
    band_names = image.bandNames().getInfo()
    print(f"  Extracting bands: {band_names}")

    # Get the region info
    region_info = region.getInfo()
    print(f"  Region type: {region_info['type']}")

    # Calculate expected dimensions
    width, height = calculate_dimensions(region, scale)
    print(f"  Expected dimensions: {width}x{height} pixels")

    if width * height > 10000 * 10000:
        raise ValueError(
            f"Region too large: {width}x{height} pixels. Maximum is 10000x10000."
        )

    # Try to use GDAL if available
    try:
        from osgeo import gdal
        import tempfile

        print(f"  Attempting download via getDownloadURL...")
        url = image.getDownloadURL(
            {"region": region, "scale": scale, "crs": crs, "format": "GEO_TIFF"}
        )

        # Download the file
        response = requests.get(url)
        response.raise_for_status()

        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name

        # Read with GDAL
        dataset = gdal.Open(tmp_path)
        bands = []

        for i in range(1, dataset.RasterCount + 1):
            band = dataset.GetRasterBand(i)
            bands.append(band.ReadAsArray())

        # Clean up
        dataset = None
        os.unlink(tmp_path)

        # Stack bands
        stacked = np.stack(bands, axis=-1)
        print(f"  ✓ Successfully downloaded: {stacked.shape}")

        return stacked

    except ImportError:
        print(f"  ⚠️  GDAL not available, using alternative method...")
        return ee_image_to_numpy_thumb(image, region, scale, crs)
    except Exception as e:
        print(f"  ⚠️  getDownloadURL failed: {e}")
        print(f"  Trying alternative method...")
        return ee_image_to_numpy_thumb(image, region, scale, crs)


def ee_image_to_numpy_sample(
    image: ee.Image, region: ee.Geometry, scale: int, crs: str
) -> np.ndarray:
    """
    Convert Earth Engine image to numpy using computePixels API.
    Most reliable method that works without GDAL.

    Parameters:
    -----------
    image : ee.Image
        Earth Engine image to convert
    region : ee.Geometry
        Region of interest
    scale : int
        Scale in meters
    crs : str
        Coordinate reference system

    Returns:
    --------
    np.ndarray : 3D numpy array (height, width, bands)
    """
    band_names = image.bandNames().getInfo()
    print(f"  Using computePixels API...")

    try:
        # Get bounds
        bounds = region.bounds().getInfo()["coordinates"][0]
        min_lon = min(coord[0] for coord in bounds)
        max_lon = max(coord[0] for coord in bounds)
        min_lat = min(coord[1] for coord in bounds)
        max_lat = max(coord[1] for coord in bounds)

        # Create a grid expression
        grid = {
            "expression": image,
            "fileFormat": "NUMPY_NDARRAY",
            "grid": {
                "dimensions": {
                    "width": int(
                        (max_lon - min_lon) * 111320 / scale
                    ),  # approximate meters per degree
                    "height": int((max_lat - min_lat) * 111320 / scale),
                },
                "affineTransform": {
                    "scaleX": scale,
                    "scaleY": -scale,
                    "translateX": min_lon,
                    "translateY": max_lat,
                },
                "crsCode": crs,
            },
        }

        print(f"    Grid dimensions: {grid['grid']['dimensions']}")

        # Compute pixels
        result = ee.data.computePixels(grid)

        # Convert to numpy array
        import struct

        # The result is in a structured format, need to parse it
        # For now, let's use a simpler approach with getThumbURL
        raise NotImplementedError("Using getThumbURL instead")

    except Exception as e:
        print(f"  ⚠️  computePixels failed: {e}")
        print(f"  Trying getThumbURL method...")
        return ee_image_to_numpy_thumb(image, region, scale, crs)


def ee_image_to_numpy_thumb(
    image: ee.Image, region: ee.Geometry, scale: int, crs: str
) -> np.ndarray:
    """
    Convert Earth Engine image to numpy using getThumbURL with proper visualization.

    Parameters:
    -----------
    image : ee.Image
        Earth Engine image to convert
    region : ee.Geometry
        Region of interest
    scale : int
        Scale in meters
    crs : str
        Coordinate reference system

    Returns:
    --------
    np.ndarray : 3D numpy array (height, width, bands)
    """
    from PIL import Image as PILImage
    import io

    band_names = image.bandNames().getInfo()
    print(f"  Using getThumbURL method with auto-scaling...")

    # Get bounds for dimensions calculation
    bounds = region.bounds().getInfo()["coordinates"][0]
    min_lon = min(coord[0] for coord in bounds)
    max_lon = max(coord[0] for coord in bounds)
    min_lat = min(coord[1] for coord in bounds)
    max_lat = max(coord[1] for coord in bounds)

    # Calculate dimensions in pixels
    width = int(
        (max_lon - min_lon)
        * 111320
        * np.cos(np.radians((min_lat + max_lat) / 2))
        / scale
    )
    height = int((max_lat - min_lat) * 111320 / scale)

    print(f"    Calculated dimensions: {width}x{height} pixels")

    # Process each band separately
    band_arrays = []

    for band_name in band_names:
        print(f"    Processing band {band_name}...")

        # Get the single band
        single_band = image.select([band_name])

        # Get min/max for visualization (sample from the actual data)
        try:
            stats = single_band.reduceRegion(
                reducer=ee.Reducer.minMax(), geometry=region, scale=scale, maxPixels=1e9
            ).getInfo()

            band_min = stats.get(f"{band_name}_min", 0)
            band_max = stats.get(f"{band_name}_max", 1)

            print(f"      Value range: [{band_min:.2f}, {band_max:.2f}]")
        except Exception as e:
            print(f"      ⚠️  Could not get stats: {e}")
            # Use default ranges
            band_min = 0
            band_max = 1

        # Ensure we have a valid range
        if band_min == band_max:
            band_min = band_min - 0.1
            band_max = band_max + 0.1

        # Get thumbnail URL with visualization parameters
        url = single_band.getThumbURL(
            {
                "region": region.getInfo(),
                "dimensions": [width, height],
                "min": band_min,
                "max": band_max,
                "format": "png",
            }
        )

        # Download the image
        response = requests.get(url)
        response.raise_for_status()

        # Open with PIL
        img = PILImage.open(io.BytesIO(response.content))

        # Convert to numpy array (0-255 range)
        arr = np.array(img)

        # If RGB image (getThumbURL sometimes returns RGB), take first channel
        if arr.ndim == 3:
            arr = arr[:, :, 0]

        # Convert back to original scale
        # arr is in 0-255 range, convert back to original values
        arr_scaled = arr.astype(np.float32) / 255.0 * (band_max - band_min) + band_min

        print(
            f"      Shape: {arr_scaled.shape}, Range: [{arr_scaled.min():.2f}, {arr_scaled.max():.2f}]"
        )
        band_arrays.append(arr_scaled)

    # Stack bands
    stacked = np.stack(band_arrays, axis=-1)
    print(f"  ✓ Successfully downloaded: {stacked.shape}")

    return stacked


def ee_images_to_hdf5(
    s1_image: ee.Image,
    s2_image: ee.Image,
    output_path: str,
    region: ee.Geometry,
    scale: int = 10,
    crs: str = "EPSG:4326",
    s1_bands: Optional[List[str]] = None,
    s2_bands: Optional[List[str]] = None,
    use_export_method: bool = True,
) -> None:
    """
    Convert two Earth Engine images (S1 and S2) to a single HDF5 file.

    Parameters:
    -----------
    s1_image : ee.Image
        Sentinel-1 image
    s2_image : ee.Image
        Sentinel-2 image
    output_path : str
        Path to save the HDF5 file (e.g., 'output.h5')
    region : ee.Geometry
        Region of interest for export
    scale : int
        Scale in meters for export (default: 10)
    crs : str
        Coordinate reference system (default: 'EPSG:4326')
    s1_bands : List[str], optional
        List of S1 bands to export. If None, exports all bands.
    s2_bands : List[str], optional
        List of S2 bands to export. If None, exports all bands.
    use_export_method : bool
        If True, use getDownloadURL (more reliable). If False, use sampleRectangle.
    """

    print("\n" + "=" * 70)
    print("STARTING DATA EXTRACTION")
    print("=" * 70)

    # Get available band names first
    available_s1_bands = s1_image.bandNames().getInfo()
    available_s2_bands = s2_image.bandNames().getInfo()

    print(f"\nAvailable S1 bands: {available_s1_bands}")
    print(f"Available S2 bands: {available_s2_bands}")

    # Check if images are empty
    if len(available_s1_bands) == 0:
        raise ValueError("S1 image has no bands available!")
    if len(available_s2_bands) == 0:
        raise ValueError("S2 image has no bands available!")

    # Select specific bands if provided
    s1_band_names = []
    if s1_bands:
        valid_s1_bands = [b for b in s1_bands if b in available_s1_bands]
        if not valid_s1_bands:
            raise ValueError(
                f"None of the requested S1 bands {s1_bands} are available. Available: {available_s1_bands}"
            )
        if len(valid_s1_bands) != len(s1_bands):
            missing = set(s1_bands) - set(valid_s1_bands)
            print(f"Warning: S1 bands {missing} not available, using {valid_s1_bands}")
        s1_image = s1_image.select(valid_s1_bands)
        s1_band_names = valid_s1_bands
    else:
        s1_band_names = available_s1_bands

    s2_band_names = []
    if s2_bands:
        valid_s2_bands = [b for b in s2_bands if b in available_s2_bands]
        if not valid_s2_bands:
            raise ValueError(
                f"None of the requested S2 bands {s2_bands} are available. Available: {available_s2_bands}"
            )
        if len(valid_s2_bands) != len(s2_bands):
            missing = set(s2_bands) - set(valid_s2_bands)
            print(f"Warning: S2 bands {missing} not available, using {valid_s2_bands}")
        s2_image = s2_image.select(valid_s2_bands)
        s2_band_names = valid_s2_bands
    else:
        s2_band_names = available_s2_bands

    print(f"\nProcessing:")
    print(f"  S1 bands: {s1_band_names}")
    print(f"  S2 bands: {s2_band_names}")

    # Choose extraction method
    extract_func = (
        ee_image_to_numpy_export if use_export_method else ee_image_to_numpy_sample
    )

    # Download images as numpy arrays
    print("\n" + "-" * 70)
    print("Downloading S1 image...")
    print("-" * 70)
    s1_array = extract_func(s1_image, region, scale, crs)
    print(f"✓ S1 array shape: {s1_array.shape}")

    print("\n" + "-" * 70)
    print("Downloading S2 image...")
    print("-" * 70)
    s2_array = extract_func(s2_image, region, scale, crs)
    print(f"✓ S2 array shape: {s2_array.shape}")

    # Verify data is not all zeros
    if np.all(s1_array == 0):
        print("\n⚠️  WARNING: S1 data is all zeros!")
    if np.all(s2_array == 0):
        print("\n⚠️  WARNING: S2 data is all zeros!")

    # Create HDF5 file
    print("\n" + "-" * 70)
    print(f"Creating HDF5 file: {output_path}")
    print("-" * 70)

    with h5py.File(output_path, "w") as hf:
        # Create groups for each sensor
        s1_group = hf.create_group("sentinel1")
        s2_group = hf.create_group("sentinel2")

        # Store S1 data
        for i, band_name in enumerate(s1_band_names):
            s1_group.create_dataset(
                band_name,
                data=s1_array[:, :, i],
                compression="gzip",
                compression_opts=4,
            )
            print(f"  Saved S1/{band_name}: {s1_array[:, :, i].shape}")

        # Store S2 data
        for i, band_name in enumerate(s2_band_names):
            s2_group.create_dataset(
                band_name,
                data=s2_array[:, :, i],
                compression="gzip",
                compression_opts=4,
            )
            print(f"  Saved S2/{band_name}: {s2_array[:, :, i].shape}")

        # Store metadata
        metadata = hf.create_group("metadata")
        metadata.attrs["scale"] = scale
        metadata.attrs["crs"] = crs
        metadata.attrs["region"] = str(region.getInfo())
        metadata.attrs["s1_bands"] = s1_band_names
        metadata.attrs["s2_bands"] = s2_band_names

    print(f"\n✓ Successfully saved to {output_path}")
    print("=" * 70)


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

    print(f"Processing period: {start_date} to {end_date}")
    print(f"Region type: {geometry.type().getInfo()}")
    print(f"Region bounds: {geometry.bounds().getInfo()}")

    # Get Sentinel-2 mosaic
    print("\nRetrieving Sentinel-2 data...")
    s_2_mosaic = get_s2_image(geometry, start_date, end_date, max_cloud_percent=50)

    print("\nRetrieving Sentinel-1 data...")
    s_1_mosiac = get_s1_image(geometry, start_date, end_date)

    # Convert to HDF5
    try:
        ee_images_to_hdf5(
            s1_image=s_1_mosiac,
            s2_image=s_2_mosaic,
            output_path="random.h5",
            region=geometry,
            scale=10,
            s1_bands=["VV"],  # Only VV available
            s2_bands=["B2", "B3", "B4", "B8"],
            use_export_method=True,  # Try this method first
        )
    except Exception as e:
        print(f"\n❌ Export method failed: {e}")
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
