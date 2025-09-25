import dash
from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
import json
import os
import ee


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


def handle_login_callbacks(app):
    """Register all login-related callbacks"""

    # Callback to update form based on current mode
    @app.callback(
        [
            Output("form-title", "children"),
            Output("action-button", "children"),
            Output("toggle-text", "children"),
            Output("toggle-link", "children"),
            Output("project-row", "style"),
            Output("current-mode", "children"),
        ],
        [Input("toggle-link", "n_clicks")],
        [State("current-mode", "children")],
        prevent_initial_call=False,
    )
    def update_form_mode(n_clicks, current_mode):
        if n_clicks and current_mode == "login":
            # Switch to create account mode
            return (
                "Create Account",
                "Create Account",
                "Already have an account?",
                "Login here",
                {"display": "block"},
                "create",
            )
        else:
            # Default to login mode
            return (
                "Login",
                "Login",
                "Don't have an account?",
                "Create one here",
                {"display": "none"},
                "login",
            )

    # Callback for handling both login and account creation
    @app.callback(
        [
            Output("message", "children"),
            Output("login-status", "data"),
            Output("current-user", "data"),
        ],
        [Input("action-button", "n_clicks")],
        [
            State("username-input", "value"),
            State("password-input", "value"),
            State("project-input", "value"),
            State("current-mode", "children"),
        ],
        prevent_initial_call=True,
    )
    def handle_action(n_clicks, username, password, project, mode):
        if n_clicks > 0:
            if not username or not password:
                return (
                    dbc.Alert(
                        "Please enter both username and password.",
                        color="warning",
                        dismissable=True,
                    ),
                    False,
                    None,
                )

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
                        return ("", True, username)  # Successful login
                    except Exception as e:
                        return (
                            dbc.Alert(
                                f"Login successful but Earth Engine initialization failed: {str(e)}",
                                color="warning",
                                dismissable=True,
                            ),
                            False,
                            None,
                        )
                else:
                    return (
                        dbc.Alert(
                            "Invalid credentials. Please try again.",
                            color="danger",
                            dismissable=True,
                        ),
                        False,
                        None,
                    )

            elif mode == "create":
                # Handle account creation
                if not project:
                    return (
                        dbc.Alert(
                            "Please enter an Earth Engine project ID.",
                            color="warning",
                            dismissable=True,
                        ),
                        False,
                        None,
                    )

                if username in users:
                    return (
                        dbc.Alert(
                            "Username already exists. Please choose a different username.",
                            color="warning",
                            dismissable=True,
                        ),
                        False,
                        None,
                    )

                # Add new user
                users[username] = {"password": password, "ee_project": project}

                # Save to file
                try:
                    with open("user_details.json", "w") as file:
                        json.dump(users, file, indent=2)

                    return (
                        dbc.Alert(
                            "Account created successfully! You can now login.",
                            color="success",
                            dismissable=True,
                        ),
                        False,
                        None,
                    )
                except Exception as e:
                    return (
                        dbc.Alert(
                            f"Error creating account: {str(e)}",
                            color="danger",
                            dismissable=True,
                        ),
                        False,
                        None,
                    )

        return ("", False, None)
