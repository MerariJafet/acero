#!/usr/bin/env bash
# Build the ACERO sandbox image. Reproducible; run once, then the Docker backend
# is available. Requires network for the pip install layer.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${ACERO_SANDBOX_IMAGE:-acero-sandbox:py312}"
echo "Building $IMAGE ..."
docker build -t "$IMAGE" "$HERE"
echo "Done: $IMAGE"
