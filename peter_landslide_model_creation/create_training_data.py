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

    # --- Use centroid coordinates for clustering ---
    x = gdf_m.geometry.centroid.x.values
    y = gdf_m.geometry.centroid.y.values
    coords = np.column_stack((x, y))

    # --- Cluster with DBSCAN ---
    db = DBSCAN(eps=epsilon, min_samples=1, algorithm='kd_tree').fit(coords)
    gdf_m['cluster'] = db.labels_

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

def get_s2_image(geometry, start_date, end_date, max_cloud_percent=100, s2_bands=['B2','B3','B4','B8','B11','B12']):
    if end_date < pd.to_datetime("2017-03-28"):
        print("Sentinel-2A data available from June 27, 2015 to March 28, 2017.")
        s2 = (
            ee.ImageCollection("COPERNICUS/S2_HARMONIZED")
            .filterBounds(geometry)\
            .filterDate(start_date, end_date)
            .select(s2_bands)
        )
        cloud =False
    else:
        s2 = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(geometry)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", max_cloud_percent))
            .select(s2_bands)
        )
        cloud = True
        if s2.size().getInfo() == 0:
            print("No images found. Trying Sentinel-2A ")
            s2 = (
                ee.ImageCollection("COPERNICUS/S2_HARMONIZED")
                .filterBounds(geometry)\
                .filterDate(start_date, end_date)
                .select(s2_bands)
            )
            cloud =False

    # Check if collection is empty
    if s2.size().getInfo() == 0:
        return None, None

    # Sort by cloud coverage percentage (lowest first)
    if cloud:
        s2_sorted = s2.sort("CLOUDY_PIXEL_PERCENTAGE")
    else:
        s2_sorted = s2 

    # Create a mosaic to cover the entire geometry
    # This will use the least cloudy images first to fill in the mosaic
    mosaic = s2_sorted.mosaic().clip(geometry)
    return mosaic

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

    # Sort by date (most recent first)
    s1_sorted = s1.sort("system:time_start", False)

    # Create a mosaic to cover the entire geometry
    mosaic = s1_sorted.mosaic().clip(geometry)
    return mosaic

def constrain_bbox_size(bbox_geom, min_size=1000, max_size=5000):
    """
    Constrain bounding box to be between min_size and max_size meters.
    
    Parameters:
    bbox_geom: shapely.geometry.Polygon
        Bounding box in Web Mercator (EPSG:3857) with meters
    min_size: float
        Minimum size in meters (default 1000m = 1km)
    max_size: float
        Maximum size in meters (default 5000m = 5km)
    
    Returns:
    shapely.geometry.Polygon
        Adjusted bounding box
    """
    bounds = bbox_geom.bounds
    minx, miny, maxx, maxy = bounds
    
    width = maxx - minx
    height = maxy - miny
    
    # Get center point
    center_x = (minx + maxx) / 2
    center_y = (miny + maxy) / 2
    
    # Adjust width
    if width < min_size:
        new_width = min_size
    elif width > max_size:
        new_width = max_size
    else:
        new_width = width
    
    # Adjust height
    if height < min_size:
        new_height = min_size
    elif height > max_size:
        new_height = max_size
    else:
        new_height = height
    
    # Create new bbox centered on original
    new_minx = center_x - new_width / 2
    new_maxx = center_x + new_width / 2
    new_miny = center_y - new_height / 2
    new_maxy = center_y + new_height / 2
    
    return box(new_minx, new_miny, new_maxx, new_maxy)

def pull_sentinel_data(bbox, start_date, end_date, max_cloud_percent=100):
    """
    Pull Sentinel-1 and Sentinel-2 data for a given bounding box and date range.
    Constrains bbox to be between 1km x 1km and 5km x 5km.

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
    
    # Constrain bbox size (bbox is in EPSG:3857 - meters)
    constrained_bbox = constrain_bbox_size(bbox, min_size=1000, max_size=5000)
    
    print(f"Pulling Sentinel-2 data for bbox {constrained_bbox.bounds} from {start_date} to {end_date}...")
    
    if end_date < pd.to_datetime("2015-06-27"):
        print("No Sentinel-2 data available before June 27, 2015.")
        return None
    
    # Convert to GeoSeries so you can reproject
    gdf = gpd.GeoSeries([constrained_bbox], crs="EPSG:3857")

    # Reproject to geographic CRS (WGS84)
    gdf_4326 = gdf.to_crs(epsg=4326)

    # Convert to GeoJSON-like dict
    geojson_dict = mapping(gdf_4326.iloc[0])

    # Convert to Earth Engine Geometry
    geometry = ee.Geometry(geojson_dict)
    s2 = get_s2_image(geometry, start_date, end_date, max_cloud_percent)
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
    - Resolution = 10m
    - Extent = ee_geometry (bounding region)
    
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
    
    print(f"Mask {idx} statistics: {stats}")
    
    # Export GeoTIFF
    task = ee.batch.Export.image.toDrive(
        image=mask_image.toByte(),
        description=f'mask_{idx}',
        folder='TrainingData',
        fileNamePrefix=f'landslide_mask_{idx}',
        region=ee_geometry,
        scale=10,
        crs='EPSG:4326',
        fileFormat='GeoTIFF',
        maxPixels=1e13
    )
    
    task.start()
    print(f"Exporting landslide mask {idx} to Drive...")

def create_training_data(gdf, bbox_gdf):
    for idx, row in bbox_gdf.iterrows():
        if idx != 6:
            continue
        event_date = row['event_date']
        bbox = row['geometry']
        start_date = event_date
        end_date = event_date + timedelta(days=60)
        images = pull_sentinel_data(bbox, start_date, end_date)
        if images is None:
            print("No Sentinel data found for event date:", event_date)
            continue
        else:
            s1_image, s2_image, ee_geometry, shapely_geometry = images
            print("Retrieved Sentinel data for event date:", event_date)
            
            # Convert both images to Float32 to ensure compatibility
            s1_image = s1_image.toFloat()
            s2_image = s2_image.toFloat()
            
            # Stack the images
            stacked = s1_image.addBands(s2_image)
            
            # Uncomment to export the stacked images
            task = ee.batch.Export.image.toDrive(
                image=stacked,
                description=f'image_{idx}',
                folder='TrainingData',
                fileNamePrefix=f's1s2_combined_{idx}',
                region=ee_geometry,
                scale=10,
                crs='EPSG:4326',
                fileFormat='GeoTIFF',
                maxPixels=1e13
            )
            task.start()
            
            create_mask(idx, gdf, ee_geometry, shapely_geometry)
    return

if __name__ == "__main__":
    gdf, bbox_gdf = get_landslides()
    ee.Initialize(project = project_name)
    create_training_data(gdf, bbox_gdf)