"""Package this validated checkout, with content hashes and baseline change inventory."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKIP = {".git", ".venv", "venv", "__pycache__", ".pytest_cache"}
MANIFESTS = {"reports/changed-files.txt", "reports/SHA256SUMS"}


def files():
    result = []
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT)
        if set(rel.parts) & SKIP or path.suffix in {".pyc", ".pyo"}:
            continue
        if path.is_symlink():
            raise RuntimeError(f"Release must not contain symlink: {rel}")
        if not path.is_file():
            continue
        if (path.name.startswith(".env") and path.name != ".env.example") or path.suffix.lower() in {
            ".db", ".sqlite", ".sqlite3", ".key", ".pem", ".crt", ".zip", ".dump",
        }:
            raise RuntimeError(f"Runtime/secret artifact must not be packaged: {rel}")
        result.append(path)
    return result


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True, help="Original uploaded source ZIP (read-only)")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(ROOT):
        parser.error("ZIP output must be outside the source tree")
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    with zipfile.ZipFile(args.baseline) as original:
        old = {}
        for item in original.infolist():
            if item.is_dir():
                continue
            name = Path(item.filename)
            # Uploaded GitHub ZIP has one top-level repository directory.
            relative = Path(*name.parts[1:]).as_posix()
            if not set(name.parts) & SKIP:
                old[relative] = digest(original.read(item))
    current = {p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in files()
               if p.relative_to(ROOT).as_posix() not in MANIFESTS}
    changes = []
    for name in sorted(old.keys() | current.keys()):
        if name not in current:
            state = "REMOVED"
        elif name not in old:
            state = "ADDED"
        elif old[name] != current[name]:
            state = "MODIFIED"
        else:
            continue
        changes.append(f"{state:8} {name}")
    (reports / "changed-files.txt").write_text(
        "Compared with the original uploaded source ZIP; caches excluded.\n"
        "Generated changed-files.txt and SHA256SUMS are additionally new release metadata.\n\n"
        + "\n".join(changes) + "\n")
    entries = files()
    (reports / "SHA256SUMS").write_text("".join(
        f"{digest(path.read_bytes())}  {path.relative_to(ROOT).as_posix()}\n"
        for path in entries if path.name != "SHA256SUMS"))
    entries = files()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in entries:
            info = zipfile.ZipInfo("SIEM-Backend/" + path.relative_to(ROOT).as_posix(),
                                   date_time=(2026, 10, 6, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            mode = 0o755 if path.suffix == ".sh" else 0o644
            info.external_attr = (stat.S_IFREG | mode) << 16
            archive.writestr(info, path.read_bytes())
    with zipfile.ZipFile(args.output) as archive:
        assert archive.testzip() is None
        assert len(archive.infolist()) == len(entries)
    print(json.dumps({"file": str(args.output), "files": len(entries),
                      "changes": len(changes), "bytes": args.output.stat().st_size,
                      "sha256": digest(args.output.read_bytes())}, indent=2))


if __name__ == "__main__":
    main()
