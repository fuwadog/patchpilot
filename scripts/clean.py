#!/usr/bin/env python3
"""Cleanup script – removes __pycache__, .coverage, caches."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DIRS_TO_REMOVE = [
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "build",
    "dist",
    "*.egg-info",
]

FILES_TO_REMOVE = [
    ".coverage",
    "coverage.xml",
]


def clean() -> None:
    for pattern in DIRS_TO_REMOVE:
        for p in ROOT.rglob(pattern):
            if p.is_dir() and not any(
                part.startswith(".") and part not in (".git",)
                for part in p.relative_to(ROOT).parts
            ):
                shutil.rmtree(p, ignore_errors=True)
                print(f"  Removed directory: {p.relative_to(ROOT)}")

    for pattern in FILES_TO_REMOVE:
        for p in ROOT.rglob(pattern):
            if p.is_file():
                p.unlink(missing_ok=True)
                print(f"  Removed file: {p.relative_to(ROOT)}")


if __name__ == "__main__":
    clean()
    print("Done.")
