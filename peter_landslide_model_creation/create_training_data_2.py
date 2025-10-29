import geopandas as gpd
from shapely.geometry import box, mapping
from datetime import datetime, timedelta
import pandas as pd
from sklearn.cluster import DBSCAN
import numpy as np
import os
import ee
project_name = "geog761-peag224"

def parse_geojson(path):
    gdf = gpd.read_file(path)
    gdf['event_date'] = pd.to_datetime(gdf['event_date'])
    gdf = gdf[gdf.is_valid]
    return gdf


def group_nearby_landslides(gdf, epsilon=5000):
    """
    Group nearby landslides using DBSCAN and create bounding boxes efficiently.
    Clusters landslides WITHIN each event_date separately.

    Parameters:
    gdf: GeoDataFrame
        Input landslide points or polygons.
    epsilon: float
        Distance threshold (in meters) for clustering.

    Returns:
    gdf_grouped: GeoDataFrame
        Dissolved landslides by event_date and cluster.
    bbox_gdf: GeoDataFrame
        Bounding boxes around each cluster.
    """

    output_dir = "peter_landslide_model_creation"
    os.makedirs(output_dir, exist_ok=True)

    # --- Reproject to Web Mercator (meters) ---
    gdf_m = gdf.to_crs(3857)

    # --- Cluster within each event_date separately ---
    print("Clustering landslides by date...")
    cluster_results = []
    
    for event_date, group in gdf_m.groupby('event_date'):
        # Get centroid coordinates for this date's landslides
        x = group.geometry.centroid.x.values
        y = group.geometry.centroid.y.values
        coords = np.column_stack((x, y))
        
        # Cluster with DBSCAN
        db = DBSCAN(eps=epsilon, min_samples=1, algorithm='kd_tree').fit(coords)
        
        # Add cluster labels to this group
        group_copy = group.copy()
        group_copy['cluster'] = db.labels_
        cluster_results.append(group_copy)
        
        print(f"  {event_date.date()}: {len(group)} landslides -> {len(set(db.labels_))} clusters")
    
    # Combine all results
    gdf_m = pd.concat(cluster_results, ignore_index=True)

    # --- Dissolve by event_date + cluster ---
    print("Grouping landslides...")
    gdf_grouped_m = gdf_m.dissolve(by=['event_date', 'cluster']).reset_index()

    # --- Create bounding boxes efficiently ---
    print("Creating bounding boxes...")
    gdf_grouped_m['bbox'] = gdf_grouped_m.bounds.apply(
        lambda row: box(row.minx, row.miny, row.maxx, row.maxy), axis=1
    )

    # --- Convert back to geographic coordinates ---
    gdf_grouped = gdf_grouped_m.to_crs(4326)
    bbox_gdf = gpd.GeoDataFrame(
        gdf_grouped[['event_date', 'cluster']],
        geometry=gdf_grouped['bbox'],
        crs="EPSG:4326"
    )

    # --- Save results ---
    landslides_path = os.path.join(output_dir, "grouped_landslides.geojson")
    bboxes_path = os.path.join(output_dir, "grouped_bboxes.geojson")

    gdf_grouped.drop(columns='bbox').to_file(landslides_path, driver="GeoJSON")
    bbox_gdf.to_file(bboxes_path, driver="GeoJSON")

    print(f"Saved {landslides_path} and {bboxes_path}.")
    return gdf_grouped, bbox_gdf


def get_landslides():
    try:
        gdf = gpd.read_file("peter_landslide_model_creation/grouped_landslides.geojson")
        bbox_gdf = gpd.read_file("peter_landslide_model_creation/grouped_bboxes.geojson")
        print("Loaded previously grouped landslides.")
    except:
        print("Grouped files not found, processing raw data...")
        gdf = parse_geojson("peter_landslide_model_creation/akl_landslides.geojson")
        gdf, bbox_gdf = group_nearby_landslides(gdf, epsilon=5000)
    
    return gdf, bbox_gdf

def get_s2_image(geometry, start_date, end_date, s2_bands=['B2','B3','B4','B8','B11','B12']):
    if end_date < pd.to_datetime("2017-03-28"):
        print("Sentinel-2A data available from June 27, 2015 to March 28, 2017.")
        s2 = (
            ee.ImageCollection("COPERNICUS/S2_HARMONIZED")
            .filterBounds(geometry)
            .filterDate(start_date, end_date)
            .select(s2_bands)
        )
        cloud = False
    else:
        s2 = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(geometry)
            .filterDate(start_date, end_date)
            .select(s2_bands)
        )
        cloud = True
        if s2.size().getInfo() == 0:
            print("No images found. Trying Sentinel-2A ")
            s2 = (
                ee.ImageCollection("COPERNICUS/S2_HARMONIZED")
                .filterBounds(geometry)
                .filterDate(start_date, end_date)
                .select(s2_bands)
            )
            cloud = False

    # Check if collection is empty
    if s2.size().getInfo() == 0:
        return None

    # Sort by cloud coverage percentage (lowest first) and get the first (lowest cloud) image
    if cloud:
        s2_sorted = s2.sort("CLOUDY_PIXEL_PERCENTAGE")
        lowest_cloud_image = s2_sorted.first()
        cloud_percent = lowest_cloud_image.get("CLOUDY_PIXEL_PERCENTAGE").getInfo()
        print(f"Selected image with {cloud_percent:.2f}% cloud coverage")
    else:
        s2_sorted = s2.sort("system:time_start", False)  # Get most recent if no cloud info
        lowest_cloud_image = s2_sorted.first()
        print("Selected most recent image (no cloud percentage available)")

    # Clip to geometry
    clipped_image = lowest_cloud_image.clip(geometry)
    return clipped_image

def get_s1_image(geometry, start_date, end_date):
    s1 = (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filterBounds(geometry)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .sort("system:time_start", False)
    )

    # Check if collection is empty
    if s1.size().getInfo() == 0:
        return None

    # Get the most recent image
    most_recent = s1.first().clip(geometry)
    return most_recent

def create_128x128_bbox(bbox_geom):
    """
    Create a 128x128 pixel bounding box centered on the input geometry.
    At 10m resolution, this equals 1280m x 1280m.
    
    Parameters:
    bbox_geom: shapely.geometry.Polygon
        Bounding box in Web Mercator (EPSG:3857) with meters
    
    Returns:
    shapely.geometry.Polygon
        128x128 pixel bounding box (1280m x 1280m)
    """
    bounds = bbox_geom.bounds
    minx, miny, maxx, maxy = bounds
    
    # Get center point
    center_x = (minx + maxx) / 2
    center_y = (miny + maxy) / 2
    
    # Size in meters for 128 pixels at 10m resolution
    size = 128 * 10  # 1280 meters
    half_size = size / 2
    
    # Create new bbox centered on original
    new_minx = center_x - half_size
    new_maxx = center_x + half_size
    new_miny = center_y - half_size
    new_maxy = center_y + half_size
    
    return box(new_minx, new_miny, new_maxx, new_maxy)

def pull_sentinel_data(bbox, start_date, end_date):
    """
    Pull Sentinel-1 and Sentinel-2 data for a 128x128 pixel area.

    Parameters:
    bbox: shapely.geometry.Polygon
        Bounding box for the area of interest (in EPSG:3857).
    start_date: datetime
        Start date for data retrieval.
    end_date: datetime
        End date for data retrieval.

    Returns:
    tuple or None: (s1_image, s2_image, ee_geometry, shapely_geometry_4326)
    """
    
    # Create 128x128 pixel bbox (1280m x 1280m at 10m resolution)
    bbox_128 = create_128x128_bbox(bbox)
    
    print(f"Pulling Sentinel data for 128x128 pixel bbox from {start_date} to {end_date}...")
    
    if end_date < pd.to_datetime("2015-06-27"):
        print("No Sentinel-2 data available before June 27, 2015.")
        return None
    
    # Convert to GeoSeries so you can reproject
    gdf = gpd.GeoSeries([bbox_128], crs="EPSG:3857")

    # Reproject to geographic CRS (WGS84)
    gdf_4326 = gdf.to_crs(epsg=4326)

    # Convert to GeoJSON-like dict
    geojson_dict = mapping(gdf_4326.iloc[0])

    # Convert to Earth Engine Geometry
    geometry = ee.Geometry(geojson_dict)
    s2 = get_s2_image(geometry, start_date, end_date)
    s1 = get_s1_image(geometry, start_date, end_date)
    if s1 is not None and s2 is not None:
        # Return the Shapely geometry as well for mask creation
        return s1, s2, geometry, gdf_4326.iloc[0]
    else:
        return None

def create_mask(idx, gdf, ee_geometry, shapely_geometry):
    """
    Create and export a GeoTIFF landslide mask where:
    - 0 = non-landslide area
    - 1 = landslide area
    - Resolution = 128x128 pixels
    
    Returns True if landslide exists in the region, False otherwise.
    
    Parameters:
    idx : int
        Index of the landslide in gdf to rasterize
    gdf : GeoDataFrame
        GeoDataFrame containing landslide geometries
    ee_geometry : ee.Geometry
        Earth Engine geometry for the bounding region
    shapely_geometry : shapely.geometry.Polygon or MultiPolygon
        Shapely geometry for the bounding area
    """

    # Extract single landslide geometry
    landslide_geom = gdf.iloc[idx].geometry
    
    # Check if landslide intersects with the bounding box
    if not landslide_geom.intersects(shapely_geometry):
        print(f"Patch {idx}: No landslide in this region, skipping...")
        return False
    
    # Simplify geometry to reduce payload size (10m tolerance matches export resolution)
    landslide_geom_simplified = landslide_geom.simplify(tolerance=0.0001, preserve_topology=True)
    
    print(f"Original geometry vertices: ~{len(mapping(landslide_geom)['coordinates'])} | "
          f"Simplified: ~{len(mapping(landslide_geom_simplified)['coordinates'])}")
    
    # Convert simplified geometry to EE
    landslide_ee_geom = ee.Geometry(mapping(landslide_geom_simplified))
    
    # Create a constant image with value 1 for landslide areas
    # Paint the landslide geometry with value 1
    landslide_image = ee.Image().byte().paint(
        featureCollection=ee.FeatureCollection([ee.Feature(landslide_ee_geom)]),
        color=1
    )
    
    # Create base image with value 0 for non-landslide areas
    # unmask(0) fills all unpainted pixels with 0
    mask_image = landslide_image.unmask(0).rename('landslide_mask')
    
    # Clip to the region
    mask_image = mask_image.clip(ee_geometry)
    
    # Get statistics to verify the mask has values
    stats = mask_image.reduceRegion(
        reducer=ee.Reducer.minMax(),
        geometry=ee_geometry,
        scale=10,
        maxPixels=1e13
    ).getInfo()
    
    print(f"Patch {idx} mask statistics: {stats}")
    
    # Check if there's actually any landslide pixels (max should be 1)
    if stats.get('landslide_mask_max', 0) == 0:
        print(f"Patch {idx}: No landslide pixels in mask, skipping...")
        return False
    
    # Export GeoTIFF to masks folder
    task = ee.batch.Export.image.toDrive(
        image=mask_image.toByte(),
        description=f'mask_{idx}',
        folder='masks',
        fileNamePrefix=f'patch_{idx}',
        region=ee_geometry,
        crs='EPSG:4326',
        fileFormat='GeoTIFF',
        maxPixels=1e13,
        dimensions='128x128'
    )
    
    task.start()
    print(f"Exporting mask for patch {idx} to Drive/masks/...")
    return True

def create_training_data(gdf, bbox_gdf):
    for idx, row in bbox_gdf.iterrows():
        event_date = row['event_date']
        bbox = row['geometry']
        start_date = event_date
        end_date = event_date + timedelta(days=60)
        images = pull_sentinel_data(bbox, start_date, end_date)
        if images is None:
            print(f"Patch {idx}: No Sentinel data found for event date: {event_date}")
            continue
        else:
            s1_image, s2_image, ee_geometry, shapely_geometry = images
            print(f"Patch {idx}: Retrieved Sentinel data for event date: {event_date}")
            
            # Check if there's a landslide in this region first
            has_landslide = create_mask(idx, gdf, ee_geometry, shapely_geometry)
            
            if not has_landslide:
                print(f"Patch {idx}: Skipping image export (no landslide present)")
                continue
            
            # Only export image if landslide exists
            # Convert both images to Float32 to ensure compatibility
            s1_image = s1_image.toFloat()
            s2_image = s2_image.toFloat()
            
            # Stack the images
            stacked = s1_image.addBands(s2_image)
            
            # Export the stacked images as 128x128 pixels to images folder
            task = ee.batch.Export.image.toDrive(
                image=stacked,
                description=f'image_{idx}',
                folder='images',
                fileNamePrefix=f'patch_{idx}',
                region=ee_geometry,
                crs='EPSG:4326',
                fileFormat='GeoTIFF',
                maxPixels=1e13,
                dimensions='128x128'
            )
            task.start()
            print(f"Exporting image for patch {idx} to Drive/images/...")
    return

if __name__ == "__main__":
    gdf, bbox_gdf = get_landslides()
    ee.Initialize(project = project_name)
    create_training_data(gdf, bbox_gdf)