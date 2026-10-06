#!/usr/bin/env bash
# ONLY an empty, disposable *_test database. Explicit acknowledgement is mandatory.
set -euo pipefail
cd "$(dirname "$0")/.."
exec "${PYTHON:-python3}" scripts/acceptance.py --postgres "$@"
