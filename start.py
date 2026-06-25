#!/usr/bin/env python3
"""TPT Analyzer — Launch Script"""
import subprocess
import sys
import os
import time
import webbrowser

BASE = os.path.dirname(os.path.abspath(__file__))
procs = []


def main():
    print("=" * 50)
    print("  TPT Analyzer — Starting")
    print("=" * 50)
    print()

    # Start backend
    print("Starting Backend (port 8000)...")
    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app",
         "--host", "0.0.0.0", "--port", "8000", "--reload"],
        cwd=os.path.join(BASE, "backend")
    )
    procs.append(backend)
    time.sleep(2)

    # Start frontend
    print("Starting Frontend (port 3000)...")
    frontend = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=os.path.join(BASE, "frontend")
    )
    procs.append(frontend)
    time.sleep(3)

    # Open browser
    print()
    print("Opening browser...")
    try:
        webbrowser.open("http://localhost:3000")
    except Exception:
        pass

    print()
    print("=" * 50)
    print("  TPT Analyzer is running!")
    print()
    print("  Platform:  http://localhost:3000")
    print("  API:       http://localhost:8000")
    print("  API Docs:  http://localhost:8000/docs")
    print()
    print("  Extension: Load ./extension/ in chrome://extensions")
    print()
    print("  Press Ctrl+C to stop.")
    print("=" * 50)

    try:
        for p in procs:
            p.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        for p in procs:
            p.terminate()
        print("Stopped.")


if __name__ == "__main__":
    main()
