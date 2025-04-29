import sqlite3
import csv
import os
from datetime import datetime
import bcrypt

# Define the path to the database file
DB_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")

def init_db():
    """Initialize the database and create necessary tables."""
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()

    # Create the users table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0
        )
    ''')

    # Create the measurements table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS measurements (
            measurement_id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_recorded DATE NOT NULL,
            time_recorded TIME NOT NULL,
            user_id INTEGER NOT NULL,
            test_type TEXT NOT NULL,
            csv_file_path TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Check if the `users` table is empty
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]

    if user_count == 0:
        # Add the first user as an admin
        hashed_password = bcrypt.hashpw("Welcome1".encode('utf-8'), bcrypt.gensalt())
        cursor.execute('''
            INSERT INTO users (first_name, last_name, email, password, is_admin)
            VALUES (?, ?, ?, ?, ?)
        ''', ("Admin", "User", "admin@hp4280a.com", hashed_password, 1))
        print("Admin user created with email: admin@hp4280a.com and password: Welcome1")

        # Add a demo user with simple credentials
        cursor.execute('''
            INSERT INTO users (first_name, last_name, email, password, is_admin)
            VALUES (?, ?, ?, ?, ?)
        ''', ("Demo", "User", "demo@hp4280a.com", "demo", 0))
        print("Demo user created with email: demo@hp4280a.com and password: demo")

    conn.commit()
    conn.close()

def add_user(first_name, last_name, email, password, is_admin=None):
    """Add a new user to the database."""
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()

    # Check if there are any existing admin users
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
    admin_count = cursor.fetchone()[0]

    # Automatically make the first user after initialization an admin if no admins exist
    if admin_count == 0:
        is_admin = 1
    elif is_admin is None:
        is_admin = 0

    # Add the user to the database
    cursor.execute('''
        INSERT INTO users (first_name, last_name, email, password, is_admin)
        VALUES (?, ?, ?, ?, ?)
    ''', (first_name, last_name, email, password, is_admin))
    conn.commit()
    conn.close()

def get_user_by_id(user_id):
    """Retrieve a user from the database by ID."""
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM users WHERE id = ?
    ''', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_user_by_email(email):
    """Retrieve a user from the database by email."""
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM users WHERE email = ?
    ''', (email,))
    user = cursor.fetchone()
    conn.close()
    return user

def delete_user_by_id(user_id):
    """Delete a user from the database by ID."""
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM users WHERE id = ?
    ''', (user_id,))
    conn.commit()
    conn.close()


def add_measurement(user_id, test_type, csv_file_path):
    """
    Add a new measurement to the database and return the measurement ID.
    """
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO measurements (user_id, test_type, csv_file_path, date_recorded, time_recorded)
        VALUES (?, ?, ?, DATE('now'), TIME('now'))
    ''', (user_id, test_type, csv_file_path))
    conn.commit()
    measurement_id = cursor.lastrowid  # Get the ID of the newly inserted measurement
    conn.close()
    return measurement_id


def get_measurements(user_id=None):
    """Retrieve measurements from the database, optionally filtered by user_id."""
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    if user_id:
        cursor.execute('''
            SELECT * FROM measurements WHERE user_id = ?
        ''', (user_id,))
    else:
        cursor.execute('SELECT * FROM measurements')
    measurements = cursor.fetchall()
    conn.close()
    return measurements

def export_measurements_to_csv(filename="measurements.csv"):
    """Export all measurements to a CSV file."""
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT m.measurement_id, m.date_recorded, m.time_recorded,
               u.first_name || ' ' || u.last_name AS full_name, m.test_type
        FROM measurements m
        JOIN users u ON m.user_id = u.id
    ''')
    measurements = cursor.fetchall()
    conn.close()
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Measurement ID', 'Date', 'Time', 'Full Name', 'Test Type'])
        writer.writerows(measurements)

def migrate_passwords():
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, password FROM users")
    users = cursor.fetchall()

    for user_id, password in users:
        try:
            # Check if the password is already hashed
            bcrypt.checkpw("test".encode('utf-8'), password)
        except TypeError:
            # If the password is plain text, hash it
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_password, user_id))

    conn.commit()
    conn.close()
    print("Password migration completed.")