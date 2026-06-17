# 🚀 PatchPilot Quickstart Guide

## 🎯 Overview
PatchPilot is a terminal-native AI orchestration engine for code refactoring and file intelligence. This guide will help you get up and running quickly on Windows.

## 📋 Prerequisites
- **Python 3.10+** (Python 3.14 recommended)
- **Git** (for cloning the repository)
- **Windows 10/11** (with PowerShell or Command Prompt)

## 🚀 Quick Start (5 Minutes)

### 1. Clone and Setup
```powershell
# Clone the repository
git clone https://github.com/fuwadog/patchpilot.git

# Navigate to the project
cd patchpilot
```

### 2. Create Virtual Environment
```powershell
# Create virtual environment
python -m venv venv

# Activate it (PowerShell)
venv\Scripts\Activate.ps1
# Or in Command Prompt:
venv\Scripts\activate.bat
```

### 3. Install Dependencies
```powershell
# Install core dependencies
pip install -r requirements.txt

# Install development tools (optional but recommended)
pip install -r requirements-dev.txt
```

### 4. Configure Environment
```powershell
# Copy the example template to .env.local (required by the app)
copy .env.example .env.local
notepad .env.local
```
Add your API key to `.env.local`:
```env
# API Configuration
API_KEY=your_api_key_here
BASE_URL=https://api.nvidia.com/v1
MODEL_NAME=nv-llama-3-70b-instruct

# Model Parameters
MAX_TOKENS=4096
TEMPERATURE=0.3

# Context Management
MAX_CONTEXT_TOKENS=8000
PINNED_FILES_LIMIT=5
```

### 5. Run PatchPilot
```powershell
# Start the application
python main.py
```

You'll see an interactive CLI with commands like:
- `/file src/app.py` - Load a single file
- `/folder src/` - Load entire directory
- `/fix` - Detect and fix bugs
- `/refactor` - Improve code structure
- `/patch` - Generate and preview edits

---

## 🐛 Development & Debugging

### Run Bug-Finding Tools
```powershell
# Install development dependencies first
pip install -r requirements-dev.txt

# Run linters
python -m ruff check . --fix

# Run type checker
python -m mypy .

# Check security vulnerabilities
python -m safety check

# Format code
python -m black .
python -m isort .
```

### Run All Checks at Once
```powershell
# Windows PowerShell
python -m ruff check . && python -m mypy . && python -m safety check && python -m black --check . && python -m isort --check .
```

### Common Issues & Fixes

**Issue**: `python -m ruff` not found  
**Fix**: Make sure venv is activated: `venv\Scripts\Activate.ps1`

**Issue**: Permission errors  
**Fix**: Run PowerShell as Administrator or use `--user` flag:
```powershell
pip install --user -r requirements.txt
```

**Issue**: Missing dependencies  
**Fix**: Reinstall: `pip install -r requirements.txt --force-reinstall`

**Issue**: Black formatting fails  
**Fix**: Install black: `pip install black`

---

## 📊 Project Structure (After Move)
```
patchpilot/
├── quickstart.md          # This file
├── bugs.md               # Bug report
├── README.md             # Project overview
├── .gitignore            # Ignored files
├── .env.local            # Environment configuration (create from .env.example)
├── requirements.txt      # Core dependencies
├── requirements-dev.txt  # Development tools
├── pyproject.toml        # Tool configurations
├── Makefile              # Build automation (for Linux/Mac)
├── venv/                 # Virtual environment (ignored)
├── main.py               # Entry point (run this!)
├── config.py             # Configuration
├── files/
│   ├── manager.py
│   ├── operations.py
│   └── __init__.py
├── context/
│   ├── manager.py
│   └── __init__.py
├── session/
│   ├── manager.py
│   └── __init__.py
├── client/
│   ├── nvidia.py
│   ├── base.py
│   └── __init__.py
└── cli/
    ├── autocomplete.py
    ├── commands.py
    ├── display.py
    └── __init__.py
```

---

## 🔧 Troubleshooting

### "Module not found" errors
Make sure you're in the project root and the virtual environment is activated.

### "Command not found" in PowerShell
Use the `python -m` form or full path: `venv\Scripts\ruff.exe`

### Black/formatting issues
Run `black .` to auto-format, then `isort .` to sort imports.

### Type checking errors
Install missing stubs: `pip install types-openpyxl types-pandas`

### Security vulnerability warning
Upgrade affected packages: `pip install --upgrade pypdf`

---

## 🤝 Contributing
1. Fork the repository
2. Create a feature branch
3. Commit changes with proper formatting
4. Run `make ci` (Linux/Mac) or the full check commands above
5. Open a Pull Request

**Remember to run all checks before submitting contributions!**

---

## 📋 Development Setup
```powershell
# 1. Clone and setup virtual environment
git clone https://github.com/fuwadog/patchpilot.git
cd patchpilot
python -m venv venv
venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 3. Start coding!
python main.py
```

---

*Last updated: 2026-04-12*  
*For questions, open an issue or star the project!*