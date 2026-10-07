import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app as app_module


@pytest.fixture
def test_app():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    original_db_name = app_module.DB_NAME
    app_module.DB_NAME = db_path

    app_module.init_db()

    app_module.app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret-key",
    )

    yield app_module.app

    app_module.DB_NAME = original_db_name

    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def client(test_app):
    return test_app.test_client()


@pytest.fixture
def logged_in_client(client):
    response = client.post(
        "/login",
        data={
            "username": "admin",
            "password": "admin",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    return client


def test_login_page(client):
    response = client.get("/login")

    assert response.status_code == 200
    assert b"ACEest Fitness" in response.data
    assert b"Username" in response.data
    assert b"Password" in response.data


def test_successful_login(client):
    response = client.post(
        "/login",
        data={
            "username": "admin",
            "password": "admin",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"ACEest Fitness" in response.data


def test_failed_login(client):
    response = client.post(
        "/login",
        data={
            "username": "admin",
            "password": "wrong-password",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Invalid credentials." in response.data


def test_dashboard_requires_login(client):
    response = client.get("/")

    assert response.status_code == 302
    assert "/login" in response.location


def test_logout(logged_in_client):
    response = logged_in_client.get(
        "/logout",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"ACEest Fitness" in response.data


def test_calculate_calories(test_app):
    with test_app.app_context():
        assert app_module.calculate_calories(60, "Fat Loss") == 1320
        assert app_module.calculate_calories(60, "Muscle Gain") == 2100
        assert app_module.calculate_calories(60, "Beginner") == 1560


def test_bmi_calculation(test_app):
    with test_app.app_context():
        bmi, category = app_module.bmi_info(175, 70)

        assert bmi == 22.9
        assert category == "Normal"


def test_save_client(logged_in_client):
    response = logged_in_client.post(
        "/",
        data={
            "action": "save_client",
            "name": "Test Client",
            "age": "25",
            "height": "175",
            "weight": "70",
            "program": "Fat Loss",
            "membership_end": "2026-12-31",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Test Client" in response.data


def test_select_client(logged_in_client):
    logged_in_client.post(
        "/",
        data={
            "action": "save_client",
            "name": "Selected Client",
            "age": "30",
            "height": "180",
            "weight": "80",
            "program": "Muscle Gain",
            "membership_end": "2026-12-31",
        },
        follow_redirects=True,
    )

    response = logged_in_client.post(
        "/",
        data={
            "action": "select_client",
            "client_name": "Selected Client",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Selected Client" in response.data


def test_generate_ai_program(logged_in_client):
    logged_in_client.post(
        "/",
        data={
            "action": "save_client",
            "name": "AI Test Client",
            "age": "25",
            "height": "175",
            "weight": "70",
            "program": "Fat Loss",
            "membership_end": "2026-12-31",
        },
        follow_redirects=True,
    )

    response = logged_in_client.post(
        "/",
        data={
            "action": "generate_program",
            "client_name": "AI Test Client",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"AI Test Client" in response.data


def test_add_progress(logged_in_client):
    logged_in_client.post(
        "/",
        data={
            "action": "save_client",
            "name": "Progress Client",
            "age": "25",
            "height": "175",
            "weight": "70",
            "program": "Fat Loss",
            "membership_end": "2026-12-31",
        },
        follow_redirects=True,
    )

    response = logged_in_client.post(
        "/",
        data={
            "action": "add_progress",
            "client_name": "Progress Client",
            "week": "Week 40 - 2026",
            "adherence": "85",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200


def test_add_workout(logged_in_client):
    logged_in_client.post(
        "/",
        data={
            "action": "save_client",
            "name": "Workout Client",
            "age": "25",
            "height": "175",
            "weight": "70",
            "program": "Muscle Gain",
            "membership_end": "2026-12-31",
        },
        follow_redirects=True,
    )

    response = logged_in_client.post(
        "/",
        data={
            "action": "add_workout",
            "client_name": "Workout Client",
            "date": "2026-10-08",
            "workout_type": "Strength",
            "duration": "60",
            "notes": "Test workout",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200


def test_add_body_metric(logged_in_client):
    logged_in_client.post(
        "/",
        data={
            "action": "save_client",
            "name": "Metric Client",
            "age": "25",
            "height": "175",
            "weight": "70",
            "program": "Fat Loss",
            "membership_end": "2026-12-31",
        },
        follow_redirects=True,
    )

    response = logged_in_client.post(
        "/",
        data={
            "action": "add_metric",
            "client_name": "Metric Client",
            "date": "2026-10-08",
            "weight": "69",
            "waist": "80",
            "bodyfat": "18",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200