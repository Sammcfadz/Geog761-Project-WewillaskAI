import json
from shapely.geometry import shape, mapping, MultiPolygon, Polygon

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

print(f"Found {len(geometries)} initial geometries")

# Explode MultiPolygons into individual Polygons
all_polygons = []
for geom in geometries:
    if isinstance(geom, MultiPolygon):
        all_polygons.extend(list(geom.geoms))
        print(f"Exploded MultiPolygon into {len(geom.geoms)} polygons")
    elif isinstance(geom, Polygon):
        all_polygons.append(geom)

print(f"Total polygons: {len(all_polygons)}")

# Sort by area and show top 5
sorted_polygons = sorted(all_polygons, key=lambda g: g.area, reverse=True)
print("\nTop 5 largest polygons:")
for i in range(min(5, len(sorted_polygons))):
    print(f"  {i+1}. Area: {sorted_polygons[i].area:.8f} sq degrees")

# Get the largest polygon (mainland)
largest = sorted_polygons[0]
print(f"\nSelected largest polygon: {largest.area:.6f} sq degrees")

# Simplify to reduce size
# Start with minimal simplification
tolerance = 0.0001  # ~10m
print(f"Simplifying with tolerance {tolerance}...")
simplified = largest.simplify(tolerance, preserve_topology=True)

print(f"Original vertices: {len(largest.exterior.coords)}")
print(f"Simplified vertices: {len(simplified.exterior.coords)}")

# Convert to GeoJSON
mainland_geojson = {
    "type": "Feature",
    "properties": {"name": "Auckland Mainland"},
    "geometry": mapping(simplified),
}

# Save to file
output_file = "aklshp/akl_mainland_only.geojson"
print(f"\nSaving mainland geometry to {output_file}...")
with open(output_file, "w") as f:
    json.dump(mainland_geojson, f)

# Check file size
import os

file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
print(f"File size: {file_size_mb:.2f} MB")

if file_size_mb > 5:
    print(
        f"WARNING: File is still large. Consider increasing tolerance to 0.0005 or 0.001"
    )
else:
    print("File size is good for Earth Engine!")

print(f"\nDone! Saved to {output_file}")
