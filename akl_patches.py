import ee
import geemap  # We might not use geemap, but good to have
import geopandas as gpd
import numpy as np
import h5py
from pathlib import Path
import json

# Import your functions
from get_newest_data import (
    get_most_recent_sentinel2_auckland_ee,
    get_most_recent_sentinel1_auckland_ee
)

# Initialize Earth Engine
user = "Sam"
if user == "Peter":
    ee.Initialize(project="geog761-peag224")
elif user == "Sam":
    ee.Initialize(project="intricate-aria-467322-j0")


def extract_sentinel_patches(
    grid_utm_geojson_path,      # <--- FIX: We'll use the UTM grid for processing
    grid_wgs84_geojson_path,  # <--- FIX: We'll use the WGS84 grid for total bounds
    output_dir='patches',
    scale=10  # 10m resolution
):
    """
    Extract ALL Sentinel-1 and Sentinel-2 bands for each grid cell and save as HDF5.
    
    Args:
        grid_utm_geojson_path: Path to grid GeoJSON file in UTM projection (e.g., EPSG:32760)
        grid_wgs84_geojson_path: Path to grid GeoJSON file in WGS84 (EPSG:4326)
        output_dir: Directory to save patches
        scale: Resolution in meters
    """
    
    # Create output directories
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"Output directory: {output_path}")
    
    # Read BOTH grids
    print("\nReading grids...")
    grid_utm = gpd.read_file(grid_utm_geojson_path)
    grid_wgs84 = gpd.read_file(grid_wgs84_geojson_path)
    
    # Get the grid CRS from the UTM grid
    grid_crs = grid_utm.crs.to_string() # <--- FIX: Get the CRS (e.g., 'EPSG:32760')
    print(f"Loaded {len(grid_utm)} patches in CRS: {grid_crs}")
    
    # Get the bounding geometry from the WGS84 grid
    grid_bounds = grid_wgs84.total_bounds  # (minx, miny, maxx, maxy)
    grid_geometry = ee.Geometry.Rectangle([
        grid_bounds[0], grid_bounds[1], grid_bounds[2], grid_bounds[3]
    ])
    
    # --- Get Sentinel Images (this part was correct) ---
    print("\nFetching Sentinel-2 image...")
    s2_image = get_most_recent_sentinel2_auckland_ee(
        grid_geometry,
        days_back=100,
        cloud_cover_max=30.0
    )
    if s2_image is None: print("ERROR: S2 Image not found."); return
    s2_bands = s2_image.bandNames().getInfo()
    print(f"   S2 bands: {s2_bands}")
    
    print("\nFetching Sentinel-1 image...")
    s1_image, s1_metadata = get_most_recent_sentinel1_auckland_ee(
        grid_geometry,
        days_back=30
    )
    if s1_image is None: print("ERROR: S1 Image not found."); return
    s1_bands = s1_image.bandNames().getInfo()
    print(f"   S1 bands: {s1_bands}")
    print(f"\n✓ Sentinel images ready")
    
    # Extract patches
    print(f"\nExtracting patches for {len(grid_utm)} grid cells...")
    print("This will take some time...\n")
    
    metadata_list = []
    
    # <--- FIX: Loop over the UTM grid (grid_utm), not the WGS84 grid
    for idx, row in grid_utm.iterrows():
        patch_id = row['patch_id']
        
        if (idx + 1) % 10 == 0 or idx == 0:
            print(f"Processing patch {idx + 1}/{len(grid_utm)} (ID: {patch_id})...")
        
        # Get the geometry for this patch (it's already in UTM)
        patch_geom = ee.Geometry(row.geometry.__geo_interface__)
        
        # Get bounds for the patch (in UTM)
        bounds = row.geometry.bounds  # (minx, miny, maxx, maxy)
        
        try:
            h5_path = output_path / f'patch_{patch_id:04d}.h5'
            
            with h5py.File(h5_path, 'w') as hf:
                # <--- FIX: Pass the grid_crs to the extraction function
                
                # Extract and save Sentinel-2 data
                s2_data = extract_patch_data(s2_image, patch_geom, grid_crs, scale)
                if s2_data is not None:
                    s2_group = hf.create_group('sentinel2')
                    print(f"  -> S2 data shape: {s2_data.shape}") # Debug print
                    for i, band_name in enumerate(s2_bands):
                        # s2_data is (H, W, C), so we save each channel
                        s2_group.create_dataset(band_name, data=s2_data[:, :, i])
                
                # Extract and save Sentinel-1 data
                s1_data = extract_patch_data(s1_image, patch_geom, grid_crs, scale)
                if s1_data is not None:
                    s1_group = hf.create_group('sentinel1')
                    print(f"  -> S1 data shape: {s1_data.shape}") # Debug print
                    for i, band_name in enumerate(s1_bands):
                        s1_group.create_dataset(band_name, data=s1_data[:, :, i])
                
                # Save metadata as attributes
                hf.attrs['patch_id'] = int(patch_id)
                hf.attrs['crs'] = grid_crs
                hf.attrs['bounds_minx'] = bounds[0]
                hf.attrs['bounds_miny'] = bounds[1]
                hf.attrs['bounds_maxx'] = bounds[2]
                hf.attrs['bounds_maxy'] = bounds[3]
                hf.attrs['scale_meters'] = scale
                hf.attrs['s2_bands'] = ','.join(s2_bands)
                hf.attrs['s1_bands'] = ','.join(s1_bands)
            
            # (Metadata list logic was fine)

        except Exception as e:
            print(f"\nError processing patch {patch_id}: {e}")
            continue
    
    # (Metadata saving logic was fine)
    print(f"\n✓ Extraction complete!")


def extract_patch_data(image, geometry, crs, scale=10): # <--- FIX: Added CRS
    """
    Extract patch data from an Earth Engine image as numpy array.
    Forces all bands to a single scale.
    
    Args:
        image: ee.Image to extract from
        geometry: ee.Geometry defining the patch area (in correct CRS)
        crs: The CRS of the geometry (e.g., 'EPSG:32760')
        scale: Resolution in meters
        
    Returns:
        numpy array of shape (height, width, bands) or None if failed
    """
    
    try:
        # <--- FIX: This is the core solution ---
        # 1. Reproject the image to force all bands to the same CRS and Scale
        #    This fixes the 10m/20m/60m band conflict.
        image_rescaled = image.reproject(crs=crs, scale=scale)

        # 2. Sample the *rescaled* image
        sample = image_rescaled.sampleRectangle(region=geometry, defaultValue=0)
        # ------------------------------------
        
        # Get band names
        band_names = image.bandNames().getInfo()
        
        # Extract arrays for each band
        band_arrays = []
        for band in band_names:
            band_data = np.array(sample.get(band).getInfo())
            
            # Check for errors
            if band_data.size == 0:
                raise Exception(f"Band {band} returned no data.")
            if band_data.shape[0] < 2 or band_data.shape[1] < 2:
                # This check catches the (1, 1) pixel error
                raise Exception(f"Band {band} extracted only {band_data.shape} pixels.")
                
            band_arrays.append(band_data)
        
        # Stack bands into shape (height, width, bands)
        data_array = np.stack(band_arrays, axis=-1)
        return data_array
            
    except Exception as e:
        print(f"Error in extract_patch_data: {e}")
        return None


# Main execution
if __name__ == "__main__":
    
    # <--- FIX: Define paths for BOTH grid files
    grid_utm_path = 'aklshp/auckland_grid_5000m.geojson'
    grid_wgs84_path = 'aklshp/auckland_grid_5000m_wgs84.geojson'
    
    extract_sentinel_patches(
        grid_utm_geojson_path=grid_utm_path,
        grid_wgs84_geojson_path=grid_wgs84_path,
        output_dir='auckland_patches',
        scale=10  # 10m resolution
    )