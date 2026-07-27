# Agentic-authoring image for ACERO's experiment role.
#
# Unlike acero-sandbox:py312 (which runs SCORED experiment code with
# --network=none), this image hosts the *agent itself* (Claude Code CLI) while
# it AUTHORS and debugs an analysis script. It therefore needs Node + the claude
# binary, and it runs WITH network (the agent must reach the Anthropic API).
#
# Safety is layered elsewhere, not here:
#   * The agent's tools are confined to /work by --add-dir and the container.
#   * Data is bind-mounted read-only; credentials read-only.
#   * The SCORED, integrity-clean result comes from a SEPARATE --network=none
#     run of the agent's final script in acero-sandbox:py312, and ACERO
#     cross-checks that the agent's claimed RESULT_JSON reproduces there.
FROM python:3.12-slim

# Scientific stack the analysis scripts commonly need. Kept in sync with the
# scored sandbox image so a script that runs here also runs there.
RUN pip install --no-cache-dir "numpy>=1.26,<3" "pandas>=2,<3" "scipy>=1.11,<2"

# Node + Claude Code CLI. curl/ca-certificates are needed for the install and
# for the CLI's own HTTPS calls to the API at runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @anthropic-ai/claude-code \
    && apt-get purge -y --auto-remove \
    && rm -rf /var/lib/apt/lists/* \
    && claude --version

# Non-root user that can write the bind-mounted /work. HOME is set at runtime to
# a writable path where credentials are mounted.
RUN useradd --create-home --uid 10001 aceronaut
USER aceronaut
WORKDIR /work
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# No ENTRYPOINT: the AgenticExperimentRunner supplies the `claude -p ...` command.
