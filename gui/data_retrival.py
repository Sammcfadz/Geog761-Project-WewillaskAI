import ee


def get_s2_image(geometry, start_date, end_date, max_cloud_percent=20):
    """
    Get the most cloud-free Sentinel-2 image(s) covering a geometry and date range.

    Parameters:
    -----------
    geometry : ee.Geometry
        The area of interest to cover
    start_date : str
        Start date in 'YYYY-MM-DD' format
    end_date : str
        End date in 'YYYY-MM-DD' format
    max_cloud_percent : float, optional
        Maximum cloud coverage percentage to filter (default: 20)

    Returns:
    --------
    ee.Image
        A mosaic of the least cloudy Sentinel-2 images covering the entire geometry
    """

    # Load Sentinel-2 Surface Reflectance collection
    s2 = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(geometry)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", max_cloud_percent))
    )

    # Sort by cloud coverage percentage (lowest first)
    s2_sorted = s2.sort("CLOUDY_PIXEL_PERCENTAGE")

    # Create a mosaic to cover the entire geometry
    # This will use the least cloudy images first to fill in the mosaic
    mosaic = s2_sorted.mosaic().clip(geometry)

    return mosaic


# Example usage:
# Initialize Earth Engine (run once)
# ee.Initialize()

# Define your area of interest
# geometry = ee.Geometry.Rectangle([lon_min, lat_min, lon_max, lat_max])
# or
# geometry = ee.Geometry.Point([lon, lat]).buffer(10000)  # 10km buffer

# Get the image
# image = get_s2_image(geometry, '2024-01-01', '2024-12-31')

# Visualize
# vis_params = {
#     'bands': ['B4', 'B3', 'B2'],
#     'min': 0,
#     'max': 3000,
#     'gamma': 1.4
# }
# Map.addLayer(image, vis_params, 'S2 Image')
