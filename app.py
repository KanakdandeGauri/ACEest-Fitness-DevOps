from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3
from datetime import date, datetime
import random
from io import BytesIO

try:
    from fpdf import FPDF
except ImportError:
    FPDF = None

app = Flask(__name__)
app.secret_key = "aceest-fitness-secret-key"

APP_VERSION = "3.2.4"
DB_NAME = "aceest_fitness.db"

PROGRAM_TEMPLATES = {
    "Fat Loss": [
        "Full Body HIIT",
        "Circuit Training",
        "Cardio + Weights",
    ],
    "Muscle Gain": [
        "Push/Pull/Legs",
        "Upper/Lower Split",
        "Full Body Strength",
    ],
    "Beginner": [
        "Full Body 3x/week",
        "Light Strength + Mobility",
    ],
}


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_column(conn, table, column, definition):
    columns = {
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            role TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            age INTEGER,
            height REAL,
            weight REAL,
            program TEXT,
            calories INTEGER,
            target_weight REAL,
            target_adherence INTEGER,
            membership_status TEXT,
            membership_end TEXT
        )
    """)

    # Keep older databases compatible with v3.2.4.
    for column, definition in [
        ("age", "INTEGER"),
        ("height", "REAL"),
        ("weight", "REAL"),
        ("program", "TEXT"),
        ("calories", "INTEGER"),
        ("target_weight", "REAL"),
        ("target_adherence", "INTEGER"),
        ("membership_status", "TEXT"),
        ("membership_end", "TEXT"),
    ]:
        ensure_column(conn, "clients", column, definition)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT,
            week TEXT,
            adherence INTEGER
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT,
            date TEXT,
            workout_type TEXT,
            duration_min INTEGER,
            notes TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_id INTEGER,
            name TEXT,
            sets INTEGER,
            reps INTEGER,
            weight REAL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT,
            date TEXT,
            weight REAL,
            waist REAL,
            bodyfat REAL
        )
    """)

    conn.execute(
        "INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
        ("admin", "admin", "Admin"),
    )

    conn.commit()
    conn.close()


def calculate_calories(weight, program):
    factors = {
        "Fat Loss": 22,
        "Muscle Gain": 35,
        "Beginner": 26,
    }

    try:
        weight = float(weight)
    except (TypeError, ValueError):
        return 0

    factor = next(
        (value for key, value in factors.items() if key.lower() in (program or "").lower()),
        26,
    )
    return round(weight * factor)


def get_client(name):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM clients WHERE name = ?", (name,)
    ).fetchone()
    conn.close()
    return row


def get_clients():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM clients ORDER BY name"
    ).fetchall()
    conn.close()
    return rows


def get_progress(name):
    conn = get_db()
    rows = conn.execute(
        "SELECT week, adherence FROM progress WHERE client_name = ? ORDER BY id",
        (name,),
    ).fetchall()
    conn.close()
    return rows


def get_workouts(name):
    conn = get_db()
    rows = conn.execute(
        """
        SELECT id, date, workout_type, duration_min, notes
        FROM workouts
        WHERE client_name = ?
        ORDER BY date DESC, id DESC
        """,
        (name,),
    ).fetchall()
    conn.close()
    return rows


def get_metrics(name):
    conn = get_db()
    rows = conn.execute(
        """
        SELECT date, weight, waist, bodyfat
        FROM metrics
        WHERE client_name = ?
        ORDER BY date
        """,
        (name,),
    ).fetchall()
    conn.close()
    return rows


def bmi_info(height, weight):
    try:
        height_m = float(height) / 100
        weight = float(weight)
        if height_m <= 0 or weight <= 0:
            return None, None
        bmi = weight / (height_m ** 2)
    except (TypeError, ValueError):
        return None, None

    if bmi < 18.5:
        category = "Underweight"
    elif bmi < 25:
        category = "Normal"
    elif bmi < 30:
        category = "Overweight"
    else:
        category = "Obese"

    return round(bmi, 1), category


def login_required():
    return "username" in session


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db()
        user = conn.execute(
            "SELECT username, role FROM users WHERE username=? AND password=?",
            (username, password),
        ).fetchone()
        conn.close()

        if user:
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect(url_for("index"))

        flash("Invalid credentials.", "error")

    return render_template("login.html", app_version=APP_VERSION)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/", methods=["GET", "POST"])
def index():
    if not login_required():
        return redirect(url_for("login"))

    selected_client = session.get("current_client")

    if request.method == "POST":
        action = request.form.get("action")

        if action == "save_client":
            name = request.form.get("name", "").strip()
            if not name:
                flash("Client name is required.", "error")
                return redirect(url_for("index"))

            try:
                age = int(request.form.get("age") or 0)
                height = float(request.form.get("height") or 0)
                weight = float(request.form.get("weight") or 0)
                target_weight = float(request.form.get("target_weight") or 0)
                target_adherence = int(request.form.get("target_adherence") or 0)
            except ValueError:
                flash("Please enter valid numeric client details.", "error")
                return redirect(url_for("index"))

            program = request.form.get("program", "").strip()
            membership_status = request.form.get("membership_status", "Active")
            membership_end = request.form.get("membership_end", "").strip()
            calories = calculate_calories(weight, program)

            conn = get_db()
            existing = conn.execute(
                "SELECT id FROM clients WHERE name=?", (name,)
            ).fetchone()

            if existing:
                conn.execute(
                    """
                    UPDATE clients
                    SET age=?, height=?, weight=?, program=?, calories=?,
                        target_weight=?, target_adherence=?,
                        membership_status=?, membership_end=?
                    WHERE name=?
                    """,
                    (
                        age, height, weight, program, calories,
                        target_weight, target_adherence,
                        membership_status, membership_end, name,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO clients
                    (name, age, height, weight, program, calories,
                     target_weight, target_adherence, membership_status,
                     membership_end)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        name, age, height, weight, program, calories,
                        target_weight, target_adherence,
                        membership_status, membership_end,
                    ),
                )

            conn.commit()
            conn.close()
            session["current_client"] = name
            flash(f"Client {name} saved successfully.", "success")

        elif action == "select_client":
            name = request.form.get("client_name", "").strip()
            if name and get_client(name):
                session["current_client"] = name
            else:
                session.pop("current_client", None)

        elif action == "generate_program":
            name = selected_client
            if not name or not get_client(name):
                flash("Select a client first.", "error")
            else:
                program_type = random.choice(list(PROGRAM_TEMPLATES.keys()))
                program_detail = random.choice(PROGRAM_TEMPLATES[program_type])

                conn = get_db()
                conn.execute(
                    "UPDATE clients SET program=? WHERE name=?",
                    (program_detail, name),
                )
                conn.commit()
                conn.close()

                flash(
                    f"Program generated for {name}: {program_detail}",
                    "success",
                )

        elif action == "add_progress":
            name = selected_client
            if not name:
                flash("Select a client first.", "error")
            else:
                week = request.form.get(
                    "week",
                    datetime.now().strftime("Week %U - %Y"),
                )
                try:
                    adherence = max(
                        0, min(100, int(request.form.get("adherence", 0)))
                    )
                except ValueError:
                    adherence = 0

                conn = get_db()
                conn.execute(
                    """
                    INSERT INTO progress (client_name, week, adherence)
                    VALUES (?, ?, ?)
                    """,
                    (name, week, adherence),
                )
                conn.commit()
                conn.close()
                flash("Weekly progress saved.", "success")

        elif action == "add_workout":
            name = selected_client
            if not name:
                flash("Select a client first.", "error")
            else:
                workout_date = request.form.get(
                    "workout_date", date.today().isoformat()
                )
                workout_type = request.form.get("workout_type", "")
                try:
                    duration = int(request.form.get("duration_min") or 0)
                except ValueError:
                    duration = 0
                notes = request.form.get("notes", "").strip()

                conn = get_db()
                conn.execute(
                    """
                    INSERT INTO workouts
                    (client_name, date, workout_type, duration_min, notes)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (name, workout_date, workout_type, duration, notes),
                )
                conn.commit()
                conn.close()
                flash("Workout saved.", "success")

        elif action == "add_metric":
            name = selected_client
            if not name:
                flash("Select a client first.", "error")
            else:
                metric_date = request.form.get(
                    "metric_date", date.today().isoformat()
                )
                try:
                    metric_weight = float(request.form.get("metric_weight") or 0)
                    waist = float(request.form.get("waist") or 0)
                    bodyfat = float(request.form.get("bodyfat") or 0)
                except ValueError:
                    metric_weight = waist = bodyfat = 0

                conn = get_db()
                conn.execute(
                    """
                    INSERT INTO metrics
                    (client_name, date, weight, waist, bodyfat)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (name, metric_date, metric_weight, waist, bodyfat),
                )
                conn.commit()
                conn.close()
                flash("Body metric saved.", "success")

        return redirect(url_for("index"))

    selected_client = session.get("current_client")
    client = get_client(selected_client) if selected_client else None

    progress = get_progress(selected_client) if selected_client else []
    workouts = get_workouts(selected_client) if selected_client else []
    metrics = get_metrics(selected_client) if selected_client else []

    chart_data = {
        "weeks": [row["week"] for row in progress],
        "adherence": [row["adherence"] for row in progress],
        "metric_dates": [row["date"] for row in metrics],
        "weights": [row["weight"] for row in metrics],
    }

    bmi, bmi_category = (
        bmi_info(client["height"], client["weight"])
        if client
        else (None, None)
    )

    return render_template(
        "index.html",
        app_version=APP_VERSION,
        username=session.get("username"),
        role=session.get("role"),
        programs=PROGRAM_TEMPLATES,
        clients=get_clients(),
        client=client,
        selected_client=selected_client,
        progress=progress,
        workouts=workouts,
        metrics=metrics,
        chart_data=chart_data,
        bmi=bmi,
        bmi_category=bmi_category,
        today=date.today().isoformat(),
    )


@app.route("/report/<client_name>")
def report(client_name):
    if not login_required():
        return redirect(url_for("login"))

    client = get_client(client_name)
    if not client:
        flash("Client not found.", "error")
        return redirect(url_for("index"))

    if FPDF is None:
        flash("FPDF is not installed. Install it with: pip install fpdf2", "error")
        return redirect(url_for("index"))

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"ACEest Client Report - {client_name}", ln=True)

    pdf.set_font("Arial", "", 11)
    fields = [
        ("ID", client["id"]),
        ("Name", client["name"]),
        ("Age", client["age"]),
        ("Height", client["height"]),
        ("Weight", client["weight"]),
        ("Program", client["program"]),
        ("Calories", client["calories"]),
        ("Target Weight", client["target_weight"]),
        ("Target Adherence", client["target_adherence"]),
        ("Membership", client["membership_status"]),
        ("Membership End", client["membership_end"]),
    ]

    for label, value in fields:
        pdf.cell(0, 8, f"{label}: {value if value not in (None, '') else 'N/A'}", ln=True)

    pdf_bytes = pdf.output()
    if isinstance(pdf_bytes, str):
        pdf_bytes = pdf_bytes.encode("latin-1")

    return send_file(
        BytesIO(bytes(pdf_bytes)),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{client_name}_report.pdf",
    )


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=True)
