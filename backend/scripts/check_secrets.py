"""Portable heuristic scan for source ZIPs and git checkouts. Does not print secret values."""
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
PATTERN=re.compile(r"ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|xox[bp]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|[0-9]{8,10}:AA[A-Za-z0-9_-]{30,}")
EXCLUDED={".git",".venv","venv","__pycache__",".pytest_cache"}
hits=[]
for p in sorted(ROOT.rglob('*')):
    if not p.is_file() or EXCLUDED.intersection(p.relative_to(ROOT).parts):continue
    if p.name=='.env' or p.suffix.lower() in {'.db','.pem','.key','.crt','.sqlite','.sqlite3'}:
        hits.append(str(p.relative_to(ROOT)));continue
    try:content=p.read_text(encoding='utf-8')
    except (UnicodeError,OSError):continue
    if PATTERN.search(content):hits.append(str(p.relative_to(ROOT)))
if hits:
    print('Potential secrets/private runtime artifacts found in:',*hits,sep='\n')
    sys.exit(1)
print('Portable heuristic secret scan passed (not a replacement for a full secret-scanner).')
