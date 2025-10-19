from dash import Input, Output, State, callback
import dash_bootstrap_components as dbc
import json
import os
import ee

# Import the app from run.py - this will be available when imported
from run import app


# Callback to update form based on current mode (only responds to toggle link clicks)
@app.callback(
    [
        Output("form-title", "children"),
        Output("action-button", "children"),
        Output("toggle-text", "children"),
        Output("toggle-link", "children"),
        Output("project-row", "style"),
        Output("mode-store", "data"),
    ],
    [Input("toggle-link", "n_clicks")],
    [State("mode-store", "data")],
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


# Callback for handling both login and account creation
@app.callback(
    [
        Output("message-store", "data"),
        Output("login-status", "data"),
        Output("current-user", "data"),
        Output("mode-store", "data", allow_duplicate=True),
    ],
    [Input("action-button", "n_clicks")],
    [
        State("username-input", "value"),
        State("password-input", "value"),
        State("project-input", "value"),
        State("mode-store", "data"),
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
            return (error_msg, False, None, mode)

        # Load existing users
        users = {}
        if os.path.exists("gui/user_details.json"):
            try:
                with open("gui/user_details.json", "r") as file:
                    users = json.load(file)
            except (json.JSONDecodeError, FileNotFoundError):
                users = {}

        if mode == "login":
            # Handle login
            if username in users and password == users[username]["password"]:
                try:
                    ee.Initialize(project=users[username]["ee_project"])
                    print("DEBUG: Successful login")
                    return ("", True, username, mode)
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
                return (error_msg, False, None, mode)

            if username in users:
                error_msg = {
                    "type": "alert",
                    "message": "Username already exists. Please choose a different username.",
                    "color": "warning",
                }
                print("DEBUG: Username exists error")
                return (error_msg, False, None, mode)

            # Add new user
            users[username] = {"password": password, "ee_project": project}

            # Save to file
            try:
                with open("gui/user_details.json", "w") as file:
                    json.dump(users, file, indent=2)

                success_msg = {
                    "type": "alert",
                    "message": "Account created successfully! You can now login.",
                    "color": "success",
                }
                print("DEBUG: Account created successfully")
                return (success_msg, False, None, "login")
            except Exception as e:
                error_msg = {
                    "type": "alert",
                    "message": f"Error creating account: {str(e)}",
                    "color": "danger",
                }
                print("DEBUG: Account creation failed")
                return (error_msg, False, None, mode)

    print("DEBUG: Returning empty message")
    return ("", False, None, mode)


# Callback to display messages from the store
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
