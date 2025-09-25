import dash
from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

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
                                                "Auckland Interactive Map",
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

    # Auckland points of interest
    poi_data = {
        "names": [
            "Auckland CBD",
            "Sky Tower",
            "Auckland Harbour Bridge",
            "Mission Bay",
            "Mount Eden",
        ],
        "lat": [-36.8485, -36.8485, -36.8063, -36.8553, -36.8785],
        "lon": [174.7633, 174.7633, 174.7444, 174.7972, 174.7633],
        "descriptions": [
            "Auckland Central Business District",
            "Iconic 328m observation tower",
            "Famous harbour bridge connecting North Shore",
            "Popular beach suburb",
            "Volcanic cone with city views",
        ],
    }

    fig = go.Figure()

    # Add markers for points of interest
    fig.add_trace(
        go.Scattermapbox(
            lat=poi_data["lat"],
            lon=poi_data["lon"],
            mode="markers",
            marker=go.scattermapbox.Marker(
                size=12, color=["red", "blue", "green", "orange", "purple"]
            ),
            text=[
                f"<b>{name}</b><br>{desc}"
                for name, desc in zip(poi_data["names"], poi_data["descriptions"])
            ],
            hoverinfo="text",
            name="Points of Interest",
        )
    )

    fig.update_layout(
        mapbox=dict(
            bearing=0,
            center=go.layout.mapbox.Center(lat=AUCKLAND_LAT, lon=AUCKLAND_LON),
            pitch=0,
            zoom=11,
            style="open-street-map",  # Free map style
        ),
        height=600,
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        showlegend=False,
    )

    return fig


def handle_map_callbacks(app):
    """Register all map-related callbacks"""

    # Callback to update welcome message
    @app.callback(
        Output("welcome-message", "children"),
        [Input("current-user", "data")],
        prevent_initial_call=False,
    )
    def update_welcome_message(username):
        if username:
            return f"Welcome, {username}!"
        return ""

    # Callback for logout functionality
    @app.callback(
        [
            Output("login-status", "data", allow_duplicate=True),
            Output("current-user", "data", allow_duplicate=True),
        ],
        [Input("logout-button", "n_clicks")],
        prevent_initial_call=True,
    )
    def handle_logout(n_clicks):
        if n_clicks > 0:
            return False, None
        return dash.no_update, dash.no_update
