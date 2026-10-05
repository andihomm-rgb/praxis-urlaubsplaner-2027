import streamlit as st
import pandas as pd
import numpy as np
import datetime
import sqlite3

# Page Config
st.set_page_config(
    page_title="Zahnarztpraxis Urlaubs- & Raumplanung 2027",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    .stMetric {
        background-color: #f8f9fa;
        padding: 12px;
        border-radius: 8px;
        border-left: 4px solid #0284c7;
    }
    .status-approved {
        color: #15803d;
        font-weight: bold;
    }
    .status-pending {
        color: #b45309;
        font-weight: bold;
    }
    .status-rejected {
        color: #b91c1c;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Database Setup & Initialization
DB_FILE = "praxis_urlaub.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Employees table
    c.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            weekly_hours REAL DEFAULT 40.0,
            vacation_days_per_year REAL DEFAULT 30.0,
            pin TEXT DEFAULT '1234'
        )
    """)
    
    # Absence Requests table
    c.execute("""
        CREATE TABLE IF NOT EXISTS absence_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            absence_type TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            hours REAL DEFAULT 0,
            employee_note TEXT,
            status TEXT DEFAULT 'Ausstehend',
            admin_note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees (id)
        )
    """)
    
    # Overtime Journal table
    c.execute("""
        CREATE TABLE IF NOT EXISTS overtime_journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            hours REAL NOT NULL,
            reason TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees (id)
        )
    """)
    
    # Seed default employees if empty
    c.execute("SELECT COUNT(*) FROM employees")
    if c.fetchone()[0] == 0:
        default_staff = [
            ("Dr. Veit (Zahnarzt 1)", "Zahnarzt", 1, 40.0, 30.0, "1234"),
            ("Dr. Andi (Zahnarzt 2)", "Zahnarzt", 1, 40.0, 30.0, "1234"),
            ("Sarah M. (Assistenz)", "Assistenz", 0, 38.0, 30.0, "1234"),
            ("Laura K. (Assistenz)", "Assistenz", 0, 38.0, 30.0, "1234"),
            ("Julia R. (Assistenz / Teilzeit)", "Assistenz", 0, 20.0, 15.0, "1234"),
            ("Monika P. (Prophylaxe 1)", "Prophylaxe", 0, 35.0, 30.0, "1234"),
            ("Xuan T. (Prophylaxe 2)", "Prophylaxe", 0, 30.0, 25.0, "1234"),
            ("Anna F. (Rezeption 1)", "Rezeption", 0, 38.0, 30.0, "1234"),
            ("Jessica H. (Rezeption 2)", "Rezeption", 0, 20.0, 15.0, "1234"),
            ("Sabrina D. (Azubi)", "Azubi", 0, 38.0, 30.0, "1234"),
            ("Melanie K. (Aushilfe/Assistenz)", "Assistenz", 0, 15.0, 10.0, "1234")
        ]
        c.executemany("""
            INSERT INTO employees (name, role, is_admin, weekly_hours, vacation_days_per_year, pin)
            VALUES (?, ?, ?, ?, ?, ?)
        """, default_staff)
        
    conn.commit()
    conn.close()

init_db()

# Feiertage Baden-Württemberg 2027
FEIERTAG_BW_2027 = {
    "2027-01-01": "Neujahr",
    "2027-01-06": "Heilige Drei Könige",
    "2027-03-26": "Karfreitag",
    "2027-03-29": "Ostermontag",
    "2027-05-01": "Tag der Arbeit",
    "2027-05-06": "Christi Himmelfahrt",
    "2027-05-17": "Pfingstmontag",
    "2027-05-27": "Fronleichnam",
    "2027-10-03": "Tag der Deutschen Einheit",
    "2027-11-01":
