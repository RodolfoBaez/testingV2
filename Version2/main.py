# Import Statements and Flask App Initialization ###################################################################################################################################################
import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from controller import controller
from database import init_db, add_user, get_user_by_id, get_user_by_email, add_measurement, get_measurements
from simulated_visacon import SimulatedVisaCon
from datetime import datetime
import pytz
from pytz import timezone
import sqlite3
import csv
import time
import webview
import bcrypt

# Define the path to the database file
DB_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Required for flashing messages and session management

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d'):
    """Custom filter to format datetime values, converting from UTC to Eastern Time."""
    try:
        # Define UTC timezone
        utc = pytz.utc
        # Try parsing as full datetime
        dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        # Assume the value is in UTC
        dt = utc.localize(dt)
        # Convert to Eastern Time
        eastern = timezone('US/Eastern')
        dt = dt.astimezone(eastern)
    except ValueError:
        try:
            # Try parsing as date only
            dt = datetime.strptime(value, '%Y-%m-%d')
            dt = pytz.utc.localize(dt)  # Handle as UTC
            eastern = timezone('US/Eastern')
            dt = dt.astimezone(eastern)
        except ValueError:
            try:
                # Try parsing as time only
                dt = datetime.strptime(value, '%H:%M:%S')
            except ValueError:
                # If all parsing fails, return original value
                return value
    return dt.strftime(format)
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
            return {
                'username': f"{user[1]} {user[2]}",  # First name and last name
                'user_id': user[0],  # User ID
                'email': user[3],  # Email
                'is_admin': user[5] == 1  # Check if the user is an admin (assuming `is_admin` is the 6th column)
            }
    return {
        'username': None,
        'user_id': None,
        'email': None,
        'is_admin': False
    }

# Global Dictionary to store controller instances through session ID
gpib_connections = {}

# Status and terminal output for connection status
@app.context_processor
def inject_connection_status():
    """Inject connection status into all templates"""
    if 'email' in session and session['email'] in gpib_connections:
        ctrl = gpib_connections[session['email']]
        if hasattr(ctrl, 'conn') and hasattr(ctrl.conn, 'check_connection'):
            connected = ctrl.conn.check_connection()
            return {
                'connection_status': 'success' if connected else 'failure',
                'terminal_output': ["Connected to device." if connected else "Not connected."]
            }
    return {
        'connection_status': 'failure',
        'terminal_output': ["No connection."]
    }

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

        if user[3] == "demo@hp4280a.com":
            gpib_connection = SimulatedVisaCon()
        else:
            gpib_connection = VisaCon()

        # Connect the GPIB connection
        gpib_connection.connect()
        if not gpib_connection.check_connection():
            raise Exception("Failed to connect to the GPIB device. If reconnected, please wait 10 seconds before trying again.")
        

        # Create a controller instance and store it in the dictionary
        gpib_connections[session_id] = controller(
            conn=gpib_connection,
            DC_V=5.0,
            Start_V=-5.0,
            Stop_V=5.0,
            Step_V=0.5,
            Hold_T=0.05,
            Step_T=0.05,
            Pulse=0.0,
            Meas=0.0,
            Nofread=10.0,
            Pulse_Width=1.0,
            Meas_Interval=0.15
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
            "Step_T": 0.05,
            "Pulse": 0.0,
            "Meas": 0.0,
            "Nofread": 10.0,
            "Pulse_Width": 1.0,
            "Meas_Interval": 0.15
        }

def check_connection_status():
    """Check if the controller is connected to the GPIB device."""
    if 'email' not in session:
        return "failure", ["User not logged in."]
    
    session_id = session.get('email')
    if session_id not in gpib_connections:
        return "failure", ["No GPIB connection found for current session."]

    ctrl = gpib_connections[session_id]
    if hasattr(ctrl, 'conn') and hasattr(ctrl.conn, 'check_connection'):
        connected = ctrl.conn.check_connection()
        if connected:
            return "success", ["Connection to device established."]
        else:
            return "failure", ["Failed to connect to device."]
    return "failure", ["Controller or connection is invalid."]

def add_user(first_name, last_name, email, password):
    """Add a new user to the database."""
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())  # Hash and salt the password
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO users (first_name, last_name, email, password)
        VALUES (?, ?, ?, ?)
    ''', (first_name, last_name, email, hashed_password))
    conn.commit()
    conn.close()

# GENERAL PAGES ###############################################################################################################################################

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/contributions')
def contributions():
    return render_template("contributions.html")

# MEASUREMENT PAGES #######################################################################################################################################

@app.route('/configuration', methods=["GET", "POST"])
def configuration():
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
            match action:
                case "start_measurement":
                    # Start the measurement using the sweep_measure function
                    csv_file_path = ctrl.sweep_measure()
                    if csv_file_path:
                        # Add the measurement to the database
                        user = get_user_by_email(session['email'])
                        measurement_id = add_measurement(
                            user_id=user[0], 
                            test_type="C-V Measurement",
                            csv_file_path=csv_file_path
                        )
                        flash("Measurement started successfully! Data saved to CSV.", "success")
                    else:
                        flash("Measurement failed. No data received.", "error")
                case "set_mode":
                    mode = request.form.get("mode")
                    match mode:
                        case "ct":
                            ctrl.set_ctfunc()
                            flash("Machine set to C-T mode successfully!", "success")
                        case "cgt":
                            ctrl.set_cgtfunc()
                            flash("Machine set to C-G-T mode successfully!", "success")
                        case _:
                            flash("Invalid mode selected.", "error")
                case "set_connection_mode":
                    connection_mode = request.form.get("connection_mode")
                    match connection_mode:
                        case "float":
                            ctrl.set_float()
                            flash("Connection set to Float mode successfully!", "success")
                        case "ground":
                            ctrl.set_ground()
                            flash("Connection set to Ground mode successfully!", "success")
                        case _:
                            flash("Invalid connection mode selected.", "error")
                case "set_cable_length":
                    cable_length = request.form.get("cable_length")
                    match cable_length:
                        case "1":
                            ctrl.set_cable_1()
                            flash("Cable length set to 0 meters successfully!", "success")
                        case "2":
                            ctrl.set_cable_2()
                            flash("Cable length set to 1 meter successfully!", "success")
                        case _:
                            flash("Invalid cable length selected.", "error")
                case "set_function":
                    function = request.form.get("function")
                    match function:
                        case "cg":
                            ctrl.set_cg()
                            flash("Function set to C-G successfully!", "success")
                        case "c":
                            ctrl.set_c()
                            flash("Function set to C successfully!", "success")
                        case "g":
                            ctrl.set_g()
                            flash("Function set to G successfully!", "success")
                        case "cgt":
                            ctrl.set_cgtfunc()
                            flash("Function set to C-G-T successfully!", "success")
                        case "ct":
                            ctrl.set_ctfunc()
                            flash("Function set to C-T successfully!", "success")
                        case "gt":
                            ctrl.set_gtfunc()
                            flash("Function set to G-T successfully!", "success")
                        case _:
                            flash("Invalid function selected.", "error")
                case "set_meas_speed":
                    meas_speed = request.form.get("meas_speed")
                    match meas_speed:
                        case "fast":
                            ctrl.set_fast()
                            flash("Measurement speed set to Fast successfully!", "success")
                        case "medium":
                            ctrl.set_medium()
                            flash("Measurement speed set to Medium successfully!", "success")
                        case "slow":
                            ctrl.set_slow()
                            flash("Measurement speed set to Slow successfully!", "success")
                        case _:
                            flash("Invalid measurement speed selected.", "error")
                case "set_meas_range":
                    meas_range = request.form.get("meas_range")
                    match meas_range:
                        case "auto":
                            ctrl.set_auto()
                            flash("Measurement range set to Auto successfully!", "success")
                        case "manual1":
                            ctrl.set_10nf()
                            flash("Measurement range set to 10nF/10mS successfully!", "success")
                        case "manual2":
                            ctrl.set_100pf()
                            flash("Measurement range set to 100pF/1mS successfully!", "success")
                        case "manual3":
                            ctrl.set_10pf()
                            flash("Measurement range set to 1pF/100uS successfully!", "success")
                        case _:
                            flash("Invalid measurement range selected.", "error")
                case "set_sweep":
                    sweep_mode = request.form.get("sweep_mode")
                    match sweep_mode:
                        case "int":
                            ctrl.set_int()
                            flash("Sweep mode set to Repeat successfully!", "success")
                        case "ext":
                            ctrl.set_ext()
                            flash("Sweep mode set to External successfully!", "success")
                        case "hold":
                            ctrl.set_hold()
                            flash("Sweep mode set to Single successfully!", "success")
                        case _:
                            flash("Invalid sweep mode selected.", "error")
                case "set_bias_mode":
                    bias_mode = request.form.get("bias_mode")
                    match bias_mode:
                        case "dc":
                            #ctrl.set_DCV()
                            flash("Bias mode set to DC successfully!", "success")
                        case "single":
                            ctrl.single_config()
                            flash("Bias mode set to Single successfully!", "success")
                        case "double":
                            ctrl.set_double()
                            flash("Bias mode set to Double successfully!", "success") 
                        case _:
                            flash("Invalid bias mode selected.", "error")
                case "set_sig_level":
                    sig_level = request.form.get("sig_level")
                    match sig_level:
                        case "30":
                            ctrl.set_signal_30()
                            flash("Signal level set to 30V successfully!", "success")
                        case "10":
                            ctrl.set_signal_10()
                            flash("Signal level set to 10V successfully!", "success")
                        case _:
                            flash("Invalid signal level selected.", "error")
                case _:
                    flash("Invalid action selected.", "error")
        
        # Default to cgt mode if no mode is set
        if "mode" not in session:
            session["mode"] = "cgt"

        return render_template("configuration.html", connection_type="Real Connection", settings=session["settings"])
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for("home"))
    
@app.route('/parameter', methods=["GET", "POST"])
def parameter():
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
            match action:
                case "update_settings":
                    sweep_type = request.form.get("sweep_type", "")
                    if sweep_type == "voltage":
                        session["settings"].update({
                            "DC_V": float(request.form['DC_V']),
                            "Start_V": float(request.form['Start_V']),
                            "Stop_V": float(request.form['Stop_V']),
                            "Step_V": float(request.form['Step_V']),
                            "Hold_T": float(request.form['Hold_T']),
                            "Step_T": float(request.form['Step_T']),
                        })
                        ctrl.set_DCV(session["settings"]["DC_V"])
                        ctrl.set_StartV(session["settings"]["Start_V"])
                        ctrl.set_StopV(session["settings"]["Stop_V"])
                        ctrl.set_StepV(session["settings"]["Step_V"])
                        ctrl.set_Hold_Time(session["settings"]["Hold_T"])
                        ctrl.set_StepT(session["settings"]["Step_T"])
                        flash("Voltage settings updated successfully!", "success")

                    elif sweep_type == "time":
                        session["settings"].update({
                            "Pulse": float(request.form['Pulse']),
                            "Meas": float(request.form['Meas']),
                            "Nofread": float(request.form['Nofread']),
                            "Pulse_Width": float(request.form['Pulse_Width']),
                            "Meas_Interval": float(request.form['Meas_Interval']),
                        })
                        ctrl.set_Pulse(session["settings"]["Pulse"])
                        ctrl.set_Measure_pulse(session["settings"]["Meas"])
                        ctrl.set_NOFREAD(session["settings"]["Nofread"])
                        ctrl.set_th(session["settings"]["Pulse_Width"])
                        ctrl.set_td(session["settings"]["Meas_Interval"])
                        flash("Time settings updated successfully!", "success")

                    else:
                        flash("Invalid sweep type provided for settings update.", "danger")

                case "start_pulse_sweep":
                    csv_file_name = ctrl.pulse_sweep()
                    if csv_file_name:
                        csv_file_path = os.path.join(os.environ['USERPROFILE'], 'Documents', 'HPData', csv_file_name)
                        user = get_user_by_email(session['email'])
                        add_measurement(
                            user_id=user[0],
                            test_type="Pulse Measurement",
                            csv_file_path=csv_file_path
                        )
                        flash("Pulse Sweep Measurement completed! Data saved to CSV and database.", "success")
                    else:
                        flash("Pulse Sweep Measurement failed. No data received.", "error")

                case "start_measurement":
                    measurement_type = request.form.get("sweep_type") or "voltage"
                    print(f"Measurement type selected: {measurement_type}")

                    csv_file_name = None
                    if measurement_type == "voltage":
                        print(f"Executing C-V measurement...")
                        csv_file_name = ctrl.sweep_measure()  # Assuming this is for C-V
                    elif measurement_type == "time":
                        print(f"Executing C-T measurement...")
                        csv_file_name = ctrl.sweep_measure()  # Assuming this is for C-T


                    if csv_file_name:
                        csv_file_path = os.path.join(os.environ['USERPROFILE'], 'Documents', 'HPData', csv_file_name)
                        user = get_user_by_email(session['email'])
                        add_measurement(
                            user_id=user[0],
                            test_type=measurement_type.upper() + " Measurement",
                            csv_file_path=csv_file_path
                        )
                        flash("Measurement completed successfully! Data saved to CSV and database.", "success")
                    else:
                        flash("Measurement failed. No data received.", "error")

                case _:
                    flash("Unknown action.", "error")

                    
        connection_status, terminal_output = check_connection_status()
        return render_template("parameter.html", connection_status=connection_status, terminal_output=terminal_output, settings=session["settings"])

    except Exception as e:
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for("home"))

@app.route('/graph', methods=["GET", "POST"])
def graph():
    # Check if the user is logged in
    if 'email' not in session:
        flash("Please log in to access this page.", "error")
        return redirect(url_for("login"))

    # Provide default graph_settings if accessed directly
    graph_settings = {
        "csv_file_name": "example.csv",  # Replace with a default or example file name
        "csv_file_path": "",  # No file path available when accessed directly
        "measurement": None  # No measurement data available
    }

    return render_template("graph.html", graph_settings=graph_settings)

@app.route('/wizardgraph')
def wizardgraph():
    # Check if the user is logged in
    if 'email' not in session:
        flash("Please log in to access this page.", "error")
        return redirect(url_for("login"))

    # Example: Retrieve the CSV file path from the database or session
    csv_file_path = session.get('csv_file_path')  # Or retrieve it from the database
    if not csv_file_path:
        flash("CSV file path is missing.", "error")
        return redirect(url_for('history'))

    # Pass the file path to the template
    graph_settings = {'csv_file_path': csv_file_path}
    return render_template('wizardgraph.html', graph_settings=graph_settings)

@app.route('/history', methods=["GET"])
def history():
    # Check if the user is logged in
    if 'email' not in session:
        flash("Please log in to access this page.", "error")
        return redirect(url_for("login"))

    # Get the user information
    user = get_user_by_email(session['email'])
    if not user:
        flash("User not found. Please log in again.", "error")
        return redirect(url_for("login"))

    # Fetch measurements for the logged-in user
    measurements = get_measurements(user_id=user[0])  # user[0] is the user ID

    return render_template("history.html", measurements=measurements)

@app.route('/view_measurement/<int:measurement_id>', methods=["GET"])
def view_measurement(measurement_id):
    # Check if the user is logged in
    if 'email' not in session:
        flash("Please log in to access this page.", "error")
        return redirect(url_for("login"))

    # Fetch the measurement data by ID
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT measurement_id, date_recorded, time_recorded, user_id, test_type, csv_file_path
        FROM measurements WHERE measurement_id = ?
    ''', (measurement_id,))
    measurement = cursor.fetchone()
    conn.close()

    if not measurement:
        flash("Measurement not found.", "error")
        return redirect(url_for("history"))

    # Verify that the CSV file exists in the HPData folder
    csv_file_path = measurement[5]
    if not os.path.isabs(csv_file_path):
        # Convert relative path to absolute path in the HPData folder
        csv_file_path = os.path.join(os.environ['USERPROFILE'], 'Documents', 'HPData', csv_file_path)

    if not os.path.isfile(csv_file_path):
        flash("CSV file not found or is not a valid file.", "error")
        return redirect(url_for("history"))

    # Extract only the file name to pass to the template
    csv_file_name = os.path.basename(csv_file_path)

     # For other measurement types, render the graph.html template
    return render_template(
        "graph.html",
        graph_settings={
            "csv_file_name": csv_file_name,  # Pass only the file name
            "csv_file_path": csv_file_path,  # Pass the full file path for download
            "measurement": measurement
        }
    )

@app.route('/delete_measurement/<int:measurement_id>', methods=["POST"])
def delete_measurement(measurement_id):
    # Check if the user is logged in
    if 'email' not in session:
        flash("Please log in to access this page.", "error")
        return redirect(url_for("login"))

    # Fetch the measurement data to get the file path
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT csv_file_path FROM measurements WHERE measurement_id = ?
    ''', (measurement_id,))
    measurement = cursor.fetchone()

    if measurement:
        csv_file_path = measurement[0]  # Get the file path from the database
        if csv_file_path and os.path.exists(csv_file_path):
            try:
                os.remove(csv_file_path)  # Delete the file from the filesystem
                print(f"Deleted file: {csv_file_path}")
            except Exception as e:
                print(f"Error deleting file: {csv_file_path}. Error: {e}")
                flash(f"Error deleting file: {csv_file_path}.", "error")

        # Delete the measurement from the database
        cursor.execute('''
            DELETE FROM measurements WHERE measurement_id = ?
        ''', (measurement_id,))
        conn.commit()
        flash("Measurement and associated file deleted successfully.", "success")
    else:
        flash("Measurement not found.", "error")

    conn.close()
    return redirect(url_for("history"))

@app.route('/admin_measure', methods=["GET"])
def admin_measure():
    """Admin page to view all measurements."""
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
        return redirect(url_for("home"))

    # Fetch all measurements from the database
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT m.measurement_id, m.date_recorded, m.time_recorded, u.first_name || ' ' || u.last_name AS full_name, m.test_type
        FROM measurements m
        JOIN users u ON m.user_id = u.id
        ORDER BY m.date_recorded DESC, m.time_recorded DESC
    ''')
    measurements = cursor.fetchall()
    conn.close()

    return render_template("admin_measure.html", measurements=measurements)

# USER PAGES ################################################################################################################################################
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

    # Fetch all users except the demo user
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute("SELECT first_name, last_name, email, id, is_admin FROM users WHERE email != 'demo@hp4280a.com'")
    users = cursor.fetchall()
    conn.close()

    return render_template("documentation.html", users=users, logged_in_email=session['email'])

@app.route('/login', methods=["POST", "GET"])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = get_user_by_email(email)
        if user:
            stored_password = user[4]  # Assuming user[4] is the password column
            logged_in = False
            
            try:
                # Check if the stored password is hashed
                if bcrypt.checkpw(password.encode('utf-8'), stored_password):
                    session["email"] = email  # Store email in session
                    logged_in = True
            except TypeError:
                # If the stored password is plain text, hash it and update the database
                if password == stored_password:  # Plain-text password match
                    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                    conn = sqlite3.connect(DB_path)
                    cursor = conn.cursor()
                    cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_password, user[0]))
                    conn.commit()
                    conn.close()
                    
                    # Log the user in after updating the password
                    session["email"] = email
                    logged_in = True
                    flash("Your password has been secured.", "info")
            
            if logged_in:
                try:
                    # Try to get or create controller to establish connection
                    get_controller()
                    flash("Login successful! Device connection established.", "success")
                except Exception as e:
                    flash(f"Login successful, but device connection failed: {str(e)}", "warning")
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

@app.route('/settings', methods=["GET", "POST"])
def settings():
    # Check if the user is logged in
    if 'email' not in session:
        flash("Please log in to access this page.", "error")
        return redirect(url_for("login"))

    # Prevent the demo user from accessing the settings page
    if session['email'] == "demo@hp4280a.com":
        flash("Demo user cannot access the settings page.", "error")
        return redirect(url_for("home"))

    # Get the current user
    user = get_user_by_email(session['email'])
    if not user:
        flash("User not found. Please log in again.", "error")
        return redirect(url_for("login"))

    if request.method == "POST":
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")
        new_email = request.form.get("email")

        # Validate current password
        if not bcrypt.checkpw(current_password.encode('utf-8'), user[4]):  # Assuming user[4] is the hashed password
            flash("Current password is incorrect.", "error")
            return redirect(url_for("settings"))

        # Validate new password and confirmation
        if new_password and new_password != confirm_password:
            flash("New password and confirmation do not match.", "error")
            return redirect(url_for("settings"))

        # Update the user's email and/or password
        conn = sqlite3.connect(DB_path)
        cursor = conn.cursor()
        if new_email:
            cursor.execute("UPDATE users SET email = ? WHERE id = ?", (new_email, user[0]))
            session['email'] = new_email  # Update session email
        if new_password:
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())  # Hash and salt the new password
            cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_password, user[0]))
        conn.commit()
        conn.close()

        flash("Settings updated successfully!", "success")
        return redirect(url_for("settings"))

    return render_template("settings.html", user=user)

# NON PAGES ####################################################################################################################################################
@app.route('/uploads/<path:filename>')
def serve_uploads(filename):
    # Update the path to point to the Documents/HPData folder
    hp_data_folder = os.path.join(os.environ['USERPROFILE'], 'Documents', 'HPData')
    return send_from_directory(hp_data_folder, filename)

@app.route('/reset_connection', methods=["POST"])
def reset_connection():
    if 'email' not in session:
        flash("Please log in to access this page.", "error")
        return redirect(url_for("login"))

    session_id = session['email']
    try:
        # Remove existing controller instance if it exists
        if session_id in gpib_connections:
            # Try to disconnect the current connection
            old_ctrl = gpib_connections[session_id]
            if hasattr(old_ctrl.conn, "disconnect"):
                old_ctrl.conn.disconnect()
            del gpib_connections[session_id]

        # Reinitialize the controller with a fresh connection
        ctrl = get_controller()
        ctrl.clear()  # Clear the controller
        flash("Connection reset and re-established successfully!", "success")
    except Exception as e:
        flash(f"Error during reset: {str(e)}", "error")

    return redirect(request.referrer or url_for("home"))

# LAUNCHING THE APP #######################################################################################################################################
if __name__ == '__main__':
    # Create a WebView window. Use for production.
    webview.create_window('HP 4280A Controller', app, width=1920, height=1080)  # Pass the Flask app to the WebView window
    webview.start()

    # Start the Flask app via web browser. Use for debugging and testing.
    #app.run(debug=True, host="0.0.0.0", port=5001)