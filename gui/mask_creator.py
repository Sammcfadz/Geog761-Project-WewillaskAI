# TO DO:
# Get app to update itself when each button is selected in draw mode
# Get clear to work in annotation mode
# Convert annotation to patch

import dash
from dash import dcc, html, Input, Output, State, callback_context
import dash_leaflet as dl
import dash_leaflet.express as dlx
from datetime import datetime, timedelta
import ee
import json
import sys
import os

# add parent directory (project root) to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ee.Authenticate()
ee.Initialize(project="geog761-peag224")

from data_retrival import get_s2_image

# Initialize the Dash app
app = dash.Dash(__name__)

# Default coordinates (Auckland) - for map centering only
DEFAULT_LAT = -36.8485
DEFAULT_LON = 174.7633
DEFAULT_ZOOM = 10

# Your preset geometry - update this with your actual geometry
geojson_path = r"aklshp\akl_mainland_only.geojson"
with open(geojson_path) as f:
    geojson_data = json.load(f)

# Convert to Earth Engine Feature
PRESET_GEOMETRY = ee.Geometry(geojson_data["geometry"])
# Get preset geometry bounds for initial map view

app.layout = html.Div(
    [
        html.H1(
            "Sentinel-2 Landslide Annotation Tool",
            style={"textAlign": "center", "marginBottom": "20px"},
        ),
        # Imagery controls
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
        # Drawing controls section
        html.Div(
            [
                html.H3("Landslide Annotation Tools", style={"marginBottom": "10px"}),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Label(
                                    "Drawing Mode:", style={"fontWeight": "bold"}
                                ),
                                dcc.RadioItems(
                                    id="drawing-mode",
                                    options=[
                                        {"label": " View Only", "value": "view"},
                                        {
                                            "label": " Draw Region of Interest (Rectangle)",
                                            "value": "roi",
                                        },
                                        {
                                            "label": " Draw Landslides (Polygon/Rectangle)",
                                            "value": "landslide",
                                        },
                                    ],
                                    value="view",
                                    inline=True,
                                    style={"marginLeft": "10px"},
                                    labelStyle={"marginRight": "20px"},
                                ),
                            ],
                            style={"marginBottom": "15px"},
                        ),
                        html.Div(
                            [
                                html.Div(
                                    "📍 Instructions: Select a drawing mode above, then use the drawing toolbar on the LEFT side of the map:",
                                    style={
                                        "color": "#856404",
                                        "fontWeight": "bold",
                                        "marginBottom": "5px",
                                    },
                                ),
                                html.Div(
                                    "   • Rectangle icon: Draw rectangles",
                                    style={"fontSize": "12px"},
                                ),
                                html.Div(
                                    "   • Polygon icon: Draw custom shapes (landslide mode only)",
                                    style={"fontSize": "12px"},
                                ),
                                html.Div(
                                    "   • Edit icon: Modify existing shapes",
                                    style={"fontSize": "12px"},
                                ),
                                html.Div(
                                    "   • Trash icon: Delete shapes",
                                    style={"fontSize": "12px", "marginBottom": "10px"},
                                ),
                            ],
                            style={
                                "textAlign": "left",
                                "marginBottom": "15px",
                                "backgroundColor": "#ffe69c",
                                "padding": "10px",
                                "borderRadius": "5px",
                                "border": "1px solid #ffc107",
                            },
                        ),
                        html.Div(
                            [
                                html.Label(
                                    "Filename:",
                                    style={"fontWeight": "bold", "marginRight": "10px"},
                                ),
                                dcc.Input(
                                    id="save-filename",
                                    type="text",
                                    value="landslide_annotations",
                                    style={"width": "250px", "marginRight": "10px"},
                                ),
                                html.Button(
                                    "💾 Save Annotations",
                                    id="save-button",
                                    n_clicks=0,
                                    style={
                                        "padding": "10px 20px",
                                        "fontSize": "16px",
                                        "cursor": "pointer",
                                        "backgroundColor": "#28a745",
                                        "color": "white",
                                        "border": "none",
                                        "borderRadius": "5px",
                                        "marginRight": "10px",
                                    },
                                ),
                                html.Button(
                                    "🗑️ Clear All",
                                    id="clear-button",
                                    n_clicks=0,
                                    style={
                                        "padding": "10px 20px",
                                        "fontSize": "16px",
                                        "cursor": "pointer",
                                        "backgroundColor": "#dc3545",
                                        "color": "white",
                                        "border": "none",
                                        "borderRadius": "5px",
                                    },
                                ),
                            ],
                            style={
                                "display": "flex",
                                "alignItems": "center",
                                "justifyContent": "center",
                            },
                        ),
                    ],
                    style={"textAlign": "center"},
                ),
                html.Div(
                    id="annotation-status",
                    style={
                        "textAlign": "center",
                        "fontSize": "14px",
                        "minHeight": "30px",
                        "marginTop": "10px",
                    },
                ),
            ],
            style={
                "backgroundColor": "#fff3cd",
                "padding": "15px",
                "borderRadius": "5px",
                "marginTop": "10px",
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
        # Map
        html.Div(
            dl.Map(
                id="map",
                center=[DEFAULT_LAT, DEFAULT_LON],
                zoom=DEFAULT_ZOOM,
                children=[
                    dl.TileLayer(
                        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    ),
                    dl.LayersControl(
                        [
                            dl.BaseLayer(
                                dl.TileLayer(
                                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                                ),
                                name="OpenStreetMap",
                                checked=True,
                            ),
                            dl.BaseLayer(
                                dl.TileLayer(
                                    url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                                ),
                                name="Satellite",
                                checked=False,
                            ),
                            dl.Overlay(
                                dl.LayerGroup(id="s2-layer"),
                                name="Sentinel-2",
                                checked=True,
                            ),
                            dl.Overlay(
                                dl.LayerGroup(id="preset-geometry-layer"),
                                name="Study Area",
                                checked=True,
                            ),
                            dl.Overlay(
                                dl.LayerGroup(id="roi-layer"),
                                name="Region of Interest",
                                checked=True,
                            ),
                            dl.Overlay(
                                dl.LayerGroup(id="landslide-layer"),
                                name="Landslides",
                                checked=True,
                            ),
                        ]
                    ),
                    dl.FeatureGroup(
                        id="draw-control",
                        children=[
                            dl.EditControl(
                                id="edit-control",
                                draw={
                                    "polyline": False,
                                    "circle": False,
                                    "circlemarker": False,
                                    "marker": False,
                                },
                                edit=True,
                            )
                        ],
                    ),
                    dl.ScaleControl(position="bottomleft"),
                ],
                style={"width": "100%", "height": "700px"},
            ),
        ),
        # Data stores
        dcc.Store(id="current-tile-url"),
        dcc.Store(id="roi-features", data=None),
        dcc.Store(id="landslide-features", data=[]),
        dcc.Download(id="download-geojson"),
    ]
)


def get_ee_image_url(image: ee.Image, geometry: ee.Geometry, vis_params: dict) -> str:
    """Get a tile URL for an Earth Engine image."""
    map_id = image.getMapId(vis_params)
    return map_id["tile_fetcher"].url_format


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


# Update preset geometry layer
@app.callback(Output("preset-geometry-layer", "children"), Input("map", "id"))
def add_preset_geometry(_):
    """Add the preset geometry boundary to the map."""
    try:
        geom_json = PRESET_GEOMETRY.getInfo()
        return dl.GeoJSON(
            data=geom_json,
            style={"color": "blue", "weight": 2, "fillOpacity": 0, "dashArray": "5, 5"},
        )
    except:
        return None


# Load Sentinel-2 imagery
@app.callback(
    [
        Output("s2-layer", "children"),
        Output("current-tile-url", "data"),
        Output("status-message", "children"),
    ],
    Input("load-button", "n_clicks"),
    [
        State("start-date", "date"),
        State("end-date", "date"),
        State("cloud-cover", "value"),
        State("vis-type", "value"),
    ],
    prevent_initial_call=True,
)
def load_imagery(n_clicks, start_date, end_date, cloud_cover, vis_type):
    try:
        status_msgs = []
        status_msgs.append(
            html.Div(
                "🔄 Fetching Sentinel-2 imagery...",
                style={"color": "blue", "fontWeight": "bold"},
            )
        )

        geometry = PRESET_GEOMETRY

        # Get Sentinel-2 image
        image = get_s2_image(
            geometry=geometry,
            start_date=start_date,
            end_date=end_date,
            max_cloud_percent=cloud_cover,
        )

        if image is None:
            return (
                None,
                None,
                html.Div(
                    "❌ No suitable imagery found. Try adjusting parameters.",
                    style={"color": "red", "fontWeight": "bold"},
                ),
            )

        # Calculate index if needed
        if vis_type == "ndvi":
            nir = image.select("B8")
            red = image.select("B4")
            image = nir.subtract(red).divide(nir.add(red)).rename("NDVI")
        elif vis_type == "ndwi":
            green = image.select("B3")
            nir = image.select("B8")
            image = green.subtract(nir).divide(green.add(nir)).rename("NDWI")

        # Get visualization parameters and tile URL
        vis_params = get_visualization_params(vis_type)
        tile_url = get_ee_image_url(image, geometry, vis_params)

        # Create tile layer
        tile_layer = dl.TileLayer(
            url=tile_url, attribution="Sentinel-2 (Google Earth Engine)", opacity=0.8
        )

        status_msg = html.Div(
            [
                html.Div(
                    "✅ Imagery loaded successfully!",
                    style={"color": "green", "fontWeight": "bold"},
                ),
                html.Div(f"📅 {start_date} to {end_date}", style={"fontSize": "12px"}),
                html.Div(f"📊 {vis_type.upper()}", style={"fontSize": "12px"}),
            ]
        )

        return tile_layer, tile_url, status_msg

    except Exception as e:
        return (
            None,
            None,
            html.Div(
                f"❌ Error: {str(e)}", style={"color": "red", "fontWeight": "bold"}
            ),
        )


# Update drawing controls based on mode
@app.callback(Output("edit-control", "draw"), Input("drawing-mode", "value"))
def update_draw_mode(mode):
    if mode == "view":
        return {
            "polyline": False,
            "polygon": False,
            "rectangle": False,
            "circle": False,
            "circlemarker": False,
            "marker": False,
        }
    elif mode == "roi":
        return {
            "polyline": False,
            "polygon": False,
            "rectangle": {
                "shapeOptions": {
                    "color": "orange",
                    "fillColor": "yellow",
                    "fillOpacity": 0.2,
                    "weight": 3,
                }
            },
            "circle": False,
            "circlemarker": False,
            "marker": False,
        }
    else:  # landslide mode
        return {
            "polyline": False,
            "polygon": {
                "shapeOptions": {
                    "color": "darkred",
                    "fillColor": "red",
                    "fillOpacity": 0.4,
                    "weight": 2,
                }
            },
            "rectangle": {
                "shapeOptions": {
                    "color": "darkred",
                    "fillColor": "red",
                    "fillOpacity": 0.4,
                    "weight": 2,
                }
            },
            "circle": False,
            "circlemarker": False,
            "marker": False,
        }


# Handle drawn features
@app.callback(
    [
        Output("roi-features", "data"),
        Output("landslide-features", "data"),
        Output("roi-layer", "children"),
        Output("landslide-layer", "children"),
        Output("annotation-status", "children"),
    ],
    [Input("edit-control", "geojson"), Input("clear-button", "n_clicks")],
    [
        State("drawing-mode", "value"),
        State("roi-features", "data"),
        State("landslide-features", "data"),
    ],
    prevent_initial_call=True,
)
def handle_drawing(geojson_data, clear_clicks, mode, roi_data, landslide_data):
    ctx = callback_context
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]

    # Initialize if None
    if landslide_data is None:
        landslide_data = []

    # Clear all
    if triggered_id == "clear-button":
        status = html.Div(
            "🗑️ All annotations cleared!",
            style={"color": "orange", "fontWeight": "bold"},
        )
        return None, [], None, None, status

    # Handle new drawings
    if geojson_data and triggered_id == "edit-control":
        features = geojson_data.get("features", [])

        if mode == "roi" and features:
            # Take the last drawn feature as ROI (only one ROI allowed)
            roi_data = features[-1]["geometry"]
            roi_layer = dl.GeoJSON(
                data={"type": "Feature", "geometry": roi_data},
                style={
                    "color": "orange",
                    "fillColor": "yellow",
                    "fillOpacity": 0.2,
                    "weight": 3,
                },
            )
            status = html.Div(
                f"📏 ROI defined (1 region)",
                style={"color": "green", "fontWeight": "bold"},
            )
            return (
                roi_data,
                landslide_data,
                roi_layer,
                create_landslide_layer(landslide_data),
                status,
            )

        elif mode == "landslide" and features:
            # Add new landslides
            for feature in features:
                geom = feature["geometry"]
                if geom not in landslide_data:
                    landslide_data.append(geom)

            landslide_layer = create_landslide_layer(landslide_data)
            status = html.Div(
                f"🔴 {len(landslide_data)} landslide(s) marked",
                style={"color": "green", "fontWeight": "bold"},
            )
            return (
                roi_data,
                landslide_data,
                create_roi_layer(roi_data),
                landslide_layer,
                status,
            )

    # Return current state
    return (
        roi_data,
        landslide_data,
        create_roi_layer(roi_data),
        create_landslide_layer(landslide_data),
        "",
    )


def create_roi_layer(roi_data):
    """Create layer for ROI."""
    if roi_data:
        return dl.GeoJSON(
            data={"type": "Feature", "geometry": roi_data},
            style={
                "color": "orange",
                "fillColor": "yellow",
                "fillOpacity": 0.2,
                "weight": 3,
            },
        )
    return None


def create_landslide_layer(landslide_data):
    """Create layer for landslides."""
    if landslide_data and len(landslide_data) > 0:
        features = [{"type": "Feature", "geometry": geom} for geom in landslide_data]
        return dl.GeoJSON(
            data={"type": "FeatureCollection", "features": features},
            style={
                "color": "darkred",
                "fillColor": "red",
                "fillOpacity": 0.4,
                "weight": 2,
            },
        )
    return None


# Save annotations
@app.callback(
    [
        Output("download-geojson", "data"),
        Output("annotation-status", "children", allow_duplicate=True),
    ],
    Input("save-button", "n_clicks"),
    [
        State("save-filename", "value"),
        State("roi-features", "data"),
        State("landslide-features", "data"),
        State("start-date", "date"),
        State("end-date", "date"),
    ],
    prevent_initial_call=True,
)
def save_annotations(
    n_clicks, filename, roi_data, landslide_data, start_date, end_date
):
    if not roi_data and (not landslide_data or len(landslide_data) == 0):
        return None, html.Div("⚠️ No annotations to save!", style={"color": "red"})

    # Create GeoJSON structure
    geojson = {
        "type": "FeatureCollection",
        "metadata": {
            "created": datetime.now().isoformat(),
            "start_date": start_date,
            "end_date": end_date,
            "description": "Landslide annotations for ML training",
        },
        "features": [],
    }

    # Add ROI
    if roi_data:
        roi_feature = {
            "type": "Feature",
            "properties": {"class": "region_of_interest", "label": 0},
            "geometry": roi_data,
        }
        geojson["features"].append(roi_feature)

    # Add landslides
    if landslide_data:
        for idx, landslide_geom in enumerate(landslide_data):
            landslide_feature = {
                "type": "Feature",
                "properties": {
                    "class": "landslide",
                    "label": 1,
                    "landslide_id": idx + 1,
                },
                "geometry": landslide_geom,
            }
            geojson["features"].append(landslide_feature)

    json_string = json.dumps(geojson, indent=2)

    status_msg = html.Div(
        [
            html.Div(
                "✅ Saved successfully!", style={"color": "green", "fontWeight": "bold"}
            ),
            html.Div(f"📁 {filename}.geojson", style={"fontSize": "12px"}),
            html.Div(
                f"📊 {len(geojson['features'])} features", style={"fontSize": "12px"}
            ),
        ]
    )

    return dict(content=json_string, filename=f"{filename}.geojson"), status_msg


if __name__ == "__main__":
    print("Starting Sentinel-2 Landslide Annotation Tool...")
    app.run(debug=True, port=8050)
