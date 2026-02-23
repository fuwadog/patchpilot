"""Central configuration for the AI assistant."""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

# Find the absolute path to the directory containing this file (the root)
ROOT_DIR = Path(__file__).resolve().parent
ENV_PATH = ROOT_DIR / ".env.local"

# Load the specific file
load_dotenv(dotenv_path=ENV_PATH)

class Config:
    # Provider
    BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://integrate.api.nvidia.com/v1")
    API_KEY: str = os.getenv("OPENAI_API_KEY", "") 
    MODEL: str = os.getenv("AI_MODEL", "z-ai/glm4.7")
    TEMPERATURE: float = float(os.getenv("AI_TEMPERATURE", "0.4"))

    # File loading settings
    MAX_FILES: int = int(os.getenv("MAX_FILES", "12"))
    MAX_FILE_TOKENS: int = int(os.getenv("MAX_FILE_TOKENS", "1500"))
    MAX_TOTAL_TOKENS: int = int(os.getenv("MAX_TOTAL_TOKENS", "4500"))
    MAX_CONVO_MESSAGES: int = int(os.getenv("MAX_CONVO_MESSAGES", "40"))
    MAX_RESPONSE_TOKENS: int = int(os.getenv("MAX_RESPONSE_TOKENS", "4096"))
    DEFAULT_EXTENSIONS: list[str] = ["*.ts", "*.js", "*.css", "*.tsx", "*.jsx", "*.py", "*.txt", "*.md"]

    # Safety & Retry
    ENABLE_SYNTAX_VALIDATION: bool = os.getenv("ENABLE_SYNTAX_VALIDATION", "false").lower() == "true"
    BACKUP_ON_WRITE: bool = os.getenv("BACKUP_ON_WRITE", "true").lower() == "true"
    DIFF_PREVIEW: bool = os.getenv("DIFF_PREVIEW", "true").lower() == "true"
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY: float = float(os.getenv("RETRY_DELAY", "1.5"))

    SYSTEM_PROMPT: str = (
        "You are a helpful AI assistant that can read, understand, and edit TypeScript, "
        "JavaScript, CSS and Python projects. When given a file, explain issues, propose edits, "
    )

# Quick check
if not Config.API_KEY:
    print(f"⚠️  Warning: API_KEY not found at {ENV_PATH}")