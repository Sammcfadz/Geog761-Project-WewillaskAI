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

import ee


def get_s1_image(geometry, start_date, end_date, orbit="ASCENDING", polarization="VV"):
    """
    Get Sentinel-1 SAR image(s) covering a geometry and date range.

    Parameters:
    -----------
    geometry : ee.Geometry
        The area of interest to cover
    start_date : str
        Start date in 'YYYY-MM-DD' format
    end_date : str
        End date in 'YYYY-MM-DD' format
    orbit : str, optional
        Orbit direction: 'ASCENDING' or 'DESCENDING' (default: 'ASCENDING')
    polarization : str, optional
        Polarization mode: 'VV', 'VH', 'VV+VH' (default: 'VV')

    Returns:
    --------
    ee.Image
        A mosaic of Sentinel-1 images covering the entire geometry
    """

    # Load Sentinel-1 Ground Range Detected collection
    s1 = (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filterBounds(geometry)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.eq("instrumentMode", "IW"))  # Interferometric Wide swath mode
        .filter(ee.Filter.eq("orbitProperties_pass", orbit))
    )

    # Filter by polarization
    if polarization == "VV":
        s1 = s1.filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
        s1 = s1.select("VV")
    elif polarization == "VH":
        s1 = s1.filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
        s1 = s1.select("VH")
    elif polarization == "VV+VH":
        s1 = s1.filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
        s1 = s1.filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
        s1 = s1.select(["VV", "VH"])

    # Create a mosaic to cover the entire geometry
    # Take the median to reduce speckle noise
    mosaic = s1.median().clip(geometry)

    return mosaic


# Example usage:
# Initialize Earth Engine (run once)
# ee.Initialize()

# Define your area of interest
# geometry = ee.Geometry.Rectangle([lon_min, lat_min, lon_max, lat_max])
# or
# geometry = ee.Geometry.Point([lon, lat]).buffer(10000)  # 10km buffer

# Get the image
# image = get_s1_image(geometry, '2024-01-01', '2024-12-31', orbit='ASCENDING', polarization='VV+VH')

# Visualize VV band
# vis_params_vv = {
#     'bands': ['VV'],
#     'min': -25,
#     'max': 0
# }
# Map.addLayer(image, vis_params_vv, 'S1 VV')

# Visualize VH band
# vis_params_vh = {
#     'bands': ['VH'],
#     'min': -25,
#     'max': 0
# }
# Map.addLayer(image, vis_params_vh, 'S1 VH')

# Visualize RGB composite (VV, VH, VV/VH ratio)
# ratio = image.select('VV').divide(image.select('VH')).rename('VV_VH_ratio')
# composite = image.addBands(ratio)
# vis_params_rgb = {
#     'bands': ['VV', 'VH', 'VV_VH_ratio'],
#     'min': [-25, -25, 0],
#     'max': [0, 0, 2]
# }
# Map.addLayer(composite, vis_params_rgb, 'S1 RGB Composite')
