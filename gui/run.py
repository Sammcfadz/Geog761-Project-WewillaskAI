import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
from auth_pages import create_login_layout
from map_page import create_map_layout

# Initialize the Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)

# Main layout with page container and stores
app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        dcc.Store(id="login-status", data=False),
        dcc.Store(id="current-user", data=None),
        dcc.Store(id="message-store", data=""),
        dcc.Store(id="mode-store", data="login"),
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


# Import callbacks after app is defined
from auth_callbacks import *
from map_callbacks import *

# Run the app
if __name__ == "__main__":
    app.run(debug=True)
