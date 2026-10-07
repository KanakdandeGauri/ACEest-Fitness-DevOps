from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3
from datetime import datetime, date
from functools import wraps
import io
import random

try:
    from fpdf import FPDF
except ImportError:
    FPDF = None

app = Flask(__name__)
app.secret_key = "aceest-fitness-secret-key"

APP_VERSION = "3.1.2"
DB_NAME = "aceest_fitness.db"

PROGRAMS = {
    "Fat Loss (FL) – 3 day": {"factor": 22, "desc": "3-day full-body fat loss"},
    "Fat Loss (FL) – 5 day": {"factor": 24, "desc": "5-day split, higher volume fat loss"},
    "Muscle Gain (MG) – PPL": {"factor": 35, "desc": "Push/Pull/Legs hypertrophy"},
    "Beginner (BG)": {"factor": 26, "desc": "3-day simple beginner full-body"},
}

EXERCISES_POOL = {
    "Strength": ["Squat", "Deadlift", "Bench Press", "Overhead Press", "Pull-Up", "Barbell Row"],
    "Hypertrophy": ["Leg Press", "Incline Dumbbell Press", "Lat Pulldown", "Lateral Raise", "Bicep Curl", "Tricep Extension"],
    "Conditioning": ["Running", "Cycling", "Rowing", "Burpees", "Jump Rope", "Kettlebell Swings"],
    "Full Body": ["Push-Up", "Pull-Up", "Lunge", "Plank", "Dumbbell Row", "Dumbbell Press"],
}


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    """)
    cur.execute(
        "INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
        ("admin", "admin", "Admin"),
    )

    cur.execute("""
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
            membership_expiry TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT,
            week TEXT,
            adherence INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT,
            date TEXT,
            workout_type TEXT,
            duration_min INTEGER,
            notes TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_id INTEGER,
            name TEXT,
            sets INTEGER,
            reps INTEGER,
            weight REAL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT,
            date TEXT,
            weight REAL,
            waist REAL,
            bodyfat REAL
        )
    """)

    # Keep older databases compatible with the v3.1.2 client fields.
    existing_columns = {row["name"] for row in cur.execute("PRAGMA table_info(clients)").fetchall()}
    migrations = {
        "height": "ALTER TABLE clients ADD COLUMN height REAL",
        "target_weight": "ALTER TABLE clients ADD COLUMN target_weight REAL",
        "target_adherence": "ALTER TABLE clients ADD COLUMN target_adherence INTEGER",
        "membership_expiry": "ALTER TABLE clients ADD COLUMN membership_expiry TEXT",
    }
    for column, sql in migrations.items():
        if column not in existing_columns:
            cur.execute(sql)

    conn.commit()
    conn.close()


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped_view


def calculate_calories(weight, program):
    try:
        factor = PROGRAMS.get(program, {}).get("factor", 25)
        return int(float(weight) * factor)
    except (TypeError, ValueError):
        return None


def get_client(name):
    conn = get_db_connection()
    client = conn.execute("SELECT * FROM clients WHERE name = ?", (name,)).fetchone()
    conn.close()
    return client


def get_all_clients():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM clients ORDER BY name").fetchall()
    conn.close()
    return rows


def get_all_progress(client_name=None):
    conn = get_db_connection()
    if client_name:
        rows = conn.execute(
            "SELECT * FROM progress WHERE client_name = ? ORDER BY id",
            (client_name,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM progress ORDER BY id DESC").fetchall()
    conn.close()
    return rows


def get_workouts(client_name):
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM workouts WHERE client_name = ? ORDER BY date DESC, id DESC",
        (client_name,),
    ).fetchall()
    conn.close()
    return rows


def get_metrics(client_name):
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM metrics WHERE client_name = ? ORDER BY date ASC, id ASC",
        (client_name,),
    ).fetchall()
    conn.close()
    return rows


def bmi_info(height, weight):
    try:
        height_m = float(height) / 100
        weight_kg = float(weight)
        if height_m <= 0 or weight_kg <= 0:
            return None, "Not available"
        bmi = weight_kg / (height_m * height_m)
        if bmi < 18.5:
            category = "Underweight"
        elif bmi < 25:
            category = "Normal"
        elif bmi < 30:
            category = "Overweight"
        else:
            category = "Obese"
        return round(bmi, 1), category
    except (TypeError, ValueError, ZeroDivisionError):
        return None, "Not available"


def generate_program(client_name, experience):
    client = get_client(client_name)
    if not client:
        return []

    program_name = client["program"] or ""
    focus = "Full Body"
    if "Fat Loss" in program_name:
        focus = "Conditioning"
    elif "Muscle Gain" in program_name:
        focus = "Hypertrophy"

    experience = experience.lower()
    if experience == "beginner":
        sets_range, reps_range, days = (2, 3), (8, 12), 3
    elif experience == "intermediate":
        sets_range, reps_range, days = (3, 4), (8, 15), 4
    else:
        sets_range, reps_range, days = (4, 5), (6, 15), 5

    weekly_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"][:days]
    generated = []

    for day_name in weekly_days:
        count = 3 if days < 4 else 4
        exercises = random.sample(EXERCISES_POOL[focus], k=count)
        for exercise in exercises:
            generated.append({
                "day": day_name,
                "exercise": exercise,
                "sets": random.randint(*sets_range),
                "reps": random.randint(*reps_range),
            })
    return generated


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db_connection()
        user = conn.execute(
            "SELECT username, role FROM users WHERE username = ? AND password = ?",
            (username, password),
        ).fetchone()
        conn.close()

        if user:
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect(url_for("index"))

        flash("Invalid credentials. Try admin / admin.", "error")

    return render_template("login.html", app_version=APP_VERSION)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    selected_client = request.form.get("client_name") or request.args.get("client_name") or session.get("current_client")
    generated_program = session.pop("generated_program", [])
    message = None

    if request.method == "POST":
        action = request.form.get("action")

        if action == "save":
            name = request.form.get("name", "").strip()
            try:
                age = int(request.form.get("age") or 0)
                height = float(request.form.get("height") or 0)
                weight = float(request.form.get("weight") or 0)
                target_weight = float(request.form.get("target_weight") or 0)
                target_adherence = int(request.form.get("target_adherence") or 0)
            except ValueError:
                flash("Age, height, weight, target weight and adherence must be valid numbers.", "error")
                return redirect(url_for("index"))

            program = request.form.get("program", "")
            membership = request.form.get("membership_expiry", "").strip()

            if not name:
                flash("Name is required.", "error")
            elif program not in PROGRAMS:
                flash("Please select a valid program.", "error")
            else:
                calories = calculate_calories(weight, program)
                conn = get_db_connection()
                conn.execute("""
                    INSERT INTO clients
                    (name, age, height, weight, program, calories, target_weight,
                     target_adherence, membership_expiry)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(name) DO UPDATE SET
                        age=excluded.age,
                        height=excluded.height,
                        weight=excluded.weight,
                        program=excluded.program,
                        calories=excluded.calories,
                        target_weight=excluded.target_weight,
                        target_adherence=excluded.target_adherence,
                        membership_expiry=excluded.membership_expiry
                """, (name, age, height, weight, program, calories, target_weight,
                      target_adherence, membership))
                conn.commit()
                conn.close()
                selected_client = name
                session["current_client"] = name
                flash(f"Client '{name}' saved successfully.", "success")

        elif action == "load":
            selected_client = request.form.get("client_name", "").strip()
            if selected_client:
                session["current_client"] = selected_client
                flash(f"Loaded client '{selected_client}'.", "success")

        elif action == "progress":
            selected_client = request.form.get("client_name", "").strip()
            try:
                adherence = max(0, min(100, int(request.form.get("adherence") or 0)))
            except ValueError:
                adherence = 0
            if selected_client and get_client(selected_client):
                week = datetime.now().strftime("Week %U - %Y")
                conn = get_db_connection()
                conn.execute(
                    "INSERT INTO progress (client_name, week, adherence) VALUES (?, ?, ?)",
                    (selected_client, week, adherence),
                )
                conn.commit()
                conn.close()
                session["current_client"] = selected_client
                flash("Weekly adherence saved.", "success")
            else:
                flash("Select a valid client first.", "error")

        elif action == "workout":
            selected_client = request.form.get("client_name", "").strip()
            if not get_client(selected_client):
                flash("Select a valid client before logging a workout.", "error")
            else:
                workout_date = request.form.get("workout_date") or date.today().isoformat()
                workout_type = request.form.get("workout_type", "Mixed")
                try:
                    duration = int(request.form.get("duration_min") or 0)
                    sets = int(request.form.get("sets") or 0)
                    reps = int(request.form.get("reps") or 0)
                    exercise_weight = float(request.form.get("exercise_weight") or 0)
                except ValueError:
                    flash("Workout duration, sets, reps and weight must be numeric.", "error")
                    return redirect(url_for("index", client_name=selected_client))

                notes = request.form.get("workout_notes", "").strip()
                exercise_name = request.form.get("exercise_name", "").strip()

                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO workouts (client_name, date, workout_type, duration_min, notes) VALUES (?, ?, ?, ?, ?)",
                    (selected_client, workout_date, workout_type, duration, notes),
                )
                workout_id = cur.lastrowid
                if exercise_name:
                    cur.execute(
                        "INSERT INTO exercises (workout_id, name, sets, reps, weight) VALUES (?, ?, ?, ?, ?)",
                        (workout_id, exercise_name, sets, reps, exercise_weight),
                    )
                conn.commit()
                conn.close()
                session["current_client"] = selected_client
                flash("Workout logged successfully.", "success")

        elif action == "metric":
            selected_client = request.form.get("client_name", "").strip()
            if not get_client(selected_client):
                flash("Select a valid client before saving metrics.", "error")
            else:
                metric_date = request.form.get("metric_date") or date.today().isoformat()
                try:
                    metric_weight = float(request.form.get("metric_weight") or 0)
                    waist = float(request.form.get("waist") or 0)
                    bodyfat = float(request.form.get("bodyfat") or 0)
                except ValueError:
                    flash("Metric values must be numeric.", "error")
                    return redirect(url_for("index", client_name=selected_client))

                conn = get_db_connection()
                conn.execute(
                    "INSERT INTO metrics (client_name, date, weight, waist, bodyfat) VALUES (?, ?, ?, ?, ?)",
                    (selected_client, metric_date, metric_weight, waist, bodyfat),
                )
                conn.commit()
                conn.close()
                session["current_client"] = selected_client
                flash("Body metrics saved.", "success")

        elif action == "generate_ai":
            selected_client = request.form.get("client_name", "").strip()
            experience = request.form.get("experience", "beginner").lower()
            if selected_client and experience in {"beginner", "intermediate", "advanced"}:
                generated_program = generate_program(selected_client, experience)
                session["generated_program"] = generated_program
                session["current_client"] = selected_client
                flash("AI-style workout program generated from the 3.1.2 rules.", "success")
            else:
                flash("Select a client and valid experience level.", "error")

        elif action == "reset":
            session.pop("current_client", None)
            generated_program = []
            selected_client = None

    if selected_client and get_client(selected_client):
        session["current_client"] = selected_client
    else:
        selected_client = None
        session.pop("current_client", None)

    client = get_client(selected_client) if selected_client else None
    progress = get_all_progress(selected_client) if selected_client else []
    workouts = get_workouts(selected_client) if selected_client else []
    metrics = get_metrics(selected_client) if selected_client else []

    chart_data = {
        "weeks": [row["week"] for row in progress],
        "adherence": [row["adherence"] for row in progress],
        "metric_dates": [row["date"] for row in metrics],
        "metric_weights": [row["weight"] for row in metrics],
    }

    bmi, bmi_category = bmi_info(client["height"], client["weight"]) if client else (None, "Not available")

    return render_template(
        "index.html",
        app_version=APP_VERSION,
        username=session.get("username"),
        role=session.get("role"),
        programs=PROGRAMS,
        clients=get_all_clients(),
        client=client,
        progress=progress,
        workouts=workouts,
        metrics=metrics,
        chart_data=chart_data,
        bmi=bmi,
        bmi_category=bmi_category,
        generated_program=generated_program,
        today=date.today().isoformat(),
    )


@app.route("/export/<path:client_name>")
@login_required
def export_pdf(client_name):
    client = get_client(client_name)
    if not client:
        flash("Client not found.", "error")
        return redirect(url_for("index"))

    if FPDF is None:
        flash("PDF export requires the fpdf package. Install it with: pip install fpdf2", "error")
        return redirect(url_for("index", client_name=client_name))

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"Client Report - {client_name}", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.ln(8)

    fields = [
        ("Name", client["name"]),
        ("Age", client["age"]),
        ("Height", f'{client["height"]} cm'),
        ("Weight", f'{client["weight"]} kg'),
        ("Program", client["program"]),
        ("Calories", client["calories"]),
        ("Target Weight", f'{client["target_weight"]} kg'),
        ("Target Adherence", f'{client["target_adherence"]}%'),
        ("Membership Expiry", client["membership_expiry"] or "Not set"),
    ]
    for label, value in fields:
        pdf.cell(0, 9, f"{label}: {value}", ln=True)

    pdf.ln(5)
    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 9, "BMI", ln=True)
    pdf.set_font("Arial", "", 12)
    bmi, category = bmi_info(client["height"], client["weight"])
    pdf.cell(0, 9, f"{bmi if bmi is not None else 'N/A'} ({category})", ln=True)

    pdf_bytes = bytes(pdf.output())
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{client_name}_report.pdf",
    )


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=True)
