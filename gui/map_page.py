from dash import dcc, html
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import json

# Auckland coordinates
AUCKLAND_LAT = -36.8485
AUCKLAND_LON = 174.7633


def create_map_layout():
    """Create the interactive map page layout"""
    return dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            # Header with welcome message and logout
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.H2(
                                                "Auckland Landslide Map",
                                                className="mb-0",
                                            )
                                        ],
                                        width=8,
                                    ),
                                    dbc.Col(
                                        [
                                            html.Div(
                                                [
                                                    html.Span(
                                                        id="welcome-message",
                                                        className="me-3",
                                                    ),
                                                    dbc.Button(
                                                        "Logout",
                                                        id="logout-button",
                                                        color="outline-secondary",
                                                        size="sm",
                                                        n_clicks=0,
                                                    ),
                                                ],
                                                className="d-flex align-items-center justify-content-end",
                                            )
                                        ],
                                        width=4,
                                    ),
                                ],
                                className="mb-4",
                            ),
                            # Map card
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            dcc.Graph(
                                                id="auckland-map",
                                                figure=create_auckland_map(),
                                                style={"height": "75vh"},
                                            )
                                        ],
                                        className="p-0",
                                    )
                                ]
                            ),
                            # Map controls and info
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Card(
                                                [
                                                    dbc.CardBody(
                                                        [
                                                            html.H5(
                                                                "Map Controls",
                                                                className="card-title",
                                                            ),
                                                            html.P(
                                                                "• Use mouse wheel to zoom in/out"
                                                            ),
                                                            html.P(
                                                                "• Click and drag to pan around"
                                                            ),
                                                            html.P(
                                                                "• Double-click to zoom in quickly"
                                                            ),
                                                            html.P(
                                                                "• Use zoom buttons (+/-) in top-right corner"
                                                            ),
                                                        ]
                                                    )
                                                ]
                                            )
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Card(
                                                [
                                                    dbc.CardBody(
                                                        [
                                                            html.H5(
                                                                "Map Information",
                                                                className="card-title",
                                                            ),
                                                            html.P(
                                                                "Location: Auckland, New Zealand"
                                                            ),
                                                            html.P(
                                                                "Coordinates: -36.8485°S, 174.7633°E"
                                                            ),
                                                            html.P(
                                                                "Map Style: OpenStreetMap"
                                                            ),
                                                            html.P(
                                                                "Population: ~1.7 million"
                                                            ),
                                                        ]
                                                    )
                                                ]
                                            )
                                        ],
                                        width=6,
                                    ),
                                ],
                                className="mt-4",
                            ),
                        ],
                        width=12,
                    )
                ]
            )
        ],
        fluid=True,
        className="py-4",
    )


def create_auckland_map():
    """Create an interactive map centered on Auckland"""

    fig = go.Figure()

    # Add polygons of landslides

    with open("regions.geojson", "r") as f:
        geojson = json.load(f)

    fig.add_trace(
        go.Choroplethmapbox(
            geojson=geojson,  # your GeoJSON polygon data
            locations=["region1", "region2"],  # must match feature "id" in geojson
            z=[10, 30],  # values to shade polygons
            featureidkey="id",  # match on GeoJSON "id"
            colorscale="Viridis",  # colormap
            marker_opacity=0.6,
            marker_line_width=1,
            text=["Region 1: Value 10", "Region 2: Value 30"],  # hover labels
            hoverinfo="text",
            name="Shaded Regions",
        )
    )

    fig.update_layout(
        mapbox=dict(
            bearing=0,
            center=go.layout.mapbox.Center(lat=AUCKLAND_LAT, lon=AUCKLAND_LON),
            pitch=0,
            zoom=9,
            style="open-street-map",
        ),
        height=600,
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        showlegend=False,
    )

    return fig
