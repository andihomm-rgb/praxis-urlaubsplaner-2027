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
    "2027-11-01": "Allerheiligen",
    "2027-12-25": "1. Weihnachtstag",
    "2027-12-26": "2. Weihnachtstag"
}

# Schulferien Baden-Württemberg 2027
FERIEN_BW_2027 = [
    ("2027-01-01", "2027-01-09", "Weihnachtsferien"),
    ("2027-02-08", "2027-02-12", "Faschingsferien"),
    ("2027-03-22", "2027-04-03", "Osterferien"),
    ("2027-05-18", "2027-05-29", "Pfingstferien"),
    ("2027-07-29", "2027-09-11", "Sommerferien"),
    ("2027-11-02", "2027-11-06", "Herbstferien"),
    ("2027-12-23", "2027-12-31", "Weihnachtsferien")
]

def is_ferien(date_str):
    for s, e, name in FERIEN_BW_2027:
        if s <= date_str <= e:
            return name
    return None

def get_employees():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM employees ORDER BY role DESC, name ASC", conn)
    conn.close()
    return df

def get_absences(year=2027, status_filter=None):
    conn = get_db_connection()
    query = """
        SELECT a.*, e.name as employee_name, e.role as employee_role
        FROM absence_requests a
        JOIN employees e ON a.employee_id = e.id
        WHERE strftime('%Y', a.start_date) = ? OR strftime('%Y', a.end_date) = ?
    """
    params = [str(year), str(year)]
    if status_filter:
        query += " AND a.status = ?"
        params.append(status_filter)
    query += " ORDER BY a.start_date ASC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def calculate_overtime_balance(emp_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT SUM(hours) FROM overtime_journal WHERE employee_id = ?", (emp_id,))
    res = c.fetchone()[0]
    conn.close()
    return res if res else 0.0

# -----------------------------------------------------------------------------
# LOGIN & SITZUNGS-STEUERUNG (SESSION STATE)
# -----------------------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_id = None

st.sidebar.title("🦷 Praxis Urlaubsplaner 2027")

employees_df = get_employees()

# Fall 1: Benutzer ist noch NICHT angemeldet
if not st.session_state.authenticated:
    st.sidebar.subheader("🔒 Bitte anmelden")
    
    selected_user_name = st.sidebar.selectbox("👤 Benutzer auswählen", employees_df['name'].tolist())
    selected_user = employees_df[employees_df['name'] == selected_user_name].iloc[0]
    
    # Passwort / PIN Eingabefeld (verdeckt durch type="password")
    entered_pin = st.sidebar.text_input("🔑 PIN / Passwort", type="password")
    
    if st.sidebar.button("Anmelden"):
        if entered_pin == str(selected_user['pin']):
            st.session_state.authenticated = True
            st.session_state.user_id = selected_user['id']
            st.sidebar.success("✅ Erfolgreich angemeldet!")
            st.rerun()
        else:
            st.sidebar.error("❌ Falsches Passwort / PIN!")
            
    # Stoppt die App-Ausführung hier, sodass keine Daten ohne Login sichtbar sind
    st.stop()

# Fall 2: Benutzer IST erfolgreich angemeldet
current_user = employees_df[employees_df['id'] == st.session_state.user_id].iloc[0]
is_admin = current_user['is_admin'] == 1
user_role = current_user['role']

# Benutzer-Info und Logout-Button in der Sidebar
st.sidebar.write(f"Angemeldet als: **{current_user['name']}**")
st.sidebar.info(f"**Rolle:** {user_role}\n\n**Rechte:** {'🔑 Admin / Leitung' if is_admin else '👤 Mitarbeiter'}")

if st.sidebar.button("🚪 Abmelden"):
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.rerun()

# Navigation anzeigen
menu = ["📅 Masterkalender & Raumplanung", "📝 Meine Anträge & Urlaub", "⏳ Überstundenkonto (+/-)", "⚙️ Verwaltung & Genehmigung"]
if not is_admin:
    menu = ["📅 Masterkalender & Raumplanung", "📝 Meine Anträge & Urlaub", "⏳ Überstundenkonto (+/-)"]

choice = st.sidebar.radio("Navigation", menu)

st.sidebar.markdown("---")
st.sidebar.caption("Zahnarztpraxis mit 4 Behandlungszimmern\n(2x Zahnbehandlung, 2x Prophylaxe)")
menu = ["📅 Masterkalender & Raumplanung", "📝 Meine Anträge & Urlaub", "⏳ Überstundenkonto (+/-)", "⚙️ Verwaltung & Genehmigung"]
if not is_admin:
    menu = ["📅 Masterkalender & Raumplanung", "📝 Meine Anträge & Urlaub", "⏳ Überstundenkonto (+/-)"]

choice = st.sidebar.radio("Navigation", menu)

st.sidebar.markdown("---")
st.sidebar.caption("Zahnarztpraxis mit 4 Behandlungszimmern\n(2x Zahnbehandlung, 2x Prophylaxe)")

# TAB 1: MASTERKALENDER & RAUMPLANUNG
if choice == "📅 Masterkalender & Raumplanung":
    st.header("📅 Masterkalender 2027 & Raumbelegungs-Analyse")
    st.caption("Echtzeit-Analyse der Behandlungszimmer basierend auf der aktuellen Personalstärke.")

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        selected_month = st.selectbox("Monat wählen", [
            "Januar", "Februar", "März", "April", "Mai", "Juni", 
            "Juli", "August", "September", "Oktober", "November", "Dezember"
        ], index=0)
    month_idx = [
        "Januar", "Februar", "März", "April", "Mai", "Juni", 
        "Juli", "August", "September", "Oktober", "November", "Dezember"
    ].index(selected_month) + 1
    
    start_dt = datetime.date(2027, month_idx, 1)
    if month_idx == 12:
        end_dt = datetime.date(2027, 12, 31)
    else:
        end_dt = datetime.date(2027, month_idx + 1, 1) - datetime.timedelta(days=1)

    absences_df = get_absences(year=2027, status_filter='Genehmigt')
    
    st.subheader("🔍 Tages-Inspector & Zimmer-Empfehlung")
    
    insp_col1, insp_col2 = st.columns([1, 2])
    with insp_col1:
        inspect_date = st.date_input("Tag im Detail prüfen", value=start_dt, min_value=datetime.date(2027, 1, 1), max_value=datetime.date(2027, 12, 31))
        inspect_str = inspect_date.strftime("%Y-%m-%d")
        
        feiertag_name = FEIERTAG_BW_2027.get(inspect_str)
        ferien_name = is_ferien(inspect_str)
        is_weekend = inspect_date.weekday() >= 5
        
        if feiertag_name:
            st.error(f"🎉 **Feiertag (BW):** {feiertag_name}")
        elif is_weekend:
            st.warning("⏸️ **Wochenende:** Praxis geschlossen")
        elif ferien_name:
            st.info(f"🏫 **Schulferien BW:** {ferien_name}")

    with insp_col2:
        absent_emp_ids = set()
        absent_details = {}
        
        for _, row in absences_df.iterrows():
            s_d = datetime.datetime.strptime(row['start_date'], "%Y-%m-%d").date()
            e_d = datetime.datetime.strptime(row['end_date'], "%Y-%m-%d").date()
            if s_d <= inspect_date <= e_d:
                absent_emp_ids.add(row['employee_id'])
                absent_details[row['employee_id']] = row['absence_type']
                
        all_emp = get_employees()
        present_counts = {"Zahnarzt": 0, "Assistenz": 0, "Prophylaxe": 0, "Rezeption": 0, "Azubi": 0}
        
        working_list = []
        absent_list = []
        
        for _, emp in all_emp.iterrows():
            if emp['id'] in absent_emp_ids:
                absent_list.append(f"{emp['name']} ({emp['role']}) - *{absent_details[emp['id']]}*")
            else:
                present_counts[emp['role']] = present_counts.get(emp['role'], 0) + 1
                working_list.append(f"{emp['name']} ({emp['role']})")
                
        doctors_present = present_counts.get("Zahnarzt", 0)
        assistants_present = present_counts.get("Assistenz", 0)
        proph_present = present_counts.get("Prophylaxe", 0)
        reception_present = present_counts.get("Rezeption", 0)
        
        open_zahn_rooms = min(2, doctors_present, assistants_present)
        open_proph_rooms = min(2, proph_present)
        
        st.markdown(f"### Belegungsanalyse für {inspect_date.strftime('%d.%m.%Y')}")
        
        rc1, rc2, rc3, rc4 = st.columns(4)
        with rc1:
            st.metric("Zahnarzt-Zimmer (max 2)", f"{open_zahn_rooms} / 2 Geöffnet", 
                      delta="Voll besetzt" if open_zahn_rooms == 2 else ("Eingeschränkt" if open_zahn_rooms == 1 else "Geschlossen"),
                      delta_color="normal" if open_zahn_rooms > 0 else "inverse")
        with rc2:
            st.metric("Prophylaxe-Zimmer (max 2)", f"{open_proph_rooms} / 2 Geöffnet",
                      delta="Voll besetzt" if open_proph_rooms == 2 else ("Eingeschränkt" if open_proph_rooms == 1 else "Geschlossen"),
                      delta_color="normal" if open_proph_rooms > 0 else "inverse")
        with rc3:
            st.metric("Rezeption Besetzt", f"{reception_present} Pers.",
                      delta="OK" if reception_present >= 1 else "⚠️ Engpass!",
                      delta_color="normal" if reception_present >= 1 else "inverse")
        with rc4:
            st.metric("Gesamt Anwesend", f"{len(working_list)} / {len(all_emp)}")

        if open_zahn_rooms < 2:
            st.warning(f"💡 **Empfehlung Zimmerbelegung:** Nur **{open_zahn_rooms} Behandlungszimmer** öffnen! (Vorhanden: {doctors_present} Zahnarzt, {assistants_present} Assistenz). Zimmer {open_zahn_rooms + 1} muss blockiert werden.")
        else:
            st.success("✅ **Zahnbehandlung:** Beide Behandlungszimmer (Zimmer 1 & 2) können uneingeschränkt laufen.")
            
        if open_proph_rooms < 2:
            st.warning(f"💡 **Empfehlung Prophylaxe:** Nur **{open_proph_rooms} Prophylaxezimmer** öffnen! ({proph_present} Prophylaxekraft anwesend).")
        else:
            st.success("✅ **Prophylaxe:** Beide Prophylaxezimmer (Zimmer 3 & 4) sind voll besetzt.")

        with st.expander("👥 Detail-Anwesenheitsliste für diesen Tag anzeigen"):
            col_w, col_a = st.columns(2)
            with col_w:
                st.markdown("**🟢 Anwesend im Dienst:**")
                for w in working_list:
                    st.write(f"- {w}")
            with col_a:
                st.markdown("**🔴 Abwesend:**")
                if absent_list:
                    for a in absent_list:
                        st.write(f"- {a}")
                else:
                    st.write("*Keine Abwesenheiten*")

    st.markdown("---")
    st.subheader(f"🗓️ Monatsübersicht {selected_month} 2027")
    
    num_days = (end_dt - start_dt).days + 1
    days_list = [start_dt + datetime.timedelta(days=i) for i in range(num_days)]
    
    grid_data = []
    all_emp = get_employees()
    
    for _, emp in all_emp.iterrows():
        row_data = {"Mitarbeiter": emp['name'], "Rolle": emp['role']}
        emp_abs = absences_df[absences_df['employee_id'] == emp['id']]
        
        for d in days_list:
            d_str = d.strftime("%Y-%m-%d")
            day_num = d.day
            
            if d.weekday() >= 5:
                status_char = "WE"
            elif d_str in FEIERTAG_BW_2027:
                status_char = "FT"
            else:
                status_char = "Dienst"
                for _, abs_row in emp_abs.iterrows():
                    s_d = datetime.datetime.strptime(abs_row['start_date'], "%Y-%m-%d").date()
                    e_d = datetime.datetime.strptime(abs_row['end_date'], "%Y-%m-%d").date()
                    if s_d <= d <= e_d:
                        t = abs_row['absence_type']
                        if "Urlaub" in t:
                            status_char = "🌴 U"
                        elif "Krank" in t:
                            status_char = "🤒 K"
                        elif "Überstunden" in t:
                            status_char = "⏳ Ü"
                        elif "Schule" in t:
                            status_char = "🏫 S"
                        else:
                            status_char = "📌 A"
                        break
            row_data[str(day_num)] = status_char
        grid_data.append(row_data)
        
    grid_df = pd.DataFrame(grid_data)
    st.dataframe(grid_df, use_container_width=True, height=400)
    st.caption("Legende: **Dienst** = Regulär | **🌴 U** = Urlaub | **🤒 K** = Krankheit | **⏳ Ü** = Überstundenabbau | **🏫 S** = Berufsschule | **WE** = Wochenende | **FT** = Feiertag")

# TAB 2: MEINE ANTRÄGE & URLAUB
elif choice == "📝 Meine Anträge & Urlaub":
    st.header(f"📝 Urlaubs- & Abwesenheitsplanung für {current_user['name']}")
    
    with st.form("absence_request_form"):
        st.subheader("Neuen Antrag einreichen")
        
        col_type, col_start, col_end = st.columns([2, 1, 1])
        with col_type:
            absence_type = st.selectbox("Art der Abwesenheit", [
                "Urlaub (Ganztags)",
                "Urlaub (Halbtags)",
                "Überstundenabbau (Ganztags)",
                "Überstundenabbau (Stundenweise)",
                "Krankheit / Krankschreibung",
                "Berufsschule (Azubi)",
                "Fortbildung / Schulung"
            ])
        with col_start:
            start_date = st.date_input("Von Datum", value=datetime.date(2027, 6, 1))
        with col_end:
            end_date = st.date_input("Bis Datum", value=datetime.date(2027, 6, 1))
            
        hours_input = 0.0
        if "Stundenweise" in absence_type or "Halbtags" in absence_type:
            hours_input = st.number_input("Anzahl Stunden (bei stundenweise/halbtags)", min_value=0.5, max_value=12.0, value=4.0, step=0.5)
            
        emp_note = st.text_area("Anmerkung / Notiz zum Antrag (optional)", placeholder="z. B. Abstimmung bereits mit Kollegin erfolgt...")
        
        submit_btn = st.form_submit_button("🚀 Antrag kostenfrei einreichen")
        
        if submit_btn:
            if end_date < start_date:
                st.error("Das Enddatum darf nicht vor dem Startdatum liegen!")
            else:
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("""
                    INSERT INTO absence_requests (employee_id, absence_type, start_date, end_date, hours, employee_note, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'Ausstehend')
                """, (current_user['id'], absence_type, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), hours_input, emp_note))
                conn.commit()
                conn.close()
                st.success("✅ Ihr Antrag wurde erfolgreich eingereicht und liegt der Praxisleitung zur Genehmigung vor.")
                st.rerun()

    st.markdown("---")
    st.subheader("📋 Meine bisherigen Anträge 2027")
    
    conn = get_db_connection()
    my_requests = pd.read_sql_query("""
        SELECT absence_type as 'Art', start_date as 'Von', end_date as 'Bis', hours as 'Stunden', employee_note as 'Notiz Mitarbeiter', status as 'Status', admin_note as 'Notiz Leitung', created_at as 'Eingereicht am'
        FROM absence_requests
        WHERE employee_id = ?
        ORDER BY created_at DESC
    """, conn, params=[current_user['id']])
    conn.close()
    
    if not my_requests.empty:
        st.dataframe(my_requests, use_container_width=True)
    else:
        st.info("Sie haben noch keine Anträge für 2027 eingereicht.")

# TAB 3: ÜBERSTUNDENKONTO (+/-)
elif choice == "⏳ Überstundenkonto (+/-)":
    st.header(f"⏳ Überstundenkonto von {current_user['name']}")
    
    balance = calculate_overtime_balance(current_user['id'])
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Aktueller Überstundensaldo", f"{balance:+.1f} Std.", delta="Guthaben" if balance >= 0 else "Minusstunden", delta_color="normal" if balance >= 0 else "inverse")
    with c2:
        st.metric("Wöchentliche Sollzeit", f"{current_user['weekly_hours']} Std./Woche")
    with c3:
        st.metric("Jahresurlaub Kontingent", f"{current_user['vacation_days_per_year']} Tage")

    st.markdown("---")
    st.subheader("➕ / ➖ Mehrarbeit oder Einspringen manuell erfassen")
    st.caption("Hier können Sie z. B. eintragen, wenn Sie an freien Tagen wegen Krankheitsvertretung eingesprungen sind.")

    with st.form("overtime_form"):
        col_d, col_h, col_r = st.columns([1, 1, 2])
        with col_d:
            ot_date = st.date_input("Datum", value=datetime.date.today())
        with col_h:
            ot_hours = st.number_input("Stunden (+ für Überstunden, - für Abbau)", value=2.0, step=0.5)
        with col_r:
            ot_reason = st.text_input("Grund / Beschreibung", value="Aushilfe bei Krankheitsvertretung")
            
        ot_sub = st.form_submit_button("💾 Stunde auf Konto buchen")
        if ot_sub:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("""
                INSERT INTO overtime_journal (employee_id, date, hours, reason)
                VALUES (?, ?, ?, ?)
            """, (current_user['id'], ot_date.strftime("%Y-%m-%d"), ot_hours, ot_reason))
            conn.commit()
            conn.close()
            st.success(f"✅ {ot_hours:+.1f} Stunden wurden Ihrem Konto gutgeschrieben/abgebucht.")
            st.rerun()

    st.subheader("📜 Verlauf Überstundenkonto")
    conn = get_db_connection()
    ot_df = pd.read_sql_query("""
        SELECT date as 'Datum', hours as 'Stunden (+/-)', reason as 'Grund', created_at as 'Erfasst am'
        FROM overtime_journal
        WHERE employee_id = ?
        ORDER BY date DESC
    """, conn, params=[current_user['id']])
    conn.close()
    
    if not ot_df.empty:
        st.dataframe(ot_df, use_container_width=True)
    else:
        st.info("Noch keine Überstundeneinträge vorhanden.")

# TAB 4: VERWALTUNG & GENEHMIGUNG (ADMIN ONLY)
elif choice == "⚙️ Verwaltung & Genehmigung" and is_admin:
    st.header("⚙️ Praxisleitung: Genehmigungen & Personalverwaltung")
    
    tab_gen, tab_emp, tab_settings = st.tabs(["📌 Anträge Genehmigen", "👥 Mitarbeiter verwalten", "⚙️ Praxis-Parameter"])
    
    with tab_gen:
        st.subheader("Offene Anträge zur Prüfung")
        
        pending_df = get_absences(year=2027, status_filter='Ausstehend')
        
        if pending_df.empty:
            st.success("🎉 Keine offenen Anträge zur Genehmigung vorhanden.")
        else:
            for _, req in pending_df.iterrows():
                with st.expander(f"Antrag #{req['id']} - {req['employee_name']} ({req['employee_role']}): {req['absence_type']} [{req['start_date']} bis {req['end_date']}]"):
                    st.write(f"**Mitarbeiter-Notiz:** {req['employee_note'] if req['employee_note'] else 'Keine Notiz'}")
                    if req['hours'] > 0:
                        st.write(f"**Umfang:** {req['hours']} Stunden")
                        
                    admin_comment = st.text_input(f"Notiz von Leitung (Antrag #{req['id']})", key=f"admin_note_{req['id']}")
                    
                    b_col1, b_col2, b_col3 = st.columns(3)
                    with b_col1:
                        if st.button("✅ Genehmigen", key=f"app_{req['id']}"):
                            conn = get_db_connection()
                            c = conn.cursor()
                            c.execute("UPDATE absence_requests SET status = 'Genehmigt', admin_note = ? WHERE id = ?", (admin_comment, req['id']))
                            conn.commit()
                            conn.close()
                            st.success("Antrag genehmigt!")
                            st.rerun()
                    with b_col2:
                        if st.button("🟡 Teilweise Genehmigen", key=f"part_{req['id']}"):
                            conn = get_db_connection()
                            c = conn.cursor()
                            c.execute("UPDATE absence_requests SET status = 'Teilweise genehmigt', admin_note = ? WHERE id = ?", (admin_comment, req['id']))
                            conn.commit()
                            conn.close()
                            st.warning("Antrag als teilweise genehmigt markiert.")
                            st.rerun()
                    with b_col3:
                        if st.button("❌ Ablehnen", key=f"rej_{req['id']}"):
                            conn = get_db_connection()
                            c = conn.cursor()
                            c.execute("UPDATE absence_requests SET status = 'Abgelehnt', admin_note = ? WHERE id = ?", (admin_comment, req['id']))
                            conn.commit()
                            conn.close()
                            st.error("Antrag abgelehnt.")
                            st.rerun()

    with tab_emp:
        st.subheader("Mitarbeiterstamm & Arbeitszeiten")
        st.dataframe(get_employees(), use_container_width=True)
        
        with st.expander("➕ Neuen Mitarbeiter anlegen"):
            with st.form("add_emp_form"):
                new_name = st.text_input("Vollständiger Name")
                new_role = st.selectbox("Aufgabengruppe / Rolle", ["Zahnarzt", "Assistenz", "Prophylaxe", "Rezeption", "Azubi"])
                new_hours = st.number_input("Soll-Wochenstunden", value=38.0, step=1.0)
                new_vacation = st.number_input("Jahresurlaub (Tage)", value=30.0, step=1.0)
                new_is_admin = st.checkbox("Ist Praxisleitung / Admin (darf Anträge genehmigen)")
                
                add_emp_sub = st.form_submit_button("Mitarbeiter hinzufügen")
                if add_emp_sub and new_name:
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("""
                        INSERT INTO employees (name, role, is_admin, weekly_hours, vacation_days_per_year)
                        VALUES (?, ?, ?, ?, ?)
                    """, (new_name, new_role, 1 if new_is_admin else 0, new_hours, new_vacation))
                    conn.commit()
                    conn.close()
                    st.success(f"Mitarbeiter {new_name} angelegt!")
                    st.rerun()

    with tab_settings:
        st.subheader("Praxis-Konfiguration 2027")
        st.write("**Behandlungszimmer:** 4 Räume (2x Zahnärztliche Behandlung, 2x Prophylaxe)")
        st.write("**Bundesland für Feiertage & Schulferien:** Baden-Württemberg")
        st.info("Weitere Parameter wie z. B. gesperrte Urlaubszeiten oder Praxisurlaub können hier erweitert werden.")
