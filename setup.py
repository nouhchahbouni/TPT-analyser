#!/usr/bin/env python3
"""TPT Analyzer — Auto Setup Script"""
import subprocess
import sys
import os


def run(cmd, **kw):
    print(f"  → {cmd}")
    subprocess.run(cmd, shell=True, check=True, **kw)


def main():
    print("=" * 50)
    print("  TPT Analyzer — Setup")
    print("=" * 50)
    print()

    # Python dependencies
    print("[1/3] Installing Python dependencies...")
    run(f"{sys.executable} -m pip install fastapi uvicorn playwright aiohttp aiosqlite openpyxl pydantic python-multipart")

    print()
    print("[2/3] Installing Playwright browser (Chromium)...")
    try:
        run("playwright install chromium")
    except subprocess.CalledProcessError:
        print("  Warning: Playwright browser install failed. Scraping will use mock data.")

    # Node dependencies
    print()
    print("[3/3] Installing Node.js frontend dependencies...")
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    run("npm install", cwd=frontend_dir)

    print()
    print("=" * 50)
    print("  Setup complete!")
    print("  Run: python start.py")
    print("=" * 50)


if __name__ == "__main__":
    main()
