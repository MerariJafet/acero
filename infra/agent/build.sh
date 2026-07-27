#!/usr/bin/env bash
# Build the ACERO agentic-authoring image (Node + Claude Code CLI + sci stack).
# Requires network. Run once; then the agentic experiment role is available.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${ACERO_AGENT_IMAGE:-acero-agent:py312}"
echo "Building $IMAGE ..."
docker build -t "$IMAGE" "$HERE"
echo "Done: $IMAGE"
