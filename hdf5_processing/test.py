import ee
import json
import os
import h5py
import numpy as np
from typing import List, Tuple
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
import tempfile
from pathlib import Path
import sys

ee.Initialize(project="geog761-peag224")
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from gui.data_retrival import *


def process_single_patch(
    feature: dict,
    index: int,
    start_date: str,
    end_date: str,
    output_dir: str,
    s1_bands: List[str],
    s2_bands: List[str],
    scale: int = 10,
    max_cloud_percent: int = 50,
) -> Tuple[int, bool, str]:
    """
    Process a single patch and save to H5.
    Returns: (index, success, message)
    """
    try:
        coordinates = feature["geometry"]["coordinates"][0]
        geometry = ee.Geometry.Polygon([coordinates])

        # Get data
        s2_mosaic = get_s2_image(geometry, start_date, end_date, max_cloud_percent)
        s1_mosaic = get_s1_image(geometry, start_date, end_date)

        # Download using single export (much faster than band-by-band)
        output_path = os.path.join(output_dir, f"image_{index}.h5")

        ee_images_to_hdf5_optimized(
            s1_image=s1_mosaic,
            s2_image=s2_mosaic,
            output_path=output_path,
            region=geometry,
            scale=scale,
            s1_bands=s1_bands,
            s2_bands=s2_bands,
        )

        return (index, True, f"✓ Patch {index}")

    except Exception as e:
        return (index, False, f"✗ Patch {index}: {str(e)}")


def ee_images_to_hdf5_optimized(
    s1_image: ee.Image,
    s2_image: ee.Image,
    output_path: str,
    region: ee.Geometry,
    scale: int = 10,
    crs: str = "EPSG:4326",
    s1_bands: List[str] = None,
    s2_bands: List[str] = None,
) -> None:
    """
    Optimized version that downloads all bands at once.
    """
    # Select bands
    if s1_bands:
        s1_image = s1_image.select(s1_bands)
    if s2_bands:
        s2_image = s2_image.select(s2_bands)

    s1_band_names = s1_image.bandNames().getInfo()
    s2_band_names = s2_image.bandNames().getInfo()

    print(f"  Processing {len(s1_band_names)} S1 + {len(s2_band_names)} S2 bands...")

    # Download using GeoTIFF (fastest method - all bands at once)
    try:
        s1_array = download_via_geotiff(s1_image, region, scale, crs)
        s2_array = download_via_geotiff(s2_image, region, scale, crs)
    except Exception as e:
        print(f"  GeoTIFF download failed: {e}, using fallback...")
        s1_array = ee_image_to_numpy_thumb(s1_image, region, scale, crs)
        s2_array = ee_image_to_numpy_thumb(s2_image, region, scale, crs)

    # Save to H5
    with h5py.File(output_path, "w") as hf:
        s1_group = hf.create_group("sentinel1")
        s2_group = hf.create_group("sentinel2")

        for i, band_name in enumerate(s1_band_names):
            s1_group.create_dataset(
                band_name,
                data=s1_array[:, :, i],
                compression="gzip",
                compression_opts=4,
            )

        for i, band_name in enumerate(s2_band_names):
            s2_group.create_dataset(
                band_name,
                data=s2_array[:, :, i],
                compression="gzip",
                compression_opts=4,
            )

        metadata = hf.create_group("metadata")
        metadata.attrs["scale"] = scale
        metadata.attrs["crs"] = crs
        metadata.attrs["s1_bands"] = s1_band_names
        metadata.attrs["s2_bands"] = s2_band_names


def download_via_geotiff(
    image: ee.Image, region: ee.Geometry, scale: int, crs: str
) -> np.ndarray:
    """
    Download all bands at once via GeoTIFF (fastest method).
    """
    from osgeo import gdal

    url = image.getDownloadURL(
        {"region": region, "scale": scale, "crs": crs, "format": "GEO_TIFF"}
    )

    response = requests.get(url, timeout=300)
    response.raise_for_status()

    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
        tmp.write(response.content)
        tmp_path = tmp.name

    try:
        dataset = gdal.Open(tmp_path)
        bands = [
            dataset.GetRasterBand(i + 1).ReadAsArray()
            for i in range(dataset.RasterCount)
        ]
        dataset = None
        return np.stack(bands, axis=-1)
    finally:
        os.unlink(tmp_path)


def batch_process_patches(
    geojson_path: str,
    start_date: str,
    end_date: str,
    output_dir: str,
    s1_bands: List[str],
    s2_bands: List[str],
    max_workers: int = 4,
    scale: int = 10,
    max_cloud_percent: int = 50,
) -> None:
    """
    Process multiple patches in parallel.

    Parameters:
    -----------
    max_workers : int
        Number of parallel downloads (be careful not to exceed EE rate limits)
    """
    # Load features
    with open(geojson_path, "r") as f:
        data = json.load(f)
    features = data.get("features", [])

    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*70}")
    print(f"BATCH PROCESSING {len(features)} PATCHES")
    print(f"{'='*70}")
    print(f"Period: {start_date} to {end_date}")
    print(f"Output: {output_dir}")
    print(f"Parallel workers: {max_workers}")
    print(f"{'='*70}\n")

    # Process in parallel (but limit workers to avoid EE rate limits)
    process_func = partial(
        process_single_patch,
        start_date=start_date,
        end_date=end_date,
        output_dir=output_dir,
        s1_bands=s1_bands,
        s2_bands=s2_bands,
        scale=scale,
        max_cloud_percent=max_cloud_percent,
    )

    completed = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_func, feature, i): i
            for i, feature in enumerate(features)
        }

        for future in as_completed(futures):
            idx, success, message = future.result()
            print(message)

            if success:
                completed += 1
            else:
                failed += 1

            print(
                f"Progress: {completed + failed}/{len(features)} "
                f"(✓ {completed}, ✗ {failed})"
            )

    print(f"\n{'='*70}")
    print(f"COMPLETED: {completed}/{len(features)} patches")
    if failed > 0:
        print(f"FAILED: {failed} patches")
    print(f"{'='*70}\n")


# Example usage
if __name__ == "__main__":
    geojson_path = r"aklshp\auckland_grid_5000m_wgs84.geojson"
    start_date = "2023-02-15"
    end_date = "2023-04-15"

    s1_bands = ["VV"]
    s2_bands = [
        "B1",
        "B2",
        "B3",
        "B4",
        "B5",
        "B6",
        "B7",
        "B8",  # Fixed typo here
        "B8A",
        "B9",
        "B11",
        "B12",
    ]

    batch_process_patches(
        geojson_path=geojson_path,
        start_date=start_date,
        end_date=end_date,
        output_dir="Training Data/cyclone_gabriella_patches",
        s1_bands=s1_bands,
        s2_bands=s2_bands,
        max_workers=3,  # Conservative to avoid EE rate limits
        scale=10,
        max_cloud_percent=50,
    )
