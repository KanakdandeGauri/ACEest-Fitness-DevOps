from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime, date

app = Flask(__name__)
app.secret_key = "aceest-fitness-secret-key"

DB_NAME = "aceest_fitness.db"

PROGRAMS = {
    "Fat Loss (FL) – 3 day": {
        "factor": 22,
        "description": "3-day full-body fat loss"
    },
    "Fat Loss (FL) – 5 day": {
        "factor": 24,
        "description": "5-day split, higher volume fat loss"
    },
    "Muscle Gain (MG) – PPL": {
        "factor": 35,
        "description": "Push/Pull/Legs hypertrophy"
    },
    "Beginner (BG)": {
        "factor": 26,
        "description": "3-day simple beginner full-body"
    }
}

WORKOUT_TYPES = [
    "Strength",
    "Hypertrophy",
    "Conditioning",
    "Mixed",
    "Mobility"
]


# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()

    # -----------------------------------------------------
    # Clients
    # -----------------------------------------------------

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
            target_adherence INTEGER
        )
    """)

    # -----------------------------------------------------
    # Existing v2.0/v2.1/v2.2 progress
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT,
            week TEXT,
            adherence INTEGER
        )
    """)

    # -----------------------------------------------------
    # Workouts
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Exercises
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Body metrics
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Upgrade older v2.1/v2.2 clients table if necessary
    # -----------------------------------------------------

    columns = conn.execute(
        "PRAGMA table_info(clients)"
    ).fetchall()

    existing_columns = {
        column["name"] for column in columns
    }

    required_columns = {
        "height": "REAL",
        "target_weight": "REAL",
        "target_adherence": "INTEGER"
    }

    for column_name, column_type in required_columns.items():

        if column_name not in existing_columns:

            conn.execute(
                f"ALTER TABLE clients ADD COLUMN "
                f"{column_name} {column_type}"
            )

    conn.commit()
    conn.close()


# ---------------------------------------------------------
# CLIENT FUNCTIONS
# ---------------------------------------------------------

def calculate_calories(weight, program):
    return int(
        float(weight) * PROGRAMS[program]["factor"]
    )


def get_client(name):
    conn = get_db_connection()

    client = conn.execute(
        """
        SELECT *
        FROM clients
        WHERE name = ?
        """,
        (name,)
    ).fetchone()

    conn.close()

    return client


def get_all_clients():
    conn = get_db_connection()

    clients = conn.execute(
        """
        SELECT *
        FROM clients
        ORDER BY name
        """
    ).fetchall()

    conn.close()

    return clients


# ---------------------------------------------------------
# PROGRESS
# ---------------------------------------------------------

def get_all_progress():
    conn = get_db_connection()

    progress = conn.execute(
        """
        SELECT *
        FROM progress
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    return progress


def get_client_progress(name):
    conn = get_db_connection()

    progress = conn.execute(
        """
        SELECT week, adherence
        FROM progress
        WHERE client_name = ?
        ORDER BY id
        """,
        (name,)
    ).fetchall()

    conn.close()

    return progress


# ---------------------------------------------------------
# WORKOUTS
# ---------------------------------------------------------

def get_workout_history(name):
    conn = get_db_connection()

    workouts = conn.execute(
        """
        SELECT
            w.id,
            w.date,
            w.workout_type,
            w.duration_min,
            w.notes,
            e.name AS exercise_name,
            e.sets,
            e.reps,
            e.weight AS exercise_weight
        FROM workouts w
        LEFT JOIN exercises e
            ON w.id = e.workout_id
        WHERE w.client_name = ?
        ORDER BY w.date DESC, w.id DESC
        """,
        (name,)
    ).fetchall()

    conn.close()

    return workouts


# ---------------------------------------------------------
# BODY METRICS
# ---------------------------------------------------------

def get_client_metrics(name):
    conn = get_db_connection()

    metrics = conn.execute(
        """
        SELECT *
        FROM metrics
        WHERE client_name = ?
        ORDER BY date DESC, id DESC
        """,
        (name,)
    ).fetchall()

    conn.close()

    return metrics


def get_weight_chart_data(name):
    conn = get_db_connection()

    rows = conn.execute(
        """
        SELECT date, weight
        FROM metrics
        WHERE client_name = ?
          AND weight IS NOT NULL
        ORDER BY date
        """,
        (name,)
    ).fetchall()

    conn.close()

    return {
        "dates": [row["date"] for row in rows],
        "weights": [row["weight"] for row in rows]
    }


# ---------------------------------------------------------
# BMI
# ---------------------------------------------------------

def calculate_bmi(height, weight):
    if not height or not weight:
        return None

    height_m = float(height) / 100.0

    if height_m <= 0:
        return None

    return round(
        float(weight) / (height_m * height_m),
        1
    )


def get_bmi_category(bmi):
    if bmi is None:
        return None

    if bmi < 18.5:
        return {
            "category": "Underweight",
            "risk": "Potential nutrient deficiency, low energy."
        }

    if bmi < 25:
        return {
            "category": "Normal",
            "risk": "Low risk if active and strong."
        }

    if bmi < 30:
        return {
            "category": "Overweight",
            "risk": (
                "Moderate risk; focus on adherence "
                "and progressive activity."
            )
        }

    return {
        "category": "Obese",
        "risk": (
            "Higher risk; prioritize fat loss, "
            "consistency, and supervision."
        )
    }


# ---------------------------------------------------------
# MAIN PAGE
# ---------------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def index():

    form_data = {
        "name": "",
        "age": "",
        "height": "",
        "weight": "",
        "program": "",
        "target_weight": "",
        "target_adherence": "",
        "adherence": 0
    }

    selected_client = None
    summary = None

    chart_data = {
        "weeks": [],
        "adherence": []
    }

    weight_chart_data = {
        "dates": [],
        "weights": []
    }

    bmi_info = None

    workout_history = []
    metrics = []

    if request.method == "POST":

        action = request.form.get("action")

        # -------------------------------------------------
        # SAVE CLIENT
        # -------------------------------------------------

        if action == "save":

            name = request.form.get(
                "name", ""
            ).strip()

            age = request.form.get(
                "age", ""
            ).strip()

            height = request.form.get(
                "height", ""
            ).strip()

            weight = request.form.get(
                "weight", ""
            ).strip()

            program = request.form.get(
                "program", ""
            ).strip()

            target_weight = request.form.get(
                "target_weight", ""
            ).strip()

            target_adherence = request.form.get(
                "target_adherence", ""
            ).strip()

            adherence = request.form.get(
                "adherence", "0"
            )

            form_data.update({
                "name": name,
                "age": age,
                "height": height,
                "weight": weight,
                "program": program,
                "target_weight": target_weight,
                "target_adherence": target_adherence,
                "adherence": adherence
            })

            if not name:
                flash(
                    "Name is required.",
                    "error"
                )

            elif not program:
                flash(
                    "Program is required.",
                    "error"
                )

            elif program not in PROGRAMS:
                flash(
                    "Please select a valid program.",
                    "error"
                )

            else:

                try:

                    age_value = (
                        int(age)
                        if age
                        else None
                    )

                    height_value = (
                        float(height)
                        if height
                        else None
                    )

                    weight_value = (
                        float(weight)
                        if weight
                        else None
                    )

                    target_weight_value = (
                        float(target_weight)
                        if target_weight
                        else None
                    )

                    target_adherence_value = (
                        int(target_adherence)
                        if target_adherence
                        else None
                    )

                    calories = (
                        calculate_calories(
                            weight_value,
                            program
                        )
                        if weight_value
                        else None
                    )

                    conn = get_db_connection()

                    conn.execute(
                        """
                        INSERT OR REPLACE INTO clients
                        (
                            name,
                            age,
                            height,
                            weight,
                            program,
                            calories,
                            target_weight,
                            target_adherence
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            name,
                            age_value,
                            height_value,
                            weight_value,
                            program,
                            calories,
                            target_weight_value,
                            target_adherence_value
                        )
                    )

                    conn.commit()
                    conn.close()

                    selected_client = get_client(name)

                    flash(
                        "Client data saved successfully.",
                        "success"
                    )

                except ValueError:

                    flash(
                        "Please enter valid numeric values.",
                        "error"
                    )

        # -------------------------------------------------
        # LOAD CLIENT
        # -------------------------------------------------

        elif action == "load":

            name = request.form.get(
                "name", ""
            ).strip()

            form_data["name"] = name

            client = get_client(name)

            if not name:

                flash(
                    "Enter a client name to load.",
                    "error"
                )

            elif client is None:

                flash(
                    "Client not found.",
                    "error"
                )

            else:

                selected_client = client

                form_data.update({
                    "name": client["name"],
                    "age": client["age"] or "",
                    "height": client["height"] or "",
                    "weight": client["weight"] or "",
                    "program": client["program"] or "",
                    "target_weight":
                        client["target_weight"] or "",
                    "target_adherence":
                        client["target_adherence"] or "",
                    "adherence": 0
                })

                flash(
                    "Client loaded successfully.",
                    "success"
                )

        # -------------------------------------------------
        # SAVE WEEKLY PROGRESS
        # -------------------------------------------------

        elif action == "progress":

            name = request.form.get(
                "name", ""
            ).strip()

            adherence = request.form.get(
                "adherence", "0"
            )

            form_data.update({
                "name": name,
                "adherence": adherence
            })

            client = get_client(name)

            if not name:

                flash(
                    "Enter a client name first.",
                    "error"
                )

            elif client is None:

                flash(
                    "Client not found. Save the client first.",
                    "error"
                )

            else:

                try:

                    adherence_value = int(
                        float(adherence)
                    )

                    if not 0 <= adherence_value <= 100:
                        raise ValueError

                    week = datetime.now().strftime(
                        "Week %U - %Y"
                    )

                    conn = get_db_connection()

                    conn.execute(
                        """
                        INSERT INTO progress
                        (
                            client_name,
                            week,
                            adherence
                        )
                        VALUES (?, ?, ?)
                        """,
                        (
                            name,
                            week,
                            adherence_value
                        )
                    )

                    conn.commit()
                    conn.close()

                    selected_client = get_client(name)

                    flash(
                        "Weekly progress logged successfully.",
                        "success"
                    )

                except ValueError:

                    flash(
                        "Adherence must be between 0 and 100.",
                        "error"
                    )

        # -------------------------------------------------
        # ADHERENCE CHART
        # -------------------------------------------------

        elif action == "chart":

            name = request.form.get(
                "name", ""
            ).strip()

            form_data["name"] = name

            client = get_client(name)

            if not name:

                flash(
                    "Enter a client name first.",
                    "error"
                )

            elif client is None:

                flash(
                    "Client not found.",
                    "error"
                )

            else:

                selected_client = client

                progress_data = get_client_progress(
                    name
                )

                if not progress_data:

                    flash(
                        "No progress data available for this client.",
                        "error"
                    )

                else:

                    chart_data = {
                        "weeks": [
                            row["week"]
                            for row in progress_data
                        ],
                        "adherence": [
                            row["adherence"]
                            for row in progress_data
                        ]
                    }

                    form_data.update({
                        "name": client["name"],
                        "age": client["age"] or "",
                        "height": client["height"] or "",
                        "weight": client["weight"] or "",
                        "program": client["program"] or "",
                        "target_weight":
                            client["target_weight"] or "",
                        "target_adherence":
                            client["target_adherence"] or ""
                    })

        # -------------------------------------------------
        # VIEW WEIGHT CHART
        # -------------------------------------------------

        elif action == "weight_chart":

            name = request.form.get(
                "name", ""
            ).strip()

            form_data["name"] = name

            client = get_client(name)

            if not name:

                flash(
                    "Enter a client name first.",
                    "error"
                )

            elif client is None:

                flash(
                    "Client not found.",
                    "error"
                )

            else:

                selected_client = client

                weight_chart_data = get_weight_chart_data(
                    name
                )

                if not weight_chart_data["dates"]:

                    flash(
                        "No weight metrics available for this client.",
                        "error"
                    )

                else:

                    form_data.update({
                        "name": client["name"],
                        "age": client["age"] or "",
                        "height": client["height"] or "",
                        "weight": client["weight"] or "",
                        "program": client["program"] or "",
                        "target_weight":
                            client["target_weight"] or "",
                        "target_adherence":
                            client["target_adherence"] or ""
                    })

        # -------------------------------------------------
        # BMI
        # -------------------------------------------------

        elif action == "bmi":

            name = request.form.get(
                "name", ""
            ).strip()

            form_data.update({
                "name": name,
                "height": request.form.get(
                    "height", ""
                ).strip(),
                "weight": request.form.get(
                    "weight", ""
                ).strip()
            })

            client = get_client(name)

            try:

                height_value = float(
                    form_data["height"]
                )

                weight_value = float(
                    form_data["weight"]
                )

                bmi = calculate_bmi(
                    height_value,
                    weight_value
                )

                if bmi is None:
                    raise ValueError

                bmi_info = get_bmi_category(bmi)

                bmi_info["value"] = bmi
                bmi_info["name"] = name

            except ValueError:

                flash(
                    "Enter valid height and weight values.",
                    "error"
                )

        # -------------------------------------------------
        # VIEW PROGRAM / SUMMARY
        # -------------------------------------------------

        elif action == "view":

            name = request.form.get(
                "name", ""
            ).strip()

            age = request.form.get(
                "age", ""
            ).strip()

            height = request.form.get(
                "height", ""
            ).strip()

            weight = request.form.get(
                "weight", ""
            ).strip()

            program = request.form.get(
                "program", ""
            ).strip()

            target_weight = request.form.get(
                "target_weight", ""
            ).strip()

            target_adherence = request.form.get(
                "target_adherence", ""
            ).strip()

            adherence = request.form.get(
                "adherence", "0"
            )

            form_data.update({
                "name": name,
                "age": age,
                "height": height,
                "weight": weight,
                "program": program,
                "target_weight": target_weight,
                "target_adherence": target_adherence,
                "adherence": adherence
            })

            if program not in PROGRAMS:

                flash(
                    "Please select a valid program.",
                    "error"
                )

            else:

                try:

                    calories = (
                        calculate_calories(
                            float(weight),
                            program
                        )
                        if weight
                        else None
                    )

                    summary = {
                        "name": name,
                        "age": age,
                        "height": height,
                        "weight": weight,
                        "program": program,
                        "calories": calories,
                        "target_weight":
                            target_weight,
                        "target_adherence":
                            target_adherence
                    }

                except ValueError:

                    flash(
                        "Weight must be a valid number.",
                        "error"
                    )

        # -------------------------------------------------
        # WORKOUT HISTORY
        # -------------------------------------------------

        elif action == "history":

            name = request.form.get(
                "name", ""
            ).strip()

            form_data["name"] = name

            client = get_client(name)

            if not name:

                flash(
                    "Enter a client name first.",
                    "error"
                )

            elif client is None:

                flash(
                    "Client not found.",
                    "error"
                )

            else:

                selected_client = client

                workout_history = get_workout_history(
                    name
                )

                metrics = get_client_metrics(
                    name
                )

        # -------------------------------------------------
        # RESET
        # -------------------------------------------------

        elif action == "reset":

            return redirect(
                url_for("index")
            )

    clients = get_all_clients()
    progress = get_all_progress()

    return render_template(
        "index.html",
        programs=PROGRAMS,
        workout_types=WORKOUT_TYPES,
        form_data=form_data,
        selected_client=selected_client,
        summary=summary,
        clients=clients,
        progress=progress,
        chart_data=chart_data,
        weight_chart_data=weight_chart_data,
        bmi_info=bmi_info,
        workout_history=workout_history,
        metrics=metrics
    )


# ---------------------------------------------------------
# LOG WORKOUT
# ---------------------------------------------------------

@app.route("/workout", methods=["POST"])
def log_workout():

    name = request.form.get(
        "client_name", ""
    ).strip()

    workout_date = request.form.get(
        "date", ""
    ).strip()

    workout_type = request.form.get(
        "workout_type", ""
    ).strip()

    duration = request.form.get(
        "duration", ""
    ).strip()

    notes = request.form.get(
        "notes", ""
    ).strip()

    exercise_name = request.form.get(
        "exercise_name", ""
    ).strip()

    sets = request.form.get(
        "sets", ""
    ).strip()

    reps = request.form.get(
        "reps", ""
    ).strip()

    exercise_weight = request.form.get(
        "exercise_weight", ""
    ).strip()

    if not name:

        flash(
            "Client name is required.",
            "error"
        )

        return redirect(url_for("index"))

    if not workout_date:
        workout_date = date.today().isoformat()

    if not workout_type:

        flash(
            "Workout type is required.",
            "error"
        )

        return redirect(url_for("index"))

    try:

        duration_value = int(duration)

        sets_value = (
            int(sets)
            if sets
            else None
        )

        reps_value = (
            int(reps)
            if reps
            else None
        )

        weight_value = (
            float(exercise_weight)
            if exercise_weight
            else None
        )

        conn = get_db_connection()

        cursor = conn.execute(
            """
            INSERT INTO workouts
            (
                client_name,
                date,
                workout_type,
                duration_min,
                notes
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name,
                workout_date,
                workout_type,
                duration_value,
                notes
            )
        )

        workout_id = cursor.lastrowid

        if exercise_name:

            conn.execute(
                """
                INSERT INTO exercises
                (
                    workout_id,
                    name,
                    sets,
                    reps,
                    weight
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    workout_id,
                    exercise_name,
                    sets_value,
                    reps_value,
                    weight_value
                )
            )

        conn.commit()
        conn.close()

        flash(
            "Workout logged successfully.",
            "success"
        )

    except ValueError:

        flash(
            "Duration, sets, reps and weight must be valid numbers.",
            "error"
        )

    return redirect(
        url_for("index")
    )


# ---------------------------------------------------------
# LOG BODY METRICS
# ---------------------------------------------------------

@app.route("/metrics", methods=["POST"])
def log_metrics():

    name = request.form.get(
        "client_name", ""
    ).strip()

    metric_date = request.form.get(
        "date", ""
    ).strip()

    weight = request.form.get(
        "weight", ""
    ).strip()

    waist = request.form.get(
        "waist", ""
    ).strip()

    bodyfat = request.form.get(
        "bodyfat", ""
    ).strip()

    if not name:

        flash(
            "Client name is required.",
            "error"
        )

        return redirect(url_for("index"))

    if not metric_date:
        metric_date = date.today().isoformat()

    try:

        weight_value = (
            float(weight)
            if weight
            else None
        )

        waist_value = (
            float(waist)
            if waist
            else None
        )

        bodyfat_value = (
            float(bodyfat)
            if bodyfat
            else None
        )

        conn = get_db_connection()

        conn.execute(
            """
            INSERT INTO metrics
            (
                client_name,
                date,
                weight,
                waist,
                bodyfat
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name,
                metric_date,
                weight_value,
                waist_value,
                bodyfat_value
            )
        )

        conn.commit()
        conn.close()

        # Also update current client weight.
        if weight_value and weight_value > 0:

            conn = get_db_connection()

            conn.execute(
                """
                UPDATE clients
                SET weight = ?
                WHERE name = ?
                """,
                (
                    weight_value,
                    name
                )
            )

            conn.commit()
            conn.close()

        flash(
            "Body metrics logged successfully.",
            "success"
        )

    except ValueError:

        flash(
            "Body metric values must be valid numbers.",
            "error"
        )

    return redirect(
        url_for("index")
    )


# ---------------------------------------------------------
# START APPLICATION
# ---------------------------------------------------------

if __name__ == "__main__":

    init_db()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )