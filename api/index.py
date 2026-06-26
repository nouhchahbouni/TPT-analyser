"""Vercel serverless entry point for TPT Analyzer FastAPI backend."""
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from dotenv import load_dotenv
load_dotenv()

from main import app
