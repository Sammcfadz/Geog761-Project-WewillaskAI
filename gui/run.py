import dash
from dash import dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc

from login_page import *
from map_page import *

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Main layout with page container and login status store
app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        dcc.Store(id="login-status", data=False),
        dcc.Store(id="current-user", data=None),
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


# Register callbacks from other modules
handle_login_callbacks(app)
handle_map_callbacks(app)

if __name__ == "__main__":
    app.run(debug=True)
