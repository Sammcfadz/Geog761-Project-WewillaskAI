import dash
from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import json
import os
import ee

# Initialize the Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)

# Auckland coordinates
AUCKLAND_LAT = -36.8485
AUCKLAND_LON = 174.7633


def create_login_layout():
    """Create the login/registration page layout"""
    return dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H2(
                                                id="form-title",
                                                className="text-center mb-4",
                                            ),
                                            # Username input
                                            dbc.InputGroup(
                                                [
                                                    dbc.InputGroupText("Username"),
                                                    dbc.Input(
                                                        id="username-input",
                                                        type="text",
                                                        placeholder="Enter username",
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                            # Password input
                                            dbc.InputGroup(
                                                [
                                                    dbc.InputGroupText("Password"),
                                                    dbc.Input(
                                                        id="password-input",
                                                        type="password",
                                                        placeholder="Enter password",
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                            # Project input (only visible when creating account)
                                            html.Div(
                                                id="project-row",
                                                children=[
                                                    dbc.InputGroup(
                                                        [
                                                            dbc.InputGroupText(
                                                                "EE Project"
                                                            ),
                                                            dbc.Input(
                                                                id="project-input",
                                                                type="text",
                                                                placeholder="Enter Earth Engine project ID",
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    )
                                                ],
                                                style={"display": "none"},
                                            ),
                                            # Action button (Login or Create Account)
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            dbc.Button(
                                                                id="action-button",
                                                                color="primary",
                                                                className="w-100 mb-3",
                                                                n_clicks=0,
                                                            )
                                                        ],
                                                        width={"size": 6, "offset": 3},
                                                    )
                                                ]
                                            ),
                                            # Toggle between login and create account
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            html.P(
                                                                [
                                                                    html.Span(
                                                                        id="toggle-text"
                                                                    ),
                                                                    html.A(
                                                                        id="toggle-link",
                                                                        href="#",
                                                                        style={
                                                                            "margin-left": "5px",
                                                                            "text-decoration": "none",
                                                                        },
                                                                        n_clicks=0,  # Add this to track clicks properly
                                                                    ),
                                                                ],
                                                                className="text-center",
                                                            )
                                                        ],
                                                        width=12,
                                                    )
                                                ]
                                            ),
                                            # Message area for feedback
                                            html.Div(
                                                id="message", className="text-center"
                                            ),
                                            # Hidden div to store current mode
                                            html.Div(
                                                id="current-mode",
                                                style={"display": "none"},
                                                children="login",
                                            ),
                                        ]
                                    )
                                ],
                                style={"max-width": "500px"},
                            )
                        ],
                        width=12,
                        className="d-flex justify-content-center",
                    )
                ],
                className="min-vh-100 d-flex align-items-center",
            )
        ],
        fluid=True,
    )


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
            style="open-street-map",
        ),
        height=600,
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        showlegend=False,
    )

    return fig


# Main layout with page container and login status store
app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        dcc.Store(id="login-status", data=False),
        dcc.Store(id="current-user", data=None),
        dcc.Store(id="message-store", data=""),
        dcc.Store(id="mode-store", data="login"),  # Add persistent mode store
        html.Div(id="page-content"),
    ]
)


# Main callback for page routing
@app.callback(
    Output("page-content", "children"),
    [Input("url", "pathname"), Input("login-status", "data")],
)
def display_page(pathname, logged_in):
    if logged_in:
        return create_map_layout()
    else:
        return create_login_layout()


# Modified callback to update form based on current mode (only responds to toggle link clicks)
@app.callback(
    [
        Output("form-title", "children"),
        Output("action-button", "children"),
        Output("toggle-text", "children"),
        Output("toggle-link", "children"),
        Output("project-row", "style"),
        Output("mode-store", "data"),  # Update the persistent store
    ],
    [Input("toggle-link", "n_clicks")],
    [State("mode-store", "data")],  # Use persistent store
    prevent_initial_call=False,
)
def update_form_mode(n_clicks, current_mode):
    print(
        f"DEBUG: update_form_mode called with n_clicks={n_clicks}, current_mode={current_mode}"
    )

    # Only switch mode when the toggle link is actually clicked (n_clicks > 0)
    if n_clicks and n_clicks > 0 and current_mode == "login":
        # Switch to create account mode
        print("DEBUG: Switching to create account mode")
        return (
            "Create Account",
            "Create Account",
            "Already have an account?",
            "Login here",
            {"display": "block"},
            "create",
        )
    elif n_clicks and n_clicks > 0 and current_mode == "create":
        # Switch to login mode
        print("DEBUG: Switching to login mode")
        return (
            "Login",
            "Login",
            "Don't have an account?",
            "Create one here",
            {"display": "none"},
            "login",
        )
    else:
        # Keep current mode (default to login for initial load)
        if current_mode == "create":
            print("DEBUG: Maintaining create account mode")
            return (
                "Create Account",
                "Create Account",
                "Already have an account?",
                "Login here",
                {"display": "block"},
                "create",
            )
        else:
            print("DEBUG: Maintaining login mode")
            return (
                "Login",
                "Login",
                "Don't have an account?",
                "Create one here",
                {"display": "none"},
                "login",
            )


# Modified callback for handling both login and account creation
@app.callback(
    [
        Output("message-store", "data"),
        Output("login-status", "data"),
        Output("current-user", "data"),
        Output(
            "mode-store", "data", allow_duplicate=True
        ),  # Only switch to login on successful account creation
    ],
    [Input("action-button", "n_clicks")],
    [
        State("username-input", "value"),
        State("password-input", "value"),
        State("project-input", "value"),
        State("mode-store", "data"),  # Use persistent store
    ],
    prevent_initial_call=True,
)
def handle_action(n_clicks, username, password, project, mode):
    print(f"DEBUG: handle_action called with n_clicks={n_clicks}, mode={mode}")

    if n_clicks > 0:
        if not username or not password:
            error_msg = {
                "type": "alert",
                "message": "Please enter both username and password.",
                "color": "warning",
            }
            print("DEBUG: Returning validation error message")
            return (error_msg, False, None, mode)  # Keep current mode

        # Load existing users
        users = {}
        if os.path.exists("user_details.json"):
            try:
                with open("user_details.json", "r") as file:
                    users = json.load(file)
            except (json.JSONDecodeError, FileNotFoundError):
                users = {}

        if mode == "login":
            # Handle login
            if username in users and password == users[username]["password"]:
                try:
                    ee.Initialize(project=users[username]["ee_project"])
                    print("DEBUG: Successful login")
                    return ("", True, username, mode)  # Successful login
                except Exception as e:
                    error_msg = {
                        "type": "alert",
                        "message": f"Login successful but Earth Engine initialization failed: {str(e)}",
                        "color": "warning",
                    }
                    print("DEBUG: EE init failed")
                    return (error_msg, False, None, mode)
            else:
                error_msg = {
                    "type": "alert",
                    "message": "Invalid credentials. Please try again.",
                    "color": "danger",
                }
                print("DEBUG: Invalid credentials error")
                return (error_msg, False, None, mode)

        elif mode == "create":
            # Handle account creation
            if not project:
                error_msg = {
                    "type": "alert",
                    "message": "Please enter an Earth Engine project ID.",
                    "color": "warning",
                }
                print("DEBUG: Missing project error")
                return (error_msg, False, None, mode)  # Keep create mode

            if username in users:
                error_msg = {
                    "type": "alert",
                    "message": "Username already exists. Please choose a different username.",
                    "color": "warning",
                }
                print("DEBUG: Username exists error")
                return (error_msg, False, None, mode)  # Keep create mode

            # Add new user
            users[username] = {"password": password, "ee_project": project}

            # Save to file
            try:
                with open("user_details.json", "w") as file:
                    json.dump(users, file, indent=2)

                success_msg = {
                    "type": "alert",
                    "message": "Account created successfully! You can now login.",
                    "color": "success",
                }
                print("DEBUG: Account created successfully")
                return (
                    success_msg,
                    False,
                    None,
                    "login",
                )  # Switch to login mode only on success
            except Exception as e:
                error_msg = {
                    "type": "alert",
                    "message": f"Error creating account: {str(e)}",
                    "color": "danger",
                }
                print("DEBUG: Account creation failed")
                return (error_msg, False, None, mode)  # Keep create mode

    print("DEBUG: Returning empty message")
    return ("", False, None, mode)


# Separate callback to display messages from the store
@app.callback(
    Output("message", "children"),
    [Input("message-store", "data")],
    prevent_initial_call=False,
)
def display_message(message_data):
    print(f"DEBUG: display_message called with: {message_data}")
    if (
        message_data
        and isinstance(message_data, dict)
        and message_data.get("type") == "alert"
    ):
        return dbc.Alert(
            message_data["message"],
            color=message_data["color"],
            dismissable=False,
        )
    return ""


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


# Run the app
if __name__ == "__main__":
    app.run(debug=True)
