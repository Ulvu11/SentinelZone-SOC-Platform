#!/usr/bin/env bash
# Isolated development acceptance; never migrates a configured production DB.
set -euo pipefail
cd "$(dirname "$0")/.."
exec "${PYTHON:-python3}" scripts/acceptance.py "$@"
