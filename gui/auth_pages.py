from dash import html
import dash_bootstrap_components as dbc


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
                                                                        n_clicks=0,
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
