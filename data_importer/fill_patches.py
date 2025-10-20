import ee
import geemap
import geopandas as gpd
import numpy as np
import h5py
from pathlib import Path
import json

# Import your functions
from data_importer.get_specific_data import (
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
    grid_geojson_path,
    output_dir='patches',
    scale=10  # 10m resolution
):
    """
    Extract ALL Sentinel-1 and Sentinel-2 bands for each grid cell and save as HDF5.
    
    Args:
        grid_geojson_path: Path to grid GeoJSON file
        output_dir: Directory to save patches
        scale: Resolution in meters
    """
    
    # Create output directories
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"Output directory: {output_path}")
    
    # Read the grid
    print("\nReading grid...")
    grid = gpd.read_file(grid_geojson_path)
    grid_wgs84 = grid.to_crs('EPSG:4326')
    print(f"Loaded {len(grid)} patches")
    
    # Get the bounding geometry from the grid itself
    grid_bounds = grid_wgs84.total_bounds  # (minx, miny, maxx, maxy)
    grid_geometry = ee.Geometry.Rectangle([
        grid_bounds[0], grid_bounds[1], grid_bounds[2], grid_bounds[3]
    ])
    
    # Get Sentinel images using grid geometry
    print("\nFetching Sentinel-2 image...")
    s2_image = get_most_recent_sentinel2_auckland_ee(
        grid_geometry,
        days_back=100,
        cloud_cover_max=30.0
    )
    
    if s2_image is None:
        print("ERROR: Could not get Sentinel-2 image")
        return
    
    # Get ALL Sentinel-2 bands
    s2_bands = s2_image.bandNames().getInfo()
    print(f"  S2 bands: {s2_bands}")
    
    print("\nFetching Sentinel-1 image...")
    s1_image, s1_metadata = get_most_recent_sentinel1_auckland_ee(
        grid_geometry,
        days_back=30
    )
    
    if s1_image is None:
        print("ERROR: Could not get Sentinel-1 image")
        return
    
    # Get ALL Sentinel-1 bands
    s1_bands = s1_image.bandNames().getInfo()
    print(f"  S1 bands: {s1_bands}")
    
    print(f"\n✓ Sentinel images ready")
    
    # Extract patches
    print(f"\nExtracting patches for {len(grid)} grid cells...")
    print("This will take some time...\n")
    
    metadata_list = []
    
    for idx, row in grid_wgs84.iterrows():
        patch_id = row['patch_id']
        
        if (idx + 1) % 10 == 0 or idx == 0:
            print(f"Processing patch {idx + 1}/{len(grid_wgs84)}...")
        
        # Get the geometry for this patch
        patch_geom = ee.Geometry(row.geometry.__geo_interface__)
        
        # Get bounds for the patch
        bounds = row.geometry.bounds  # (minx, miny, maxx, maxy)
        
        try:
            # Create HDF5 file for this patch
            h5_path = output_path / f'patch_{patch_id:04d}.h5'
            
            with h5py.File(h5_path, 'w') as hf:
                # Extract and save Sentinel-2 data
                s2_data = extract_patch_data(s2_image, patch_geom, scale)
                if s2_data is not None:
                    s2_group = hf.create_group('sentinel2')
                    for i, band_name in enumerate(s2_bands):
                        s2_group.create_dataset(band_name, data=s2_data[:, :, i])
                
                # Extract and save Sentinel-1 data
                s1_data = extract_patch_data(s1_image, patch_geom, scale)
                if s1_data is not None:
                    s1_group = hf.create_group('sentinel1')
                    for i, band_name in enumerate(s1_bands):
                        s1_group.create_dataset(band_name, data=s1_data[:, :, i])
                
                # Save metadata as attributes
                hf.attrs['patch_id'] = int(patch_id)
                hf.attrs['col'] = int(row['col'])
                hf.attrs['row'] = int(row['row'])
                hf.attrs['center_x'] = float(row['center_x'])
                hf.attrs['center_y'] = float(row['center_y'])
                hf.attrs['bounds_minx'] = bounds[0]
                hf.attrs['bounds_miny'] = bounds[1]
                hf.attrs['bounds_maxx'] = bounds[2]
                hf.attrs['bounds_maxy'] = bounds[3]
                hf.attrs['scale_meters'] = scale
                hf.attrs['s2_bands'] = ','.join(s2_bands)
                hf.attrs['s1_bands'] = ','.join(s1_bands)
            
            # Save metadata for JSON summary
            patch_metadata = {
                'patch_id': int(patch_id),
                'col': int(row['col']),
                'row': int(row['row']),
                'center_x': float(row['center_x']),
                'center_y': float(row['center_y']),
                'bounds_wgs84': {
                    'minx': bounds[0],
                    'miny': bounds[1],
                    'maxx': bounds[2],
                    'maxy': bounds[3]
                },
                's2_bands': s2_bands,
                's1_bands': s1_bands,
                'h5_file': f'patch_{patch_id:04d}.h5',
                'scale_meters': scale
            }
            
            metadata_list.append(patch_metadata)
            
        except Exception as e:
            print(f"\nError processing patch {patch_id}: {e}")
            continue
    
    # Save all metadata
    metadata_path = output_path / 'patches_metadata.json'
    with open(metadata_path, 'w') as f:
        json.dump(metadata_list, f, indent=2)
    
    print(f"\n✓ Extraction complete!")
    print(f"  Total patches: {len(metadata_list)}")
    print(f"  HDF5 files: {output_path}")
    print(f"  Metadata: {metadata_path}")


def extract_patch_data(image, geometry, scale=10):
    """
    Extract patch data from an Earth Engine image as numpy array.
    
    Args:
        image: ee.Image to extract from
        geometry: ee.Geometry defining the patch area
        scale: Resolution in meters
        
    Returns:
        numpy array of shape (height, width, bands) or None if failed
    """
    
    try:
        # Sample the image at the region
        # Get pixel values as a list
        sample = image.sampleRectangle(region=geometry, defaultValue=0)
        
        # Get band names
        band_names = image.bandNames().getInfo()
        
        # Extract arrays for each band
        band_arrays = []
        for band in band_names:
            band_data = np.array(sample.get(band).getInfo())
            band_arrays.append(band_data)
        
        # Stack bands into shape (height, width, bands)
        data_array = np.stack(band_arrays, axis=-1)
        return data_array
            
    except Exception as e:
        print(f"Error extracting patch: {e}")
        return None


# Main execution
if __name__ == "__main__":
    
    grid_path = 'aklshp/auckland_grid_5000m.geojson'
    
    extract_sentinel_patches(
        grid_geojson_path=grid_path,
        output_dir='auckland_patches',
        scale=10  # 10m resolution
    )