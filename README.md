# ACEest Fitness & Gym — DevOps Assignment

## Overview

ACEest Fitness & Gym is a Flask-based fitness application developed for the Introduction to DevOps assignment. This project demonstrates version control, automated testing, Docker containerization, and Continuous Integration (CI) using GitHub Actions and Jenkins.

## Objectives

- Manage application versions using Git and GitHub.
- Develop and run the application using Flask.
- Validate functionality using Pytest.
- Package the application in a Docker image.
- Automate syntax checks, tests, and Docker builds using GitHub Actions.
- Build and test the GitHub-hosted project using Jenkins.

## Technology Stack

- Python 3.9
- Flask
- Pytest
- Docker
- Git and GitHub
- GitHub Actions
- Jenkins

## Repository

GitHub: https://github.com/KanakdandeGauri/ACEest-Fitness-DevOps

## Project Structure

```text
ACEest-Fitness-DevOps/
├── app.py
├── requirements.txt
├── Dockerfile
├── .dockerignore
├── README.md
├── templates/
├── tests/
│   └── test_app.py
└── .github/
    └── workflows/
        └── main.yml
```

## Local Setup

Clone the repository:

```bash
git clone https://github.com/KanakdandeGauri/ACEest-Fitness-DevOps.git
cd ACEest-Fitness-DevOps
```

Create and activate a virtual environment on Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install the dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run the Application

Start Flask:

```bash
python app.py
```

Open the application at:

http://localhost:5000/login

Stop the server with `Ctrl+C`.

## Automated Testing

Run the test suite:

```bash
python -m pytest -v
```

Check Python syntax:

```bash
python -m py_compile app.py tests/test_app.py
```

The project test suite contains 13 tests covering login, access control, calculations, client records, workout and progress operations, and related application functionality.

## Docker

Build the Docker image:

```bash
docker build -t aceest-fitness:latest .
```

Run the container:

```bash
docker run -d --name aceest-fitness -p 5000:5000 aceest-fitness:latest
```

Open the application at:

http://localhost:5000/login

Check running containers:

```bash
docker ps
```

View container logs:

```bash
docker logs aceest-fitness
```

Stop and remove the container when required:

```bash
docker stop aceest-fitness
docker rm aceest-fitness
```

Run the test suite inside the Docker image:

```bash
docker run --rm --entrypoint python aceest-fitness:latest -m pytest -v
```

## GitHub Actions CI

The workflow is located at `.github/workflows/main.yml` and is configured to run on pushes and pull requests.

The workflow performs these steps:

1. Checks out the repository.
2. Sets up Python.
3. Installs project dependencies.
4. Checks Python syntax.
5. Runs Pytest.
6. Builds the Docker image.
7. Runs Pytest inside the Docker image.

The successful GitHub Actions run is included in the assignment evidence.

## Jenkins CI

A Jenkins Pipeline job named `ACEest-Fitness-CI` is configured to pull the `main` branch from GitHub.

The pipeline stages are:

1. Checkout GitHub.
2. Build Docker image.
3. Check Python syntax.
4. Run Pytest inside Docker.

The Jenkins build and test execution were verified successfully. Screenshots are included in the assignment evidence.

## Version Control

Git was used to maintain incremental development history and version tags throughout the project.

To inspect the commit history and tags:

```bash
git log --oneline --decorate --all
git tag
```

## Conclusion

This project demonstrates a basic DevOps workflow for a Flask application, integrating source control, automated testing, Docker containerization, and CI pipelines in GitHub Actions and Jenkins.
