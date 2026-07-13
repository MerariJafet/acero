# Minimal, hardened image for ACERO's Docker sandbox backend.
# Includes numpy so computational experiments (e.g. the Sprint-4 pilot) run under
# strong isolation (--network=none --read-only). Kept intentionally small.
FROM python:3.12-slim

# numpy is the only scientific dependency the pilot needs. Add scipy/pandas here
# if later experiments require them.
RUN pip install --no-cache-dir "numpy>=1.26,<3" \
    && useradd --create-home --uid 10001 aceronaut \
    && python -c "import numpy; print('numpy', numpy.__version__)"

# The container runs experiment code as a non-root user with no network and a
# read-only root filesystem; the run workspace is bind-mounted read-write.
USER aceronaut
WORKDIR /work
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/tmp

# No ENTRYPOINT: the runner supplies `python -I code/script.py` explicitly.
