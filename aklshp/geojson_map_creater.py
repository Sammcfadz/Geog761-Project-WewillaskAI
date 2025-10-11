import json
import folium
from shapely.geometry import shape

# Read the GeoJSON file
geojson_path = "aklshp/akl_refined.geojson"

with open(geojson_path) as f:
    geojson_data = json.load(f)

# Get the geometry to calculate center
geom = shape(geojson_data["geometry"])
bounds = geom.bounds  # (minx, miny, maxx, maxy)
center_lat = (bounds[1] + bounds[3]) / 2
center_lon = (bounds[0] + bounds[2]) / 2

# Create map centered on the geometry
m = folium.Map(location=[center_lat, center_lon], zoom_start=6, tiles="OpenStreetMap")

# Add the GeoJSON layer
folium.GeoJson(
    geojson_data,
    name="North Island",
    style_function=lambda x: {
        "fillColor": "#3388ff",
        "color": "#000000",
        "weight": 2,
        "fillOpacity": 0.3,
    },
).add_to(m)

# Fit bounds to the geometry
m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

# Add layer control
folium.LayerControl().add_to(m)

# Save to HTML file
m.save("map.html")
print("Map saved to map.html - open it in your browser!")
