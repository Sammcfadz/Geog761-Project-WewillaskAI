import geopandas as gpd

# Load shapefile
gdf = gpd.read_file("aklshp/nasa_coolr_events_poly.shp")

# Check current CRS
print(f"Original CRS: {gdf.crs}")

# Reproject to WGS84 (EPSG:4326) - latitude/longitude
gdf_wgs84 = gdf.to_crs(epsg=4326)

print(f"Reprojected CRS: {gdf_wgs84.crs}")
print(f"Number of features: {len(gdf_wgs84)}")

# Check the bounds (should be around Auckland's lat/lon now)
print(f"Bounds: {gdf_wgs84.total_bounds}")
# Should be roughly: [174.x, -37.x, 175.x, -36.x] for Auckland

# Save to GeoJSON
gdf_wgs84.to_file("aklshp/akl_landslides.geojson", driver="GeoJSON")
