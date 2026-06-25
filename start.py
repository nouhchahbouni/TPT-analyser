#!/usr/bin/env python3
"""
TPT Analyzer — Launch Script
Run: python start.py
"""
import subprocess
import sys
import os
import time
import webbrowser
import signal

BASE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(BASE, 'backend')
FRONTEND = os.path.join(BASE, 'frontend')

procs = []

def stop(sig=None, frame=None):
    print("\n\n🛑 Shutting down TPT Analyzer...")
    for p in procs:
        try: p.terminate()
        except: pass
    sys.exit(0)

signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)

print("=" * 50)
print("  🚀 TPT Analyzer — Starting")
print("=" * 50)
print()

# Start backend
print("⚙️  Starting backend API (port 8000)...")
backend_proc = subprocess.Popen(
    [sys.executable, '-m', 'uvicorn', 'main:app',
     '--host', '0.0.0.0', '--port', '8000', '--reload'],
    cwd=BACKEND
)
procs.append(backend_proc)
time.sleep(2)

# Start frontend
print("⚛️  Starting React frontend (port 3000)...")
npm_cmd = 'npm.cmd' if sys.platform == 'win32' else 'npm'
frontend_proc = subprocess.Popen(
    [npm_cmd, 'run', 'dev'],
    cwd=FRONTEND
)
procs.append(frontend_proc)
time.sleep(3)

# Open browser
print()
print("=" * 50)
print("  ✅ TPT Analyzer is running!")
print("=" * 50)
print()
print("  🌐 Platform:  http://localhost:3000")
print("  🔌 API:       http://localhost:8000")
print("  📚 API Docs:  http://localhost:8000/docs")
print()
print("  Chrome Extension:")
print("  → Open chrome://extensions")
print("  → Enable 'Developer mode'")
print("  → Click 'Load unpacked'")
print(f"  → Select: {os.path.join(BASE, 'extension')}")
print()
print("  Press Ctrl+C to stop.")
print()

try:
    webbrowser.open('http://localhost:3000')
except:
    pass

try:
    for p in procs:
        p.wait()
except KeyboardInterrupt:
    stop()
