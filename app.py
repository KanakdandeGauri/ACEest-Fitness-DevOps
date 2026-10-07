from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "aceest-fitness-secret-key"

DB_NAME = "aceest_fitness.db"

PROGRAMS = {
    "Fat Loss (FL)": {
        "factor": 22,
        "description": "Structured fat-loss training with calorie-controlled nutrition.",
    },
    "Muscle Gain (MG)": {
        "factor": 35,
        "description": "Strength-focused training with higher calorie intake.",
    },
    "Beginner (BG)": {
        "factor": 26,
        "description": "Beginner-friendly fitness program for building consistency.",
    },
}


# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            age INTEGER,
            weight REAL,
            program TEXT,
            calories INTEGER
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT,
            week TEXT,
            adherence INTEGER
        )
    """)

    conn.commit()
    conn.close()


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def calculate_calories(weight, program):
    factor = PROGRAMS[program]["factor"]
    return int(float(weight) * factor)


def get_client(name):
    conn = get_db_connection()

    client = conn.execute(
        "SELECT * FROM clients WHERE name = ?",
        (name,)
    ).fetchone()

    conn.close()
    return client


def get_all_clients():
    conn = get_db_connection()

    clients = conn.execute(
        "SELECT * FROM clients ORDER BY id DESC"
    ).fetchall()

    conn.close()
    return clients


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


# ---------------------------------------------------------
# MAIN PAGE
# ---------------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def index():

    form_data = {
        "name": "",
        "age": "",
        "weight": "",
        "program": "",
        "adherence": 0
    }

    selected_client = None
    summary = None

    if request.method == "POST":

        action = request.form.get("action")

        # ---------------------------------------------
        # SAVE CLIENT
        # ---------------------------------------------

        if action == "save":

            name = request.form.get("name", "").strip()
            age = request.form.get("age", "").strip()
            weight = request.form.get("weight", "").strip()
            program = request.form.get("program", "").strip()
            adherence = request.form.get("adherence", "0")

            form_data.update({
                "name": name,
                "age": age,
                "weight": weight,
                "program": program,
                "adherence": adherence
            })

            if not name or not program:
                flash("Name and Program are required.", "error")

            elif program not in PROGRAMS:
                flash("Please select a valid program.", "error")

            else:
                try:
                    age_value = int(age)
                    weight_value = float(weight)
                    calories = calculate_calories(weight_value, program)

                    conn = get_db_connection()

                    conn.execute(
                        """
                        INSERT OR REPLACE INTO clients
                        (name, age, weight, program, calories)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            name,
                            age_value,
                            weight_value,
                            program,
                            calories
                        )
                    )

                    conn.commit()
                    conn.close()

                    flash("Client data saved successfully.", "success")

                    selected_client = get_client(name)

                except ValueError:
                    flash(
                        "Age must be an integer and Weight must be a number.",
                        "error"
                    )

        # ---------------------------------------------
        # LOAD CLIENT
        # ---------------------------------------------

        elif action == "load":

            name = request.form.get("name", "").strip()

            form_data["name"] = name

            if not name:
                flash("Enter a client name to load.", "error")

            else:
                client = get_client(name)

                if client is None:
                    flash("Client not found.", "error")

                else:
                    selected_client = client

                    form_data.update({
                        "name": client["name"],
                        "age": client["age"],
                        "weight": client["weight"],
                        "program": client["program"],
                        "adherence": 0
                    })

        # ---------------------------------------------
        # SAVE PROGRESS
        # ---------------------------------------------

        elif action == "progress":

            name = request.form.get("name", "").strip()
            adherence = request.form.get("adherence", "0")

            form_data.update({
                "name": name,
                "adherence": adherence
            })

            if not name:
                flash("Enter a client name before saving progress.", "error")

            else:
                client = get_client(name)

                if client is None:
                    flash(
                        "Client not found. Save the client first.",
                        "error"
                    )

                else:
                    try:
                        adherence_value = int(float(adherence))

                        if not 0 <= adherence_value <= 100:
                            raise ValueError

                        week = datetime.now().strftime(
                            "Week %U - %Y"
                        )

                        conn = get_db_connection()

                        conn.execute(
                            """
                            INSERT INTO progress
                            (client_name, week, adherence)
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

                        flash(
                            "Weekly progress logged successfully.",
                            "success"
                        )

                        selected_client = get_client(name)

                    except ValueError:
                        flash(
                            "Adherence must be between 0 and 100.",
                            "error"
                        )

        # ---------------------------------------------
        # VIEW PROGRAM
        # ---------------------------------------------

        elif action == "view":

            name = request.form.get("name", "").strip()
            age = request.form.get("age", "").strip()
            weight = request.form.get("weight", "").strip()
            program = request.form.get("program", "").strip()
            adherence = request.form.get("adherence", "0")

            form_data.update({
                "name": name,
                "age": age,
                "weight": weight,
                "program": program,
                "adherence": adherence
            })

            if program not in PROGRAMS:
                flash("Please select a program.", "error")

            else:
                try:
                    if weight:
                        calories = calculate_calories(
                            float(weight),
                            program
                        )
                    else:
                        calories = None

                    summary = {
                        "name": name,
                        "age": age,
                        "weight": weight,
                        "program": program,
                        "calories": calories
                    }

                except ValueError:
                    flash("Weight must be a number.", "error")

        # ---------------------------------------------
        # RESET
        # ---------------------------------------------

        elif action == "reset":

            return redirect(url_for("index"))

    clients = get_all_clients()
    progress = get_all_progress()

    return render_template(
        "index.html",
        programs=PROGRAMS,
        form_data=form_data,
        selected_client=selected_client,
        summary=summary,
        clients=clients,
        progress=progress
    )


# ---------------------------------------------------------
# APPLICATION START
# ---------------------------------------------------------

if __name__ == "__main__":
    init_db()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )