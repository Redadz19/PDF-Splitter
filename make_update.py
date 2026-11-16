import hashlib
import json
import sys
import zipfile
from pathlib import Path

current = Path(sys.argv[1]).resolve()
previous = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else None
out = Path(sys.argv[3]).resolve()
out.mkdir(parents=True, exist_ok=True)

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

current_files = {
    p.relative_to(current).as_posix(): p
    for p in current.rglob("*") if p.is_file()
}
previous_files = {}
if previous and previous.exists():
    previous_files = {
        p.relative_to(previous).as_posix(): p
        for p in previous.rglob("*") if p.is_file()
    }

changed = [
    name for name, path in current_files.items()
    if name not in previous_files or digest(path) != digest(previous_files[name])
]
deleted = sorted(set(previous_files) - set(current_files))
manifest = {"files": sorted(changed), "deleted": deleted, "sha256": {name: digest(current_files[name]) for name in changed}}

with zipfile.ZipFile(out / "PDF-Splitter-Full.zip", "w", zipfile.ZIP_DEFLATED, compresslevel=6) as full:
    for name, path in current_files.items():
        full.write(path, name)

with zipfile.ZipFile(out / "PDF-Splitter-Update.zip", "w", zipfile.ZIP_DEFLATED, compresslevel=6) as patch:
    patch.writestr("update_manifest.json", json.dumps(manifest, ensure_ascii=False))
    for name in changed:
        patch.write(current_files[name], name)

print(json.dumps({"changed_files": len(changed), "deleted_files": len(deleted), "full_files": len(current_files)}))
