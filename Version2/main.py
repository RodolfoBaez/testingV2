import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from controller import controller
from database import init_db, add_user, get_user_by_id, get_user_by_email, add_measurement
from simulated_visacon import SimulatedVisaCon
import sqlite3
import csv
import time

# Define the path to the database file
DB_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Required for flashing messages and session management

# Initialize the database
init_db()

# Import the real VisaCon class if it exists
try:
    from visacon import VisaCon
except ImportError:
    # Use the simulated version as a fallback
    VisaCon = SimulatedVisaCon

@app.context_processor
def inject_user_info():
    """Inject user information into all templates"""
    if 'email' in session:
        user = get_user_by_email(session['email'])
        if user:
            return {'username': f"{user[1]} {user[2]}", 'user_id': user[0], 'email': user[3]}
    return {'username': None, 'user_id': None, 'email': None}

# Global Dictionary to store controller instances through session ID
gpib_connections = {}

def get_controller():
    """Retrieve or create a controller instance for the current session."""
    session_id = session.get('email')
    if not session_id:
        raise Exception("No session ID found. User must be logged in.")

    if session_id not in gpib_connections:
        # Determine the connection type
        user = get_user_by_email(session_id)
        if not user:
            raise Exception("User not found.")

        if user[3] == "demo@example.com":
            gpib_connection = SimulatedVisaCon()
        else:
            gpib_connection = VisaCon()

        # Connect the GPIB connection
        gpib_connection.connect()
        if not gpib_connection.check_connection():
            raise Exception("Failed to connect to the GPIB device.")

        # Create a controller instance and store it in the dictionary
        gpib_connections[session_id] = controller(
            conn=gpib_connection,
            DC_V=5.0,
            Start_V=-5.0,
            Stop_V=5.0,
            Step_V=0.5,
            Hold_T=0.05,
            Step_T=0.05
        )

    return gpib_connections[session_id]

def initialize_settings():
    """Initialize session settings with default values if not already set."""
    if "settings" not in session:
        session["settings"] = {
            "DC_V": 5.0,
            "Start_V": -5.0,
            "Stop_V": 5.0,
            "Step_V": 0.5,
            "Hold_T": 0.05,
            "Step_T": 0.05
        }

# GENERAL PAGES ###############################################################################################################################################

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/contributions')
def contributions():
    return render_template("contributions.html")

@app.route('/measurement', methods=["GET", "POST"])
def measurement():
    # Check if the user is logged in
    if 'email' not in session:
        flash("Please log in to access this page.", "error")
        return redirect(url_for("login"))

    # Initialize settings if not already set
    initialize_settings()

    try:
        # Get the controller instance
        ctrl = get_controller()

        if request.method == "POST":
            action = request.form.get("action")
            if action == "update_settings":
                # Update general settings
                session["settings"].update({
                    "DC_V": float(request.form['DC_V']),
                    "Start_V": float(request.form['Start_V']),
                    "Stop_V": float(request.form['Stop_V']),
                    "Step_V": float(request.form['Step_V']),
                    "Hold_T": float(request.form['Hold_T']),
                    "Step_T": float(request.form['Step_T'])
                })
                # Update controller settings
                ctrl.set_DCV(session["settings"]["DC_V"])
                ctrl.set_StartV(session["settings"]["Start_V"])
                ctrl.set_StopV(session["settings"]["Stop_V"])
                ctrl.set_StepV(session["settings"]["Step_V"])
                ctrl.set_Hold_Time(session["settings"]["Hold_T"])
                ctrl.set_StepT(session["settings"]["Step_T"])
                flash("Settings updated successfully!", "success")
            elif action == "start_measurement":
                # Get the measurement type
                measurement_type = request.form.get("measurement_type")

                # Perform measurement and save to CSV
                if measurement_type == "cv":
                    ctrl.single_config()
                    ctrl.init_sweep()
                    data = ctrl.read_data()
                    if data:
                        ctrl.mkcsv(data)
                        flash("C-V Measurement completed! Data saved successfully.", "success")
                    else:
                        flash("No data received during C-V measurement.", "error")
                elif measurement_type == "ct":
                    ctrl.set_ctfunc()
                    ctrl.default_CT()
                    ctrl.init_sweep()
                    data = ctrl.read_data()
                    if data:
                        ctrl.mkcsv(data)
                        flash("C-T Measurement completed! Data saved successfully.", "success")
                    else:
                        flash("No data received during C-T measurement.", "error")
                elif measurement_type == "pulse":
                    # Configure pulse-specific settings
                    pulse_width = float(request.form.get("pulse_width", 0.1))  # Default to 0.1 if not provided
                    pulse_amplitude = float(request.form.get("pulse_amplitude", 5.0))  # Default to 5.0 if not provided
                    ctrl.set_Pulse(pulse_amplitude)  # Set pulse amplitude
                    ctrl.set_Measure_pulse(pulse_width)  # Set pulse width

                    # Perform pulse sweep measurement
                    ctrl.pulse_sweep()
                    flash("Pulse Sweep Measurement completed! Data saved successfully.", "success")

        return render_template("measurement.html", connection_type="Real Connection", settings=session["settings"])
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for("home"))

@app.route('/graph', methods=["GET", "POST"])
def graph():
    # Check if the user is logged in
    if 'email' not in session:
        flash("Please log in to access this page.", "error")
        return redirect(url_for("login"))

    # Render the splice graph page
    return render_template("graph.html")

@app.route('/wizard', methods=["GET", "POST"])
def wizard():
    # Check if the user is logged in
    if 'email' not in session:
        flash("Please log in to access this page.", "error")
        return redirect(url_for("login"))

    # Initialize settings if not already set
    initialize_settings()

    try:
        # Get the controller instance
        ctrl = get_controller()

        if request.method == "POST":
            measurement_type = request.form.get("measurement_type")
            bias_mode = request.form.get("bias_mode")  # Retrieve the bias mode from the form
            graph_type = request.form.get("graph_type")
            x_axis = request.form.get("x_axis")
            y1_axis = request.form.get("y1_axis")
            y2_axis = request.form.get("y2_axis") if graph_type == "cgv" else None

            # Perform measurement and save data
            data = None
            if measurement_type == "cv":
                if bias_mode == "pulsed":
                    # Configure pulse-specific settings
                    pulse_width = float(request.form.get("pulse_width", 0.1))  # Default to 0.1 if not provided
                    pulse_amplitude = float(request.form.get("pulse_amplitude", 5.0))  # Default to 5.0 if not provided
                    ctrl.set_Pulse(pulse_amplitude)  # Set pulse amplitude
                    ctrl.set_Measure_pulse(pulse_width)  # Set pulse width

                    # Perform pulse sweep measurement
                    ctrl.pulse_sweep()
                    data = ctrl.read_data()
                else:
                    # Default CV measurement
                    ctrl.single_config()
                    ctrl.init_sweep()
                    data = ctrl.read_data()
            elif measurement_type == "ct":
                ctrl.set_ctfunc()  # Set the instrument to C-T mode
                ctrl.default_CT()  # Configure default C-T parameters
                ctrl.init_sweep()
                data = ctrl.read_data()
            elif measurement_type == "cgt":
                ctrl.set_cgtfunc()  # Set the instrument to C-G-T mode
                ctrl.default_CT()  # Configure default C-G-T parameters
                ctrl.init_sweep()
                data = ctrl.read_data()

            if data:
                # Save the data to a CSV file using the mkcsv function
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                filename = f"wizard_measurement_{timestamp}.csv"
                ctrl.mkcsv(data, filename)
                flash(f"Measurement completed successfully. Data saved to {filename}.", "success")
            else:
                flash("No data received during measurement. Please try again.", "error")

        return render_template("wizard.html", connection_type="Real Connection", settings=session["settings"])
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for("home"))

@app.route('/documentation', methods=["GET", "POST"])
def documentation():
    # Check if the user is logged in
    if 'email' not in session:
        flash("Please log in to access this page.", "error")
        return redirect(url_for("login"))

    # Get the user information
    user = get_user_by_email(session['email'])
    if not user:
        flash("User not found. Please log in again.", "error")
        return redirect(url_for("login"))

    # Ensure the user is an admin
    if user[5] == 0:  # Check the `is_admin` value
        flash("You do not have permission to access this page.", "error")
        return redirect(url_for("login"))

    if request.method == "POST":
        action = request.form.get("action")
        user_id = request.form.get("user_id")

        conn = sqlite3.connect(DB_path)
        cursor = conn.cursor()

        if action == "delete":
            # Delete the user
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            flash("User deleted successfully!", "success")
        elif action == "grant_admin":
            # Grant admin access
            cursor.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (user_id,))
            flash("Admin access granted!", "success")
        elif action == "revoke_admin":
            # Revoke admin access
            cursor.execute("UPDATE users SET is_admin = 0 WHERE id = ?", (user_id,))
            flash("Admin access revoked!", "success")

        conn.commit()
        conn.close()

    # Fetch all users from the database
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute("SELECT first_name, last_name, email, id, is_admin FROM users")
    users = cursor.fetchall()
    conn.close()

    return render_template("documentation.html", users=users)

@app.route('/pulse_graph')
def pulsegraph():
    # Check if the user is logged in
    if 'email' not in session:
        flash("Please log in to access this page.", "error")
        return redirect(url_for("login"))

    # Render the pulse graph page
    return render_template("pulsegraph.html")

@app.route('/wizard_graph')
def wizardgraph():
    # Check if the user is logged in
    if 'email' not in session:
        flash("Please log in to access this page.", "error")
        return redirect(url_for("login"))

    # Retrieve graph settings and data from the session
    wizard_graph_settings = session.get("wizard_graph_settings")
    if not wizard_graph_settings or not wizard_graph_settings.get("data"):
        flash("No graph settings or data found. Please set up the measurement first.", "error")
        return redirect(url_for("wizard"))

    # Debugging: Print the graph settings to the console
    print("Wizard Graph Settings:", wizard_graph_settings)

    # Render the wizard graph page with the settings and data
    return render_template("wizardgraph.html", graph_settings=wizard_graph_settings)

@app.route('/reset_connection', methods=["POST"])
def reset_connection():
    # Check if the user is logged in
    if 'email' not in session:
        flash("Please log in to access this page.", "error")
        return redirect(url_for("login"))

    # Get the user information
    session_id = session.get('email')
    if session_id in gpib_connections:
        gpib_connection = gpib_connections[session_id]
        try:
            # Create a controller instance
            ctrl = controller(
                conn=gpib_connection,
                DC_V=session["settings"]["DC_V"],
                Start_V=session["settings"]["Start_V"],
                Stop_V=session["settings"]["Stop_V"],
                Step_V=session["settings"]["Step_V"],
                Hold_T=session["settings"]["Hold_T"],
                Step_T=session["settings"]["Step_T"]
            )

            # Use the controller's clear function
            ctrl.clear()
            flash("Connection reset successfully!", "success")
        except Exception as e:
            flash(f"Error resetting connection: {str(e)}", "error")
    else:
        flash("No active connection found to reset.", "error")

    return redirect(request.referrer or url_for("home"))

# USER PAGES ################################################################################################################################################
@app.route('/login', methods=["POST", "GET"])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = get_user_by_email(email)
        if user:
            stored_password = user[4]  # Assuming user[4] is the password column
            if stored_password == password:
                session["email"] = email  # Store email in session
                flash("Login successful!", "success")
                return redirect(url_for("home"))
            else:
                flash("Incorrect password. Please try again.", "error")
                return redirect(url_for("home") + "?login=1")
        else:
            flash("Email not found. Please register.", "error")
            return redirect(url_for("home") + "?login=1")
    
    # For GET requests, just redirect to home with login parameter
    return redirect(url_for("home") + "?login=1")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']

        # Check if the user already exists by email
        user = get_user_by_email(email)
        if user:
            flash("Email already exists", "error")
            return redirect(url_for("home"))
        else:
            add_user(first_name, last_name, email, password)
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("home") + "?login=1")
    
    # For GET requests, just redirect to home
    return redirect(url_for("home"))

@app.route('/logout')
def logout():
    session_id = session.get('email')
    if session_id in gpib_connections:
        ctrl = gpib_connections[session_id]  # Get the controller instance
        if hasattr(ctrl, 'conn') and hasattr(ctrl.conn, 'disconnect'):
            ctrl.conn.disconnect()  # Disconnect the GPIB connection
        del gpib_connections[session_id]  # Remove the controller instance from the dictionary
    session.pop("email", None)  # Remove email from session
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5001)