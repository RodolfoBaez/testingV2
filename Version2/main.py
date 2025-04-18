import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from controller import controller
from database import init_db, add_user, get_user_by_id, get_user_by_email, add_measurement
from simulated_visacon import SimulatedVisaCon
import sqlite3
import csv
import time
import webview

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

# MEASUREMENT PAGES #######################################################################################################################################

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

    # C-V Measurement #################################################################################################################
        if request.method == "POST":
            action = request.form.get("action")
            if action == "set_mode":
                # Set the machine mode based on user selection
                mode = request.form.get("mode")
                if mode == "ct":
                    ctrl.set_ctfunc()  # Set to C-T mode
                    flash("Machine set to C-T mode successfully!", "success")
                elif mode == "cgt":
                    ctrl.set_cgtfunc()  # Set to C-G-T mode
                    flash("Machine set to C-G-T mode successfully!", "success")
                else:
                    flash("Invalid mode selected.", "error")
            elif action == "set_connection_mode":
                # Set the connection mode based on user selection
                connection_mode = request.form.get("connection_mode")
                if connection_mode == "float":
                    ctrl.set_float()  # Set to Float mode
                    flash("Connection set to Float mode successfully!", "success")
                elif connection_mode == "ground":
                    ctrl.set_ground()  # Set to Ground mode
                    flash("Connection set to Ground mode successfully!", "success")
                else:
                    flash("Invalid connection mode selected.", "error")
            elif action == "set_cable_length":
                # Set the cable length based on user selection
                cable_length = request.form.get("cable_length")
                if cable_length == "1":
                    ctrl.set_cable_1()  # Set to 0 meters
                    flash("Cable length set to 0 meters successfully!", "success")
                elif cable_length == "2":
                    ctrl.set_cable_2()  # Set to 1 meter
                    flash("Cable length set to 1 meter successfully!", "success")
                else:
                    flash("Invalid cable length selected.", "error")
            elif action == "set_function":
                # Set the function based on user selection
                function = request.form.get("function")
                if function == "cg": # Unique to C-V Measurement
                    ctrl.set_cg()  
                    flash("Function set to C-G successfully!", "success")
                elif function == "c": # Unique to C-V Measurement
                    ctrl.set_c()  
                    flash("Function set to C successfully!", "success")
                elif function == "g": # Unique to C-V Measurement
                    ctrl.set_g() 
                    flash("Function set to G successfully!", "success")
                elif function == "cgt": # Unique to C-T Measurement
                    ctrl.set_cgtfunc()
                    flash("Function set to C-G-T successfully!", "success")
                elif function == "ct": # Unique to C-T Measurement
                    ctrl.set_ctfunc()
                    flash("Function set to C-T successfully!", "success")
                elif function == "gt": # Unique to C-T Measurement
                    ctrl.set_gtfunc()
                    flash("Function set to G-T successfully!", "success")
                else:
                    flash("Invalid function selected.", "error")
            elif action == "set_meas_speed":
                # Set the measurement speed based on user selection
                meas_speed = request.form.get("meas_speed")
                if meas_speed == "fast":
                    ctrl.set_fast()  # Set to Fast speed
                    flash("Measurement speed set to Fast successfully!", "success")
                elif meas_speed == "medium":
                    ctrl.set_medium()  # Set to Medium speed
                    flash("Measurement speed set to Medium successfully!", "success")
                elif meas_speed == "slow":
                    ctrl.set_slow()  # Set to Slow speed
                    flash("Measurement speed set to Slow successfully!", "success")
                else:
                    flash("Invalid measurement speed selected.", "error")
            elif action == "set_meas_range":
                meas_range = request.form.get("meas_range")
                if meas_range == "auto":
                    ctrl.set_auto()
                    flash("Measurement range set to Auto successfully!", "success")
                elif meas_range == "manual1":
                    ctrl.set_10nf()
                    flash("Measurement range set to 10nF/10mS successfully!", "success")
                elif meas_range == "manual2":
                    ctrl.set_100pf()
                    flash("Measurement range set to 100pF/1mS successfully!", "success")
                elif meas_range == "manual3":
                    ctrl.set_10pf()
                    flash("Measurement range set to 1pF/100uS successfully!", "success")
                else:
                    flash("Invalid measurement range selected.", "error")
            elif action == "set_sweep":
                sweep_mode = request.form.get("sweep_mode")
                if sweep_mode == "int":
                    ctrl.set_int() # Internal pulse mode
                    flash("Sweep mode set to Repeat successfully!", "success")
                elif sweep_mode == "ext":
                    ctrl.set_ext() # External pulse mode
                    flash("Sweep mode set to External successfully!", "success")
                elif sweep_mode == "hold":
                    ctrl.set_hold() # Single pulse mode
                    flash("Sweep mode set to Single successfully!", "success")
                else:
                    flash("Invalid sweep mode selected.", "error")
            elif action == "set_sig_level":
                sig_level = request.form.get("sig_level")
                if sig_level == "30":
                    ctrl.set_signal_30()
                    flash("Signal level set to 30V successfully!", "success")
                elif sig_level == "10":
                    ctrl.set_signal_10()
                    flash("Signal level set to 10V successfully!", "success")

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
    # Create a WebView window
    webview.create_window('HP 4280A Controller', app)  # Pass the Flask app to the WebView window
    webview.start()

    # Start the Flask app via web browser
    ##app.run(debug=True, host="0.0.0.0", port=5001)