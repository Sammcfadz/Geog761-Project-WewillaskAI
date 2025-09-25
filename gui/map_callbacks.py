from dash import Input, Output, callback, no_update

# Import the app from run.py - this will be available when imported
from run import app


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
    return no_update, no_update
