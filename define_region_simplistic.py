def create_simplistic_region():
    """
    Create a simplistic rectangular bounding region around Muriwai (Auckland) in Google Earth Engine.
    Returns:
        ee.Geometry.Polygon: The rectangle geometry
    """
    # Approx center of Muriwai Beach
    center_lat = -36.83
    center_lon = 174.45

    # Half-size of rectangle in degrees (~3 km in each direction)
    half_height_deg = 0.03
    half_width_deg  = 0.03

    min_lat = center_lat - half_height_deg
    max_lat = center_lat + half_height_deg
    min_lon = center_lon - half_width_deg
    max_lon = center_lon + half_width_deg

    # Create a rectangle in GEE (lon, lat order)
    region = ee.Geometry.Rectangle([min_lon, min_lat, max_lon, max_lat])

    return region