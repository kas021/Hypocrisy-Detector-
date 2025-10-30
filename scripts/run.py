"""Create a virtual environment, install deps, and launch the app."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    venv_dir = repo_root / ".venv"
    python_exe = _venv_python(venv_dir)

    if not python_exe.exists():
        candidates = list(venv_dir.glob("**/python*"))
        if candidates:
            python_exe = candidates[0]

    if not python_exe.exists():
        print(f"Creating virtual environment at {venv_dir}")
        subprocess.check_call([sys.executable, "-m", "venv", str(venv_dir)])
        python_exe = _venv_python(venv_dir)

    print("Upgrading pip...")
    subprocess.check_call([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"])

    requirements = repo_root / "requirements.txt"
    print(f"Installing dependencies from {requirements}")
    subprocess.check_call([str(python_exe), "-m", "pip", "install", "-r", str(requirements)])

    print("Verifying configuration paths")
    subprocess.check_call([str(python_exe), "-m", "backend.config"])

    print("Starting uvicorn on http://127.0.0.1:7860")
    subprocess.check_call(
        [
            str(python_exe),
            "-m",
            "uvicorn",
            "frontend.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            "7860",
        ]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
