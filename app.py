from flask import Flask, render_template, request, Response
import sqlite3
import csv
import io
from datetime import datetime

app = Flask(__name__)

DB_NAME = "aceest_fitness.db"


# ---------------------------------------------------------
# FITNESS PROGRAMS
# ---------------------------------------------------------

PROGRAMS = {
    "Fat Loss (FL)": {
        "workout": "Back Squat, Cardio, Bench, Deadlift, Recovery",
        "diet": "Egg Whites, Chicken, Fish Curry",
        "color_class": "fat-loss",
        "calorie_factor": 22
    },

    "Muscle Gain (MG)": {
        "workout": "Squat, Bench, Deadlift, Press, Rows",
        "diet": "Eggs, Biryani, Mutton Curry",
        "color_class": "muscle-gain",
        "calorie_factor": 35
    },

    "Beginner (BG)": {
        "workout": "Air Squats, Ring Rows, Push-ups",
        "diet": "Balanced Tamil Meals",
        "color_class": "beginner",
        "calorie_factor": 26
    }
}


# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------

def get_db_connection():
    connection = sqlite3.connect(DB_NAME)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            age INTEGER,
            weight REAL,
            program TEXT,
            calories INTEGER,
            notes TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT,
            week TEXT,
            adherence INTEGER
        )
    """)

    connection.commit()
    connection.close()


init_db()


# ---------------------------------------------------------
# GYM INFORMATION
# ---------------------------------------------------------

GYM_INFO = {
    "capacity": 150,
    "area": "10,000 sq ft",
    "break_even": 250
}


# ---------------------------------------------------------
# HOME PAGE
# ---------------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def index():

    name = ""
    age = ""
    weight = ""
    selected_program = ""
    adherence = 0
    notes = ""

    selected_data = None
    calories = None
    message = ""
    error = ""
    summary = None

    if request.method == "POST":

        action = request.form.get("action", "")

        name = request.form.get("name", "").strip()
        age = request.form.get("age", "").strip()
        weight = request.form.get("weight", "").strip()
        selected_program = request.form.get("program", "")
        adherence = request.form.get("adherence", "0")
        notes = request.form.get("notes", "").strip()

        selected_data = PROGRAMS.get(selected_program)

        # -------------------------------------------------
        # RESET
        # -------------------------------------------------

        if action == "reset":

            return render_template(
                "index.html",
                name="",
                age="",
                weight="",
                selected_program="",
                adherence=0,
                notes="",
                selected_data=None,
                calories=None,
                message="",
                error="",
                summary=None,
                clients=get_all_clients(),
                progress_records=get_all_progress(),
                gym_info=GYM_INFO
            )

        # -------------------------------------------------
        # CALCULATE CALORIES
        # -------------------------------------------------

        if selected_data and weight:

            try:

                weight_value = float(weight)

                if weight_value > 0:

                    calories = int(
                        weight_value
                        * selected_data["calorie_factor"]
                    )

            except ValueError:

                error = "Please enter a valid weight."

        # -------------------------------------------------
        # SAVE CLIENT
        # -------------------------------------------------

        if action == "save":

            if not name or not selected_program:

                error = "Name and Program required"

            elif not error:

                try:

                    age_value = int(age) if age else 0
                    weight_value = float(weight) if weight else 0

                    connection = get_db_connection()

                    connection.execute("""
                        INSERT INTO clients
                        (name, age, weight, program, calories, notes)
                        VALUES (?, ?, ?, ?, ?, ?)

                        ON CONFLICT(name)
                        DO UPDATE SET
                            age = excluded.age,
                            weight = excluded.weight,
                            program = excluded.program,
                            calories = excluded.calories,
                            notes = excluded.notes
                    """, (
                        name,
                        age_value,
                        weight_value,
                        selected_program,
                        calories,
                        notes
                    ))

                    connection.commit()
                    connection.close()

                    message = "Client data saved successfully"

                except Exception as exc:

                    error = f"DB Error: {exc}"

        # -------------------------------------------------
        # LOAD CLIENT
        # -------------------------------------------------

        elif action == "load":

            if not name:

                error = "Please enter a client name."

            else:

                client = get_client(name)

                if client is None:

                    error = "Client not found"

                else:

                    name = client["name"]
                    age = client["age"]
                    weight = client["weight"]
                    selected_program = client["program"]
                    calories = client["calories"]
                    notes = client["notes"] or ""

                    selected_data = PROGRAMS.get(
                        selected_program
                    )

                    summary = client

        # -------------------------------------------------
        # SAVE PROGRESS
        # -------------------------------------------------

        elif action == "progress":

            if not name:

                error = "Please enter a client name."

            else:

                client = get_client(name)

                if client is None:

                    error = "Client not found. Save the client first."

                else:

                    week = datetime.now().strftime(
                        "Week %U - %Y"
                    )

                    try:

                        connection = get_db_connection()

                        connection.execute("""
                            INSERT INTO progress
                            (client_name, week, adherence)
                            VALUES (?, ?, ?)
                        """, (
                            name,
                            week,
                            int(adherence)
                        ))

                        connection.commit()
                        connection.close()

                        message = "Weekly progress logged"

                    except Exception as exc:

                        error = f"DB Error: {exc}"

        # -------------------------------------------------
        # VIEW PROGRAM
        # -------------------------------------------------

        elif action == "view":

            if not selected_program:

                error = "Please select a program."

    return render_template(
        "index.html",
        name=name,
        age=age,
        weight=weight,
        selected_program=selected_program,
        adherence=adherence,
        notes=notes,
        selected_data=selected_data,
        calories=calories,
        message=message,
        error=error,
        summary=summary,
        clients=get_all_clients(),
        progress_records=get_all_progress(),
        gym_info=GYM_INFO
    )


# ---------------------------------------------------------
# GET ALL CLIENTS
# ---------------------------------------------------------

def get_all_clients():

    connection = get_db_connection()

    clients = connection.execute("""
        SELECT *
        FROM clients
        ORDER BY id DESC
    """).fetchall()

    connection.close()

    return clients


# ---------------------------------------------------------
# GET ONE CLIENT
# ---------------------------------------------------------

def get_client(name):

    connection = get_db_connection()

    client = connection.execute("""
        SELECT *
        FROM clients
        WHERE name = ?
    """, (name,)).fetchone()

    connection.close()

    return client


# ---------------------------------------------------------
# GET PROGRESS RECORDS
# ---------------------------------------------------------

def get_all_progress():

    connection = get_db_connection()

    records = connection.execute("""
        SELECT *
        FROM progress
        ORDER BY id DESC
    """).fetchall()

    connection.close()

    return records


# ---------------------------------------------------------
# EXPORT CSV
# ---------------------------------------------------------

@app.route("/export")
def export_csv():

    clients = get_all_clients()

    if not clients:

        return (
            "No clients to export. "
            "Please save at least one client first.",
            400
        )

    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerow([
        "Name",
        "Age",
        "Weight",
        "Program",
        "Calories",
        "Notes"
    ])

    for client in clients:

        writer.writerow([
            client["name"],
            client["age"],
            client["weight"],
            client["program"],
            client["calories"],
            client["notes"]
        ])

    response = Response(
        output.getvalue(),
        mimetype="text/csv"
    )

    response.headers["Content-Disposition"] = (
        "attachment; filename=aceest_clients.csv"
    )

    return response


# ---------------------------------------------------------
# RUN APPLICATION
# ---------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)