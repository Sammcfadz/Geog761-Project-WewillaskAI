import json
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

# Read the GeoJSON file
print("Reading GeoJSON file...")
with open("aklshp/akl_shape.geojson", "r") as f:
    geojson_data = json.load(f)

# Extract all geometries
print("Extracting geometries...")
geometries = []

if geojson_data["type"] == "FeatureCollection":
    for feature in geojson_data["features"]:
        geom = shape(feature["geometry"])
        geometries.append(geom)
elif geojson_data["type"] == "Feature":
    geom = shape(geojson_data["geometry"])
    geometries.append(geom)
else:
    geom = shape(geojson_data)
    geometries.append(geom)

# Find the largest polygon by area
print(f"Found {len(geometries)} geometries. Finding largest...")
largest = max(geometries, key=lambda g: g.area)

print(f"Largest polygon area: {largest.area:.2f} square degrees")
print(f"Geometry type: {largest.geom_type}")

# Simplify to reduce size (adjust tolerance as needed)
# tolerance in degrees - 0.001 ≈ 100m, 0.0001 ≈ 10m
print("Simplifying geometry...")
simplified = largest.simplify(0.0001, preserve_topology=True)

print(
    f"Original vertices: ~{len(largest.exterior.coords) if hasattr(largest, 'exterior') else 'unknown'}"
)
print(
    f"Simplified vertices: ~{len(simplified.exterior.coords) if hasattr(simplified, 'exterior') else 'unknown'}"
)

# Convert to GeoJSON
north_island_geojson = {
    "type": "Feature",
    "properties": {},
    "geometry": mapping(simplified),
}

# Save to file
print("Saving new geometry...")
with open("aklshp/akl_refined.geojson", "w") as f:
    json.dump(north_island_geojson, f)
