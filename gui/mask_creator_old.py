import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
from datetime import datetime, timedelta
import ee
import folium
from folium import plugins
import base64
from io import BytesIO
import sys
import os
import json

# add parent directory (project root) to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ee.Authenticate()
ee.Initialize(project="geog761-peag224")

from data_retrival import *


# Initialize the Dash app
app = dash.Dash(__name__)

# Default coordinates (Auckland) - for map centering only
DEFAULT_LAT = -36.8485
DEFAULT_LON = 174.7633
DEFAULT_ZOOM = 10

# Your preset geometry - update this with your actual geometry
# Example: PRESET_GEOMETRY = ee.Geometry.Rectangle([174.5, -37.0, 175.0, -36.7])

geojson_path = r"aklshp\akl_mainland_only.geojson"
with open(geojson_path) as f:
    geojson_data = json.load(f)

# Convert to Earth Engine Feature
PRESET_GEOMETRY = ee.Geometry(geojson_data["geometry"])

app.layout = html.Div(
    [
        html.H1(
            "Sentinel-2 Satellite Imagery Viewer (Google Earth Engine)",
            style={"textAlign": "center", "marginBottom": "20px"},
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                html.Label("Start Date:", style={"fontWeight": "bold"}),
                                dcc.DatePickerSingle(
                                    id="start-date",
                                    date=(datetime.now() - timedelta(days=30)).date(),
                                    display_format="YYYY-MM-DD",
                                    style={"marginLeft": "10px"},
                                ),
                            ],
                            style={"display": "inline-block", "marginRight": "20px"},
                        ),
                        html.Div(
                            [
                                html.Label("End Date:", style={"fontWeight": "bold"}),
                                dcc.DatePickerSingle(
                                    id="end-date",
                                    date=datetime.now().date(),
                                    display_format="YYYY-MM-DD",
                                    style={"marginLeft": "10px"},
                                ),
                            ],
                            style={"display": "inline-block", "marginRight": "20px"},
                        ),
                        html.Div(
                            [
                                html.Label(
                                    "Max Cloud Cover (%):", style={"fontWeight": "bold"}
                                ),
                                dcc.Input(
                                    id="cloud-cover",
                                    type="number",
                                    value=50,
                                    min=0,
                                    max=100,
                                    style={"marginLeft": "10px", "width": "100px"},
                                ),
                            ],
                            style={"display": "inline-block", "marginRight": "20px"},
                        ),
                        html.Div(
                            [
                                html.Label(
                                    "Visualization:", style={"fontWeight": "bold"}
                                ),
                                dcc.Dropdown(
                                    id="vis-type",
                                    options=[
                                        {"label": "True Color (RGB)", "value": "rgb"},
                                        {
                                            "label": "False Color (NIR)",
                                            "value": "false_color",
                                        },
                                        {"label": "NDVI", "value": "ndvi"},
                                        {"label": "NDWI (Water)", "value": "ndwi"},
                                    ],
                                    value="rgb",
                                    style={"width": "200px", "marginLeft": "10px"},
                                ),
                            ],
                            style={"display": "inline-block", "marginRight": "20px"},
                        ),
                        html.Button(
                            "Load Imagery",
                            id="load-button",
                            n_clicks=0,
                            style={
                                "marginLeft": "10px",
                                "padding": "10px 20px",
                                "fontSize": "16px",
                                "cursor": "pointer",
                                "backgroundColor": "#007bff",
                                "color": "white",
                                "border": "none",
                                "borderRadius": "5px",
                            },
                        ),
                    ],
                    style={"textAlign": "center", "marginBottom": "20px"},
                ),
            ],
            style={
                "backgroundColor": "#f0f0f0",
                "padding": "20px",
                "borderRadius": "5px",
            },
        ),
        html.Div(
            id="status-message",
            style={
                "textAlign": "center",
                "marginTop": "10px",
                "fontSize": "14px",
                "minHeight": "40px",
            },
        ),
        html.Iframe(
            id="map", style={"width": "100%", "height": "700px", "border": "none"}
        ),
        dcc.Store(id="current-image-url"),
    ]
)


def get_ee_image_url(image: ee.Image, geometry: ee.Geometry, vis_params: dict) -> str:
    """Get a tile URL for an Earth Engine image."""
    map_id = image.getMapId(vis_params)
    return map_id["tile_fetcher"].url_format


def create_folium_map(lat, lon, zoom, image_url=None, geometry=None):
    """Create a Folium map with optional Sentinel-2 overlay."""
    m = folium.Map(
        location=[lat, lon], zoom_start=zoom, tiles="OpenStreetMap", control_scale=True
    )

    # Add additional tile layers
    folium.TileLayer("Stamen Terrain", name="Terrain").add_to(m)
    folium.TileLayer("CartoDB positron", name="Light").add_to(m)

    if image_url:
        # Add Sentinel-2 imagery as a tile layer
        folium.TileLayer(
            tiles=image_url,
            attr="Sentinel-2 (Google Earth Engine)",
            name="Sentinel-2",
            overlay=True,
            control=True,
            opacity=0.8,
        ).add_to(m)

    # Add geometry boundary if provided
    if geometry:
        try:
            geom_json = geometry.getInfo()
            folium.GeoJson(
                geom_json,
                name="Area of Interest",
                style_function=lambda x: {
                    "fillColor": "transparent",
                    "color": "red",
                    "weight": 2,
                    "dashArray": "5, 5",
                },
            ).add_to(m)
        except:
            pass

    # Add layer control
    folium.LayerControl().add_to(m)

    # Add coordinates on click
    m.add_child(folium.LatLngPopup())

    # Add fullscreen option
    plugins.Fullscreen().add_to(m)

    # Save map to HTML string
    map_html = m._repr_html_()
    return map_html


def get_visualization_params(vis_type: str) -> dict:
    """Get visualization parameters based on selected type."""
    vis_params = {
        "rgb": {"bands": ["B4", "B3", "B2"], "min": 0, "max": 3000, "gamma": 1.4},
        "false_color": {
            "bands": ["B8", "B4", "B3"],
            "min": 0,
            "max": 3000,
            "gamma": 1.4,
        },
        "ndvi": {"min": -1, "max": 1, "palette": ["red", "yellow", "green"]},
        "ndwi": {"min": -1, "max": 1, "palette": ["white", "blue"]},
    }
    return vis_params.get(vis_type, vis_params["rgb"])


@app.callback(
    [Output("map", "srcDoc"), Output("status-message", "children")],
    [Input("load-button", "n_clicks")],
    [
        State("start-date", "date"),
        State("end-date", "date"),
        State("cloud-cover", "value"),
        State("vis-type", "value"),
    ],
)
def update_map(n_clicks, start_date, end_date, cloud_cover, vis_type):
    if n_clicks == 0:
        # Initial map with preset geometry
        initial_map = create_folium_map(DEFAULT_LAT, DEFAULT_LON, DEFAULT_ZOOM)
        return (
            initial_map,
            "Select date range and click 'Load Imagery' to fetch Sentinel-2 data",
        )

    try:
        status_msgs = []
        status_msgs.append(
            html.Div(
                "🔄 Fetching Sentinel-2 imagery...",
                style={"color": "blue", "fontWeight": "bold"},
            )
        )

        # Use preset geometry
        geometry = PRESET_GEOMETRY

        status_msgs.append(html.Div(f"📅 Date Range: {start_date} to {end_date}"))
        status_msgs.append(html.Div(f"☁️ Max Cloud Cover: {cloud_cover}%"))

        # Get Sentinel-2 image using your function
        image = get_s2_image(
            geometry=geometry,
            start_date=start_date,
            end_date=end_date,
            max_cloud_percent=cloud_cover,
        )

        if image is None:
            error_map = create_folium_map(
                DEFAULT_LAT, DEFAULT_LON, DEFAULT_ZOOM, geometry=geometry
            )
            status_msgs.append(
                html.Div(
                    "❌ No suitable imagery found. Try adjusting the date range or cloud cover threshold.",
                    style={"color": "red", "fontWeight": "bold", "marginTop": "10px"},
                )
            )
            return error_map, html.Div(status_msgs)

        # Calculate index if needed
        if vis_type == "ndvi":
            nir = image.select("B8")
            red = image.select("B4")
            image = nir.subtract(red).divide(nir.add(red)).rename("NDVI")
        elif vis_type == "ndwi":
            green = image.select("B3")
            nir = image.select("B8")
            image = green.subtract(nir).divide(green.add(nir)).rename("NDWI")

        # Get visualization parameters
        vis_params = get_visualization_params(vis_type)

        # Get image URL
        image_url = get_ee_image_url(image, geometry, vis_params)

        # Create map with overlay
        map_html = create_folium_map(
            DEFAULT_LAT, DEFAULT_LON, DEFAULT_ZOOM, image_url, geometry
        )

        status_msgs.append(
            html.Div(
                "✅ Imagery loaded successfully!",
                style={"color": "green", "fontWeight": "bold", "marginTop": "10px"},
            )
        )
        status_msgs.append(
            html.Div(
                f"📊 Visualization: {vis_type.upper()}", style={"marginTop": "5px"}
            )
        )

        return map_html, html.Div(status_msgs)

    except Exception as e:
        error_map = create_folium_map(
            DEFAULT_LAT, DEFAULT_LON, DEFAULT_ZOOM, geometry=PRESET_GEOMETRY
        )
        error_msg = html.Div(
            [
                html.Div(
                    "❌ Error loading imagery:",
                    style={"color": "red", "fontWeight": "bold"},
                ),
                html.Div(
                    str(e),
                    style={"color": "red", "fontSize": "12px", "marginTop": "5px"},
                ),
            ]
        )
        return error_map, error_msg


if __name__ == "__main__":
    print("Starting Sentinel-2 Dash App...")
    app.run(debug=True, port=8050)
