import geopandas as gpd
import numpy as np
from shapely.geometry import box, Polygon
import json

def create_grid(geojson_path, output_path='grid_100m.geojson', grid_size=100, crs='EPSG:32760'):
    """
    Create a square grid that covers all points in a GeoJSON polygon.
    
    Args:
        geojson_path: Path to input GeoJSON file
        output_path: Path to save output grid GeoJSON
        grid_size: Size of grid cells in meters (default: 100m). Creates square cells.
        crs: Coordinate reference system to use (default: UTM 60S for Auckland)
    
    Returns:
        GeoDataFrame containing the grid
    """
    
    # Read the GeoJSON
    print(f"Reading GeoJSON from {geojson_path}")
    gdf = gpd.read_file(geojson_path)
    print(f"Original CRS: {gdf.crs}")
    
    # Reproject to UTM (meters) for accurate 100m grid
    print(f"Reprojecting to {crs}")
    gdf_utm = gdf.to_crs(crs)
    
    # Get the bounding box
    bounds = gdf_utm.total_bounds  # (minx, miny, maxx, maxy)
    minx, miny, maxx, maxy = bounds
    
    print(f"\nBounding box in {crs}:")
    print(f"  Min X: {minx:.2f}m, Max X: {maxx:.2f}m")
    print(f"  Min Y: {miny:.2f}m, Max Y: {maxy:.2f}m")
    print(f"  Width: {maxx - minx:.2f}m")
    print(f"  Height: {maxy - miny:.2f}m")
    
    # Create grid with specified size (always square)
    # grid_size is in meters
    
    print(f"\nCreating {grid_size}m x {grid_size}m grid...")
    
    # Calculate grid coordinates (snap to 100m grid)
    x_min = np.floor(minx / grid_size) * grid_size
    x_max = np.ceil(maxx / grid_size) * grid_size
    y_min = np.floor(miny / grid_size) * grid_size
    y_max = np.ceil(maxy / grid_size) * grid_size
    
    # Generate grid cells
    x_coords = np.arange(x_min, x_max, grid_size)
    y_coords = np.arange(y_min, y_max, grid_size)
    
    n_cols = len(x_coords)
    n_rows = len(y_coords)
    total_patches = n_cols * n_rows
    
    print(f"\nGrid dimensions:")
    print(f"  Columns: {n_cols}")
    print(f"  Rows: {n_rows}")
    print(f"  Total patches: {total_patches}")
    
    # Create grid polygons
    grid_cells = []
    grid_ids = []
    grid_centers_x = []
    grid_centers_y = []
    
    patch_id = 0
    for i, x in enumerate(x_coords):
        for j, y in enumerate(y_coords):
            # Create 100m x 100m box
            cell = box(x, y, x + grid_size, y + grid_size)
            
            # Calculate center
            center_x = x + grid_size / 2
            center_y = y + grid_size / 2
            
            grid_cells.append(cell)
            grid_ids.append(patch_id)
            grid_centers_x.append(center_x)
            grid_centers_y.append(center_y)
            
            patch_id += 1
    
    # Create GeoDataFrame
    grid_gdf = gpd.GeoDataFrame({
        'patch_id': grid_ids,
        'col': [i for i in range(n_cols) for j in range(n_rows)],
        'row': [j for i in range(n_cols) for j in range(n_rows)],
        'center_x': grid_centers_x,
        'center_y': grid_centers_y,
        'geometry': grid_cells
    }, crs=crs)
    
    # Filter out patches that don't intersect with the original geometry
    print(f"\nFiltering patches that intersect with GeoJSON...")
    print(f"  Before filtering: {len(grid_gdf)} patches")
    
    # Keep only patches that intersect with the original polygon
    grid_gdf = grid_gdf[grid_gdf.intersects(gdf_utm.unary_union)]
    
    # Reset patch IDs to be sequential after filtering
    grid_gdf['patch_id'] = range(len(grid_gdf))
    grid_gdf = grid_gdf.reset_index(drop=True)
    
    print(f"  After filtering: {len(grid_gdf)} patches")
    print(f"  Removed: {total_patches - len(grid_gdf)} patches")
    
    # Save to file
    print(f"\nSaving grid to {output_path}")
    grid_gdf.to_file(output_path, driver='GeoJSON')
    
    # Also create a version in original CRS (WGS84)
    output_wgs84 = output_path.replace('.geojson', '_wgs84.geojson')
    grid_wgs84 = grid_gdf.to_crs('EPSG:4326')
    grid_wgs84.to_file(output_wgs84, driver='GeoJSON')
    print(f"Saved WGS84 version to {output_wgs84}")
    
    print(f"\n✓ Grid creation complete!")
    print(f"  Grid size: {grid_size}m x {grid_size}m")
    print(f"  Total patches: {len(grid_gdf)}")
    print(f"  CRS: {grid_gdf.crs}")
    
    return grid_gdf


# Example usage
if __name__ == "__main__":
    # Replace with your GeoJSON path
    geojson_file = "aklshp/akl_mainland_only.geojson"
    
    # Create the grid (default 5000m x 5000m)
    grid = create_grid(
        geojson_path=geojson_file,
        output_path='aklshp/auckland_grid_5000m.geojson',
        grid_size=5000,  # Can change to any size in meters
        crs='EPSG:32760'  # UTM Zone 60S for Auckland
    )
    
    print("\nFirst few patches:")
    print(grid.head())