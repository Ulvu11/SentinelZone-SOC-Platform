#!/usr/bin/env bash
# Generates docs/RELEASE_NOTES.md. Run it right before tagging:  ./scripts/release-notes.sh && git tag vX.Y.Z
set -eu
cd "$(dirname "$0")/.."
[ -f .venv/bin/activate ] && . .venv/bin/activate
VER=$(python -c "from app import __version__ as v; print(v)")
SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "uncommitted")
HEAD_REV=$(alembic heads 2>/dev/null | awk '{print $1}' | head -1)
PYV=$(python --version 2>&1)
LOCKSUM=$(sha256sum requirements.lock.txt | cut -c1-16)
OUT=docs/RELEASE_NOTES.md
{
  echo "# SentinelZone Backend v$VER"
  echo
  echo "- Git commit: \`$SHA\`"
  echo "- DB migration head: \`$HEAD_REV\`"
  echo "- Python: $PYV"
  echo "- Dependency lock: requirements.lock.txt (sha256 $LOCKSUM...)"
  echo "- Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo
  echo "## Known limitations"
  awk '/^### Known limitations/{f=1;next} /^## /{f=0} f' CHANGELOG.md
} > "$OUT"
echo "wrote $OUT"
