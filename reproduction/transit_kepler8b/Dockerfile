# Fully isolated reproduction container. Downloads its own public data.
# No ACERO DB, World Model, secrets, or caches are present.
FROM python:3.12-slim
WORKDIR /repro
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . /repro
CMD ["python", "run_all.py"]
