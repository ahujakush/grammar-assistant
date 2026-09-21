"""Vercel serverless entrypoint for the FastAPI backend.

vercel.json rewrites every /api/* request to this function, and the original
path is preserved, so the routes declared in backend/main.py keep working
unchanged. Vercel's Python runtime serves the exported ASGI `app` directly.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app  # noqa: E402

__all__ = ["app"]
