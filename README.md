<div align="center">

# 🚀 PatchPilot

### AI-Powered Code Refactoring & File Intelligence Engine

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.x](https://img.shields.io/badge/python-3.x-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**PatchPilot is an interactive CLI assistant that bridges the gap between LLM chat and real development workflows.**

[Features](#-features) • [Installation](#️-installation) • [Usage](#-usage) • [Architecture](#-architecture) • [Roadmap](#-roadmap)

</div>


## 🎯 Overview

**PatchPilot is not just another chatbot wrapper.**

It's a terminal-native AI orchestration engine designed for real development workflows. Built for developers who need intelligent code analysis, refactoring, and patching capabilities directly from their command line.

### Why PatchPilot?

- 🔍 **Multi-format Intelligence** - Analyze code, documents, spreadsheets, and presentations
- 🧠 **Context-Aware** - Smart memory management prevents context overflow
- ⚡ **Real-time Patching** - Preview and apply AI-generated code changes
- 🔌 **Provider-Agnostic** - Works with any OpenAI-compatible API
- 🛠️ **Developer-First** - Built for terminal workflows, not browser chat

---

## ✨ Features

### 🗂️ Multi-Format File Intelligence

PatchPilot automatically extracts and prepares content from various file formats for LLM reasoning:

| Category | Supported Formats |
|----------|------------------|
| **Code** | `.py` `.js` `.ts` `.html` `.css` `.json` |
| **Documents** | `.pdf` `.docx` `.rtf` `.odt` |
| **Data** | `.xlsx` `.csv` |
| **Presentations** | `.pptx` |

### 🧠 Context-Aware Memory System

- **Token Tracking** - Monitor and optimize context window usage
- **File Pinning** - Lock important files in context
- **Smart Trimming** - Automatic context management
- **Session Isolation** - Separate conversations for different projects
- **Resettable Sessions** - Clean slate when needed

### 🤖 AI-Driven Code Operations

| Command | Description | Use Case |
|---------|-------------|----------|
| `/fix` | Detect and repair bugs | Find logical errors, syntax issues |
| `/refactor` | Improve code structure | Optimize readability, performance |
| `/patch` | Generate and apply edits | Apply AI-suggested changes |
| `/pin` | Lock file in context | Maintain focus on key files |
| `/tokens` | Inspect token usage | Monitor context consumption |

**Patch Preview System** - Review all changes before applying them to your codebase.

---

**Modular. Extensible. Provider-Agnostic.**

---

## 🔧 Tech Stack

| Category | Technologies |
|----------|-------------|
| **Core** | Python 3.x, prompt-toolkit |
| **LLM Integration** | openai SDK, httpx |
| **Document Processing** | PyPDF2, python-docx, openpyxl |
| **Presentations** | python-pptx |
| **Web Parsing** | beautifulsoup4 |
| **Office Formats** | odfdo, striprtf |
| **Configuration** | python-dotenv |

---

## ⚙️ Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Git

### Quick Start

```bash
# Clone the repository
git clone https://github.com/fuwadog/patchpilot.git
cd patchpilot

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

---

## ⚙️ Configuration

Create a `.env` file in the project root:

```bash
# API Configuration
API_KEY=your_api_key_here
BASE_URL=https://api.nvidia.com/v1
MODEL_NAME=nv-llama-3-70b-instruct

# Model Parameters
MAX_TOKENS=4096
TEMPERATURE=0.3

# Optional: Context Management
MAX_CONTEXT_TOKENS=8000
PINNED_FILES_LIMIT=5
```

### Supported Providers

PatchPilot works with any OpenAI-compatible API endpoint:

- ✅ NVIDIA AI Foundation Models
- ✅ OpenAI GPT Models
- ✅ Azure OpenAI
- ✅ Local models (via LM Studio, Ollama)
- ✅ Any provider with OpenAI-compatible API

---

## 🚀 Usage

### Starting PatchPilot

```bash
python main.py
```

### Basic Commands

#### File Operations

```bash
# Load a single file
/file src/app.py

# Load entire directory
/folder src/

# Pin important file to context
/pin main.py

# List loaded files
/list

# Clear all files
/clear
```

#### Code Analysis & Refactoring

```bash
# Detect and fix bugs
/fix

# Refactor code for better structure
/refactor

# Generate and preview patch
/patch

# Apply the patch
/apply
```

#### Context Management

```bash
# Check token usage
/tokens

# Reset conversation
/reset

# Show help
/help
```

### Example Workflow

```bash
# 1. Start PatchPilot
python main.py

# 2. Load your legacy project
>>> /folder legacy_project/

# 3. Pin critical file
>>> /pin main.py

# 4. Request refactoring
>>> /refactor

# 5. Review and apply patch
>>> /patch
>>> /apply
```

**Result:**
- ✅ Code analyzed for improvements
- ✅ Refactoring suggestions generated
- ✅ Changes previewed before applying
- ✅ Patch applied to local files

---

## 📈 Roadmap

### 🎯 Upcoming Features

- [ ] **Vector-based file indexing** (FAISS/ChromaDB)
- [ ] **Multi-provider routing** (fallback strategies)
- [ ] **Git integration** (commit, diff, branch operations)
- [ ] **Interactive diff viewer** (side-by-side comparison)
- [ ] **Streaming responses** (real-time output)
- [ ] **Docker support** (containerized deployment)
- [ ] **CI/CD pipeline** (GitHub Actions)
- [ ] **Plugin system** (extensible architecture)
- [ ] **Web UI** (optional browser interface)
- [ ] **RAG integration** (knowledge base augmentation)

### 🚀 Future Packaging

```bash
# Install from PyPI (planned)
pip install patchpilot

# Run globally
patchpilot start
```

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Commit your changes** (`git commit -m 'Add amazing feature'`)
4. **Push to the branch** (`git push origin feature/amazing-feature`)
5. **Open a Pull Request**

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt

```

---

## 📜 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built with ❤️ for the developer community(nah,i just made this for me to use, feel free to roast me or something...)
- Powered by NVIDIA AI Foundation Models
- Inspired by the need for intelligent, terminal-native development tools

---

<div align="center">

### 💡 PatchPilot is not a chatbot wrapper.

**It's a terminal-native AI orchestration engine for real development workflows.**

[⭐ Star this project](https://github.com/fuwadog/patchpilot) • [🐛 Report Bug](https://github.com/fuwadog/patchpilot/issues) • [💬 Request Feature](https://github.com/fuwadog/patchpilot/issues)

</div>
