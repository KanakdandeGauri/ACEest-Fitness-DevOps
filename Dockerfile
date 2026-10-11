FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt \
    && useradd --create-home appuser

COPY --chown=appuser:appuser app.py ./
COPY --chown=appuser:appuser templates/ ./templates/
COPY --chown=appuser:appuser tests/ ./tests/

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

CMD ["python", "-m", "flask", "--app", "app", "run", "--host=0.0.0.0", "--port=5000"]
