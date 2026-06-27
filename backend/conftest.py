"""Shared pytest fixtures. Keeps the test suite runnable fully offline."""

import os

os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("UPLOAD_DIR", "/tmp/kb-test-uploads")
