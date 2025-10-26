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
            print("No images found. Tryinf Sentinel-2A ")
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

def pull_sentinel_data(bbox, start_date, end_date, max_cloud_percent=100):
    """
    Placeholder function to pull Sentinel-2 data for a given bounding box and date range.
    In a real implementation, this would interface with an API or data repository.

    Parameters:
    bbox: shapely.geometry.Polygon
        Bounding box for the area of interest.
    start_date: datetime
        Start date for data retrieval.
    end_date: datetime
        End date for data retrieval.

    Returns:
    None
    """
    print(f"Pulling Sentinel-2 data for bbox {bbox.bounds} from {start_date} to {end_date}...")
    if end_date < pd.to_datetime("2015-06-27"):
        print("No Sentinel-2 data available before June 27, 2015.")
        return None
    # Convert to GeoSeries so you can reproject
    gdf = gpd.GeoSeries([bbox], crs="EPSG:3857")

    # Reproject to geographic CRS (WGS84)
    gdf_4326 = gdf.to_crs(epsg=4326)

    # Convert to GeoJSON-like dict
    geojson_dict = mapping(gdf_4326.iloc[0])

    # Convert to Earth Engine Geometry
    geometry = ee.Geometry(geojson_dict)
    s2 = get_s2_image(geometry, start_date, end_date, max_cloud_percent)
    s1 = get_s1_image(geometry, start_date, end_date)
    if s1 is not None and s2 is not None:
        return s1, s2, geometry
    else:
        return None

def create_mask(idx, gdf):
    landslide = gdf.iloc[idx]
    geometry = landslide['geometry']
    event_date = landslide['event_date']
    print(f"Creating mask for landslide on {event_date}...")
    
    # Keep geometry in EPSG:4326 - no reprojection needed
    gdf_geom = gpd.GeoSeries([geometry], crs="EPSG:4326")

    # Convert to GeoJSON-like dict (already in EPSG:4326)
    geojson_dict = mapping(gdf_geom.iloc[0])

    # Convert to Earth Engine Geometry
    ee_geometry = ee.Geometry(geojson_dict)

    # Create a raster mask where landslide area is 1 and non-landslide area is 0
    mask_image = ee.Image().byte().paint(ee_geometry, 1).rename('landslide_mask')

    # Export the mask image to Google Drive
    task = ee.batch.Export.image.toDrive(
        image=mask_image,
        description=f'mask_{idx}',
        folder='TrainingData',
        fileNamePrefix=f'landslide_mask_{idx}',
        region=ee_geometry,
        scale=10,
        crs='EPSG:4326',
        fileFormat='GeoTIFF'
    )
    task.start()
    print(f"Exporting mask for landslide {idx}...")
    return

def create_training_data(gdf, bbox_gdf):
    for idx, row in bbox_gdf.iterrows():
        event_date = row['event_date']
        bbox = row['geometry']
        start_date = event_date
        end_date = event_date + timedelta(days=60)
        images = pull_sentinel_data(bbox, start_date, end_date)
        if images is None:
            print("No Sentinel data found for event date:", event_date)
            continue
        else:
            s1_image, s2_image, geometry = images
            print("Retrieved Sentinel data for event date:", event_date)
            
            # Convert both images to Float32 to ensure compatibility
            s1_image = s1_image.toFloat()
            s2_image = s2_image.toFloat()
            
            # Stack the images
            stacked = s1_image.addBands(s2_image)
            
            task = ee.batch.Export.image.toDrive(
                image=stacked,
                description=f'image_{idx}',
                folder='TrainingData',
                fileNamePrefix=f's1s2_combined_{idx}',
                region=geometry,
                scale=10,
                crs='EPSG:4326',
                fileFormat='GeoTIFF'
            )
            task.start()
            create_mask(idx, gdf)
    return

if __name__ == "__main__":
    gdf, bbox_gdf = get_landslides()
    ee.Initialize(project = project_name)
    s1_image, s2_image = create_training_data(gdf, bbox_gdf)
