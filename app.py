from flask import Flask, render_template, request

app = Flask(__name__)

# Data Store for Program Specification
programs = {
    "Fat Loss (FL)": {
        "workout": """Mon: 5x5 Back Squat + AMRAP
Tue: EMOM 20min Assault Bike
Wed: Bench Press + 21-15-9
Thu: 10RFT Deadlifts/Box Jumps
Fri: 30min Active Recovery""",
        "diet": """B: 3 Egg Whites + Oats Idli
L: Grilled Chicken + Brown Rice
D: Fish Curry + Millet Roti
Target: 2,000 kcal""",
        "color": "#e74c3c"
    },
    "Muscle Gain (MG)": {
        "workout": """Mon: Squat 5x5
Tue: Bench 5x5
Wed: Deadlift 4x6
Thu: Front Squat 4x8
Fri: Incline Press 4x10
Sat: Barbell Rows 4x10""",
        "diet": """B: 4 Eggs + PB Oats
L: Chicken Biryani (250g Chicken)
D: Mutton Curry + Jeera Rice
Target: 3,200 kcal""",
        "color": "#2ecc71"
    },
    "Beginner (BG)": {
        "workout": """Circuit Training: Air Squats, Ring Rows, Push-ups.
Focus: Technique Mastery & Form (90% Threshold)""",
        "diet": """Balanced Tamil Meals: Idli-Sambar, Rice-Dal, Chapati.
Protein: 120g/day""",
        "color": "#3498db"
    }
}


@app.route("/", methods=["GET", "POST"])
def index():
    selected_program = None
    selected_data = None

    if request.method == "POST":
        selected_program = request.form.get("program")
        selected_data = programs.get(selected_program)

    return render_template(
        "index.html",
        programs=programs,
        selected_program=selected_program,
        selected_data=selected_data
    )


if __name__ == "__main__":
    app.run(debug=True)