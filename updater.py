import argparse
import ctypes
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath

def wait_for_process(pid):
    if os.name != "nt":
        return
    SYNCHRONIZE = 0x00100000
    handle = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
    if handle:
        try:
            ctypes.windll.kernel32.WaitForSingleObject(handle, 30000)
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    else:
        time.sleep(2)

def safe_target(root, relative):
    rel = PurePosixPath(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("Unsafe update path")
    target = (root / Path(*rel.parts)).resolve()
    if root.resolve() not in target.parents and target != root.resolve():
        raise ValueError("Update path escapes application folder")
    return target

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--app-dir", required=True)
    parser.add_argument("--package", required=True)
    args = parser.parse_args()
    app_dir = Path(args.app_dir).resolve()
    package = Path(args.package).resolve()
    wait_for_process(args.pid)

    work = Path(tempfile.mkdtemp(prefix="pdfsplitter-update-"))
    extracted = work / "package"
    backup = work / "backup"
    extracted.mkdir()
    backup.mkdir()
    changed = []
    deleted = []
    try:
        with zipfile.ZipFile(package, "r") as archive:
            names = archive.namelist()
            if "update_manifest.json" not in names:
                raise ValueError("Update manifest is missing")
            manifest = json.loads(archive.read("update_manifest.json").decode("utf-8"))
            changed = manifest.get("files", [])
            deleted = manifest.get("deleted", [])
            allowed = set(changed) | set(deleted) | {"update_manifest.json"}
            if not set(names).issubset(allowed):
                raise ValueError("Unexpected file in update package")
            for name in changed:
                target = safe_target(extracted, name)
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(name) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)

        touched = set(changed) | set(deleted)
        for relative in touched:
            current = safe_target(app_dir, relative)
            if current.exists() and current.is_file():
                saved = safe_target(backup, relative)
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(current, saved)

        for relative in deleted:
            target = safe_target(app_dir, relative)
            if target.exists() and target.is_file():
                target.unlink()

        for relative in changed:
            source = safe_target(extracted, relative)
            target = safe_target(app_dir, relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

        exe = app_dir / "PDF Splitter.exe"
        if not exe.exists():
            raise FileNotFoundError("PDF Splitter.exe is missing after update")
        subprocess.Popen([str(exe)], cwd=str(app_dir))
        try:
            package.unlink()
        except OSError:
            pass
    except Exception as exc:
        for relative in changed:
            target = safe_target(app_dir, relative)
            saved = safe_target(backup, relative)
            if saved.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(saved, target)
            elif target.exists() and target.is_file():
                target.unlink()
        for relative in deleted:
            saved = safe_target(backup, relative)
            if saved.exists():
                target = safe_target(app_dir, relative)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(saved, target)
        try:
            subprocess.Popen([str(app_dir / "PDF Splitter.exe")], cwd=str(app_dir))
        except Exception:
            pass
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)

if __name__ == "__main__":
    main()
