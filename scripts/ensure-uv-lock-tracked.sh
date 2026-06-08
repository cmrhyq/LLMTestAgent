#!/usr/bin/env bash
# scripts/ensure-uv-lock-tracked.sh — local pre-commit hook helper.
# Guard against the .gitignore footgun where uv.lock would be excluded by
# an over-broad lock glob. We rely on uv.lock being committed for
# reproducible installs.
set -euo pipefail
if ! git ls-files --error-unmatch uv.lock >/dev/null 2>&1; then
    echo "ERROR: uv.lock is not tracked. Check .gitignore for an over-broad rule excluding it." >&2
    exit 1
fi
