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

# GENERAL PAGES ###############################################################################################################################################

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/contributions')
def contributions():
    return render_template("contributions.html")

@app.route('/connection')
def connection():
    # Check if the user is logged in
    if 'email' not in session:
        flash("Please log in to access this page.", "error")
        return redirect(url_for("login"))

    # Get the user information
    user = get_user_by_email(session['email'])
    
    # Check if the logged-in user is "DEMO"
    if user and user[3] == "demo@example.com":
        # Use the simulated VisaCon class for the DEMO user
        gpib_connection = SimulatedVisaCon()
    else:
        # Use the real VisaCon class for other users
        gpib_connection = VisaCon()

    # Connect to the device
    gpib_connection.connect()

    # Check if the device is connected
    if gpib_connection.check_connection():
        terminal_output = [f"Connected to {gpib_connection.get_MAC()}",
                           f"Instrument ID: {gpib_connection.get_device_id()}"]
    else:
        terminal_output = ["Error: No GPIB device detected. Please check the connection and address."]

    # Disconnect after checking
    gpib_connection.disconnect()

    return render_template("connection.html", terminal_output=terminal_output)

@app.route('/measurement', methods=["GET", "POST"])
def measurement():
     # Check if the user is logged in
    if 'email' not in session:
        flash("Please log in to access this page.", "error")
        return redirect(url_for("login"))

    # Get the user information
    user = get_user_by_email(session['email'])
    
    if not user:
        flash("User not found. Please log in again.", "error")
        return redirect(url_for("login"))

    # Initialize settings in the session if not already present
    if "settings" not in session:
        session["settings"] = {
            "DC_V": 5.0,
            "Start_V": 0.0,
            "Stop_V": 5.0,
            "Step_V": 0.1,
            "Hold_T": 0.01,
            "Step_T": 0.03
        }

    # Check if the logged-in user is "DEMO" to determine the connection type
    if user[3] == "demo@example.com":
        gpib_connection = SimulatedVisaCon()
        gpib_connection.connect()  # Simulate connection
        connection_type = "Simulated Connection (DEMO Mode)"
    else:
        gpib_connection = VisaCon()
        gpib_connection.connect()  # Ensure real connection is established
        connection_type = "Real Connection to HP4280A"

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

    if request.method == "POST":
        action = request.form.get("action")
        if action == "update_settings":
            # Update settings
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
            
            # Create filename for CSV
            uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
            os.makedirs(uploads_dir, exist_ok=True)
            filename = os.path.join(uploads_dir, f"{measurement_type}_measurement_{int(time.time())}.csv")
            
            # Perform measurement and save to CSV
            if measurement_type == "cv":
                ctrl.single_config()  # Configure the controller for single sweep
                ctrl.init_sweep()  # Initialize the sweep
                data = ctrl.read_data()  # Read the measurement data
                if data:
                    ctrl.mkcsv(data, filename)  # Generate the CSV file
                    flash(f"C-V Measurement completed! Data saved to {filename}.", "success")
                else:
                    flash("No data received during C-V measurement.", "error")
            elif measurement_type == "ct":
                ctrl.set_ctfunc()  # Set C-T function
                ctrl.default_CT()  # Configure the controller for C-T measurement
                ctrl.init_sweep()  # Initialize the sweep
                data = ctrl.read_data()  # Read the measurement data
                if data:
                    ctrl.mkcsv(data, filename)  # Generate the CSV file
                    flash(f"C-T Measurement completed! Data saved to {filename}.", "success")
                else:
                    flash("No data received during C-T measurement.", "error")

    return render_template("measurement.html", connection_type=connection_type, settings=session["settings"])


@app.route('/graph')
def graph():
    return render_template("graph.html")

@app.route('/documentation')
def documentation():
    # Fetch all users from the database
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute("SELECT first_name, last_name FROM users")  # Fetch only names for privacy
    users = cursor.fetchall()
    conn.close()

    formatted_users = [f"{user[0]} {user[1]}" for user in users]
    
    # Pass the user data to the template
    return render_template("documentation.html", users=formatted_users)

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
    session.pop("email", None)  # Remove email from session
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5001)