#!/usr/bin/env bash
# Compatibility wrapper with the full disposable-DB guards.
set -euo pipefail
exec bash "$(dirname "$0")/postgres-acceptance.sh" "$@"
