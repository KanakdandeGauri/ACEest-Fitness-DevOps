from flask import Flask, render_template, request

app = Flask(__name__)


PROGRAMS = {
    "Fat Loss (FL)": {
        "workout": (
            "Mon: Back Squat 5x5 + Core\n"
            "Tue: EMOM 20min Assault Bike\n"
            "Wed: Bench Press + 21-15-9\n"
            "Thu: Deadlift + Box Jumps\n"
            "Fri: Zone 2 Cardio 30min"
        ),
        "diet": (
            "Breakfast: Egg Whites + Oats\n"
            "Lunch: Grilled Chicken + Brown Rice\n"
            "Dinner: Fish Curry + Millet Roti\n"
            "Target: ~2000 kcal"
        ),
        "color": "#e74c3c",
        "calorie_factor": 22
    },
    "Muscle Gain (MG)": {
        "workout": (
            "Mon: Squat 5x5\n"
            "Tue: Bench 5x5\n"
            "Wed: Deadlift 4x6\n"
            "Thu: Front Squat 4x8\n"
            "Fri: Incline Press 4x10\n"
            "Sat: Barbell Rows 4x10"
        ),
        "diet": (
            "Breakfast: Eggs + Peanut Butter Oats\n"
            "Lunch: Chicken Biryani\n"
            "Dinner: Mutton Curry + Rice\n"
            "Target: ~3200 kcal"
        ),
        "color": "#2ecc71",
        "calorie_factor": 35
    },
    "Beginner (BG)": {
        "workout": (
            "Full Body Circuit:\n"
            "- Air Squats\n"
            "- Ring Rows\n"
            "- Push-ups\n"
            "Focus: Technique & Consistency"
        ),
        "diet": (
            "Balanced Tamil Meals\n"
            "Idli / Dosa / Rice + Dal\n"
            "Protein Target: 120g/day"
        ),
        "color": "#3498db",
        "calorie_factor": 26
    }
}


# Gym information from v1.0
GYM_INFO = {
    "capacity": 150,
    "area": "10,000 sq ft",
    "break_even": 250
}


@app.route("/", methods=["GET", "POST"])
def index():
    name = ""
    age = ""
    weight = ""
    adherence = 0
    selected_program = ""
    selected_data = None
    calories = None
    message = ""
    error = ""

    if request.method == "POST":
        action = request.form.get("action", "")

        if action == "reset":
            return render_template(
                "index.html",
                name="",
                age="",
                weight="",
                adherence=0,
                selected_program="",
                selected_data=None,
                calories=None,
                message="",
                error="",
                gym_info=GYM_INFO
            )

        name = request.form.get("name", "").strip()
        age = request.form.get("age", "").strip()
        weight = request.form.get("weight", "").strip()
        selected_program = request.form.get("program", "")
        adherence = request.form.get("adherence", "0")

        selected_data = PROGRAMS.get(selected_program)

        # Calculate estimated calories when a valid weight
        # and program are provided.
        if selected_data and weight:
            try:
                weight_value = float(weight)

                if weight_value > 0:
                    calories = int(
                        weight_value * selected_data["calorie_factor"]
                    )

            except ValueError:
                error = "Please enter a valid weight."

        if action == "save":
            if not name or not selected_program:
                error = "Please fill client name and program."
            else:
                message = (
                    f"Client {name} saved successfully. "
                    f"Adherence: {adherence}%"
                )

    return render_template(
        "index.html",
        name=name,
        age=age,
        weight=weight,
        adherence=adherence,
        selected_program=selected_program,
        selected_data=selected_data,
        calories=calories,
        message=message,
        error=error,
        gym_info=GYM_INFO
    )


if __name__ == "__main__":
    app.run(debug=True)