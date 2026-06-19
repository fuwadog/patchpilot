"""Central configuration for PatchPilot.

Reads from .env.local in the project root directory.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# Project root is two levels up from this file: src/config.py -> src/ -> project root
ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env.local"

# Load the specific file
load_dotenv(dotenv_path=ENV_PATH)


class Config:
    # Provider
    BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://integrate.api.nvidia.com/v1")
    API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    MODEL: str = os.getenv("AI_MODEL", "z-ai/glm4.7")

    try:
        TEMPERATURE: float = float(os.getenv("AI_TEMPERATURE", "0.4"))
    except (ValueError, TypeError):
        TEMPERATURE: float = 0.4

    # File loading settings
    try:
        MAX_FILES: int = int(os.getenv("MAX_FILES", "12"))
    except (ValueError, TypeError):
        MAX_FILES: int = 12

    try:
        MAX_FILE_TOKENS: int = int(os.getenv("MAX_FILE_TOKENS", "1500"))
    except (ValueError, TypeError):
        MAX_FILE_TOKENS: int = 1500

    try:
        MAX_TOTAL_TOKENS: int = int(os.getenv("MAX_TOTAL_TOKENS", "4500"))
    except (ValueError, TypeError):
        MAX_TOTAL_TOKENS: int = 4500

    try:
        MAX_CONVO_MESSAGES: int = int(os.getenv("MAX_CONVO_MESSAGES", "40"))
    except (ValueError, TypeError):
        MAX_CONVO_MESSAGES: int = 40

    try:
        MAX_RESPONSE_TOKENS: int = int(os.getenv("MAX_RESPONSE_TOKENS", "4096"))
    except (ValueError, TypeError):
        MAX_RESPONSE_TOKENS: int = 4096

    DEFAULT_EXTENSIONS: list[str] = [
        "*.ts",
        "*.js",
        "*.css",
        "*.tsx",
        "*.jsx",
        "*.py",
        "*.txt",
        "*.md",
    ]

    # Safety & Retry
    ENABLE_SYNTAX_VALIDATION: bool = (
        os.getenv("ENABLE_SYNTAX_VALIDATION", "false").lower() == "true"
    )
    BACKUP_ON_WRITE: bool = os.getenv("BACKUP_ON_WRITE", "true").lower() == "true"
    DIFF_PREVIEW: bool = os.getenv("DIFF_PREVIEW", "true").lower() == "true"

    try:
        MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    except (ValueError, TypeError):
        MAX_RETRIES: int = 3

    try:
        RETRY_DELAY: float = float(os.getenv("RETRY_DELAY", "1.5"))
    except (ValueError, TypeError):
        RETRY_DELAY: float = 1.5

    SYSTEM_PROMPT: str = (
        "You are a helpful AI assistant that can read, understand, and edit "
        "TypeScript, JavaScript, CSS and Python projects. When given a file, "
        "explain issues, propose edits, "
    )

    # Database
    DB_PATH: str = os.getenv(
        "PATCHPILOT_DB_PATH",
        str(Path.home() / ".patchpilot" / "sessions.db"),
    )


logger = logging.getLogger(__name__)

if not Config.API_KEY:
    logger.warning("API_KEY not found at %s", ENV_PATH)
