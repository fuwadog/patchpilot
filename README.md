<div align="center">

# PatchPilot

### AI-Powered Code Refactoring & File Intelligence Engine

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**PatchPilot is a terminal-native AI orchestration engine for real development workflows.**

[Features](#-features) - [Installation](#-installation) - [Usage](#-usage) - [Architecture](#-architecture) - [Roadmap](#-roadmap)

</div>

## Overview

**PatchPilot is not just another chatbot wrapper.**

It's a CLI-first AI orchestration engine designed for developers who need intelligent code analysis, refactoring, and patching capabilities directly from their command line. Built with [Typer](https://typer.tiangolo.com/) and [Rich](https://rich.readthedocs.io/), it supports both interactive REPL and one-shot command modes.

### Why PatchPilot?

- **Multi-format Intelligence** - Analyze code, documents, spreadsheets, and presentations
- **Context-Aware** - Smart memory management prevents context overflow
- **Real-time Patching** - Preview and apply AI-generated code changes
- **Provider-Agnostic** - Works with any OpenAI-compatible API
- **Developer-First** - Built for terminal workflows, not browser chat
- **Dual Mode** - Interactive REPL or one-shot commands

---

## Features

### Multi-Format File Intelligence

PatchPilot automatically extracts and prepares content from various file formats for LLM reasoning:

| Category          | Supported Formats                        |
| ----------------- | ---------------------------------------- |
| **Code**          | `.py` `.js` `.ts` `.html` `.css` `.json` |
| **Documents**     | `.pdf` `.docx` `.rtf` `.odt`             |
| **Data**          | `.xlsx` `.csv`                           |
| **Presentations** | `.pptx`                                  |

### Context-Aware Memory System

- **Token Tracking** - Monitor and optimize context window usage
- **File Pinning** - Lock important files in context
- **Smart Trimming** - Automatic context management
- **Session Isolation** - Separate conversations for different projects
- **Resettable Sessions** - Clean slate when needed
- **Session Persistence** - SQLite-backed history with resume support

### AI-Driven Code Operations

One-shot commands for CI/scripts:

```bash
patchpilot fix src/main.py -i "add error handling"
patchpilot refactor src/utils.py -i "extract to class"
patchpilot patch src/api.py -i "add retry logic"
```

Or use the interactive REPL:

| Command     | Description              | Use Case                           |
| ----------- | ------------------------ | ---------------------------------- |
| `/fix`      | Detect and repair bugs   | Find logical errors, syntax issues |
| `/refactor` | Improve code structure   | Optimize readability, performance  |
| `/patch`    | Generate and apply edits | Apply AI-suggested changes         |
| `/pin`      | Lock file in context     | Maintain focus on key files        |
| `/tokens`   | Inspect token usage      | Monitor context consumption        |
| `/history`  | List past sessions       | Browse previous conversations      |
| `/resume`   | Resume a past session    | Continue where you left off        |

---

**Modular. Extensible. Provider-Agnostic.**

---

## Tech Stack

| Category                | Technologies                    |
| ----------------------- | ------------------------------- |
| **CLI Framework**       | Python 3.10+, Typer             |
| **Terminal Rendering**  | Rich (markdown, tables, panels) |
| **LLM Integration**     | openai SDK, httpx               |
| **Persistence**         | aiosqlite (SQLite)              |
| **Document Processing** | PyPDF2, python-docx, openpyxl   |
| **Presentations**       | python-pptx                     |
| **Web Parsing**         | beautifulsoup4                  |
| **Office Formats**      | odfdo, striprtf                 |
| **Configuration**       | python-dotenv                   |

---

## Installation

### Prerequisites

- Python 3.10 or higher
- pip package manager
- An OpenAI-compatible API key

### Quick Start

#### Option A: Install as a CLI tool (recommended)

```powershell
# Clone the repository
git clone https://github.com/fuwadog/patchpilot.git
cd patchpilot

# Create virtual environment
python -m venv venv

# Activate virtual environment (PowerShell)
venv\Scripts\Activate.ps1

# Install in editable mode (installs patchpilot command)
pip install -e .
```

#### Option B: Run from source

```powershell
# Clone and install dependencies
git clone https://github.com/fuwadog/patchpilot.git
cd patchpilot
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Environment Setup

```powershell
# Copy the example env file
copy .env.example .env
# Edit .env with your credentials
notepad .env
```

---

## Configuration

Create a `.env` file in the project root:

```bash
# API Configuration (required)
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://integrate.api.nvidia.com/v1
AI_MODEL=z-ai/glm4.7

# Model Parameters
AI_TEMPERATURE=0.4
MAX_RESPONSE_TOKENS=4096

# Context Management
MAX_TOTAL_TOKENS=4500
MAX_FILE_TOKENS=1500
MAX_CONVO_MESSAGES=40
MAX_FILES=12

# Persistence
PATCHPILOT_DB_PATH=~/.patchpilot/sessions.db
```

### Environment Variables Reference

| Variable              | Default                               | Description                 |
| --------------------- | ------------------------------------- | --------------------------- |
| `OPENAI_API_KEY`      | `""`                                  | API key for provider        |
| `OPENAI_BASE_URL`     | `https://integrate.api.nvidia.com/v1` | API endpoint                |
| `AI_MODEL`            | `z-ai/glm4.7`                         | Model identifier            |
| `AI_TEMPERATURE`      | `0.4`                                 | LLM temperature (0.0-2.0)   |
| `MAX_TOTAL_TOKENS`    | `4500`                                | Max context window tokens   |
| `MAX_FILE_TOKENS`     | `1500`                                | Max tokens per file         |
| `MAX_CONVO_MESSAGES`  | `40`                                  | Max conversation turns      |
| `MAX_FILES`           | `12`                                  | Max concurrent loaded files |
| `MAX_RESPONSE_TOKENS` | `4096`                                | Max tokens per response     |

### Supported Providers

PatchPilot works with any OpenAI-compatible API endpoint:

- NVIDIA AI Foundation Models
- OpenAI GPT Models
- Azure OpenAI
- Local models (via Ollama, LM Studio, vLLM)
- Any provider with OpenAI-compatible API

---

## Usage

### Starting PatchPilot

```bash
# Interactive REPL
python -m src

# Or if installed as a CLI tool:
patchpilot
patchpilot chat
```

### One-Shot Commands

Run code operations directly without entering the REPL:

```bash
# Fix bugs in a file
patchpilot fix src/main.py -i "add null check before method call"

# Refactor code
patchpilot refactor src/utils.py -i "extract duplicate logic into helper"

# Generate and preview a patch
patchpilot patch src/api.py --instructions "add retry with backoff"

# Dry-run (preview without applying)
patchpilot fix src/main.py -i "fix bug" --dry-run
```

### REPL File Operations

```bash
# Load a single file
/file src/app.py

# Load entire directory
/folder src/

# Pin important file to context
/pin main.py

# List loaded files
/list

# Show file content
/show main.py

# Unload a file
/unload main.py

# Clear all files
/unload-all
```

### REPL Context Management

```bash
# Check token usage
/tokens

# Show detailed context info
/context

# Reset conversation
/reset

# Show help
/help

# List past sessions
/history

# Resume a session
/resume <session-id>

# Save a code snippet
/snippet save my-helper

# List snippets
/snippet list
```

### Example Workflow

```bash
# 1. Start REPL
patchpilot

# 2. Load your legacy project
>>> /folder legacy_project/

# 3. Pin critical file
>>> /pin main.py

# 4. Check token budget
>>> /tokens

# 5. Request refactoring
>>> /refactor

# 6. Review and apply patch
>>> /patch
```

---

## Upcoming Features

- [x] **Streaming responses** (real-time output)
- [x] **Session persistence** (SQLite-backed history)
- [x] **One-shot commands** (CI-friendly mode)
- [ ] **Vector-based file indexing** (FAISS/ChromaDB)
- [ ] **Multi-provider routing** (fallback strategies)
- [ ] **Git integration** (commit, diff, branch operations)
- [ ] **Interactive diff viewer** (side-by-side comparison)
- [ ] **Docker support** (containerized deployment)
- [ ] **CI/CD pipeline** (GitHub Actions)
- [ ] **Plugin system** (extensible architecture)
- [ ] **RAG integration** (knowledge base augmentation)

---

## Contributing

Contributions are welcome! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Commit your changes** (`git commit -m 'Add amazing feature'`)
4. **Push to the branch** (`git push origin feature/amazing-feature`)
5. **Open a Pull Request**

### Development Setup

```bash
# Install with dev dependencies
pip install -e ".[dev]"
# Or from requirements-dev.txt
pip install -r requirements-dev.txt
```

---

## License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- Built for the developer community (nah, i just made this for me to use, feel free to roast me or something...)
- Powered by NVIDIA AI Foundation Models
- Inspired by the need for intelligent, terminal-native development tools

---

<div align="center">

### PatchPilot is not a chatbot wrapper.

**It's a terminal-native AI orchestration engine for real development workflows.**

[Star this project](https://github.com/fuwadog/patchpilot) - [Report Bug](https://github.com/fuwadog/patchpilot/issues) - [Request Feature](https://github.com/fuwadog/patchpilot/issues)

</div>
