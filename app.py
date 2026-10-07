from flask import Flask, render_template, request, Response
import csv
import io

app = Flask(__name__)


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
# GYM INFORMATION
# ---------------------------------------------------------

GYM_INFO = {
    "capacity": 150,
    "area": "10,000 sq ft",
    "break_even": 250
}


# ---------------------------------------------------------
# CLIENT STORAGE
# ---------------------------------------------------------

clients = []


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

    if request.method == "POST":

        action = request.form.get("action", "")

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
                clients=clients,
                gym_info=GYM_INFO
            )

        # -------------------------------------------------
        # READ FORM DATA
        # -------------------------------------------------

        name = request.form.get("name", "").strip()
        age = request.form.get("age", "").strip()
        weight = request.form.get("weight", "").strip()
        selected_program = request.form.get("program", "")
        adherence = request.form.get("adherence", "0")
        notes = request.form.get("notes", "").strip()

        selected_data = PROGRAMS.get(selected_program)

        # -------------------------------------------------
        # CALCULATE ESTIMATED CALORIES
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

                error = "Please fill client name and program."

            elif not error:

                client = {
                    "name": name,
                    "age": age,
                    "weight": weight,
                    "program": selected_program,
                    "adherence": adherence,
                    "notes": notes
                }

                clients.append(client)

                message = (
                    f"Client {name} saved successfully."
                )

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
        clients=clients,
        gym_info=GYM_INFO
    )


# ---------------------------------------------------------
# EXPORT CLIENT DATA TO CSV
# ---------------------------------------------------------

@app.route("/export")
def export_csv():

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
        "Adherence",
        "Notes"
    ])

    for client in clients:

        writer.writerow([
            client["name"],
            client["age"],
            client["weight"],
            client["program"],
            client["adherence"],
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