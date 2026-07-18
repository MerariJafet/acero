# Clean-room reproduction container for the transit robustness analysis.
# Fully isolated: fresh OS, fresh Python, fresh cache, downloads its own data.
# No access to the ACERO DB, World Model, secrets, or the parent repo's caches.
#
#   docker build -f docker/transit_cleanroom/Dockerfile -t acero-transit-cleanroom .
#   docker run --rm acero-transit-cleanroom
#
FROM python:3.12-slim

RUN pip install --no-cache-dir numpy scipy astropy

WORKDIR /cleanroom
# only the analysis code is copied — no DB, no secrets, no world model
COPY src/acero/studies/transit /cleanroom/transit
COPY docker/transit_cleanroom/run.py /cleanroom/run.py

# make the transit package importable as a top-level module
ENV PYTHONPATH=/cleanroom
CMD ["python", "/cleanroom/run.py"]
