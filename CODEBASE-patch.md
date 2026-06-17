# PatchPilot — CODEBASE.md

## Section 1 · Core Use Case & Problem Solved

PatchPilot is a terminal-native AI orchestration engine that bridges LLM chat and real development workflows. It provides interactive code analysis, refactoring, and patch generation directly from the command line — with multi-format file intelligence (PDF, Word, Excel, presentations, code), token-aware context management, and safe patch application with diff preview and backups.

**Confidence: HIGH** — documented in README.md

**Key files:**
- `src/app.py` — Application factory and interactive prompt loop entry point
- `src/__main__.py` — `python -m src` entry point
- `src/cli/dispatcher.py` — Central command dispatch routing all `/` commands

---

## Section 2 · Tech Stack & Ecosystem

**Language:** Python 3.10+
**CLI framework:** prompt-toolkit 3.x (interactive prompt, autocomplete)
**LLM integration:** openai SDK + httpx (OpenAI-compatible streaming)
**Document processing:** pypdf, python-docx, openpyxl, python-pptx, beautifulsoup4, striprtf, odfdo, defusedxml
**Configuration:** python-dotenv (reads `.env.local`)
**Dev tooling:** ruff (linter), mypy (type checker), black (formatter), isort (import sort), bandit (security), safety (dep audit), pytest + pytest-cov (testing)

**Key files:**
- `pyproject.toml` — Project metadata, dependencies, all tool configs (ruff, mypy, black, isort, bandit, pytest)
- `requirements.txt` — 12 runtime dependencies
- `requirements-dev.txt` — Dev tool dependencies

---

## Section 3 · File Tree & Architecture

```
patchpilot/
├── .env.example               # Environment variable template
├── .gitignore                 # Python + IDE ignores
├── .safety-policy.yml         # Safety false-positive ignore list
├── LICENSE                    # MIT License
├── Makefile                   # CI command targets (lint, typecheck, security, test, format, clean)
├── README.md                  # Comprehensive project documentation
├── pyproject.toml             # Project config + all tool configurations
├── requirements.txt           # Runtime dependencies
├── requirements-dev.txt       # Dev dependencies
├── docs/
│   └── quickstart.md          # Windows-focused 5-minute setup guide
├── scripts/
│   ├── check.ps1              # PowerShell CI script (ruff → mypy → safety → pytest)
│   └── clean.py               # Cache/build artifact cleanup
├── src/
│   ├── __init__.py            # Package docstring
│   ├── __main__.py            # Entry point for `python -m src`
│   ├── app.py                 # Application factory: build_app() → CommandDispatcher; main() runs loop
│   ├── config.py              # Config class — reads .env.local via python-dotenv
│   ├── cli/
│   │   ├── __init__.py        # Exports CLICompleter, CommandDispatcher, Display
│   │   ├── completer.py       # Prompt-toolkit fuzzy autocomplete for commands, paths, snippets
│   │   ├── dispatcher.py      # CommandDispatcher — routes all / commands to handlers
│   │   └── display.py         # Display — TTY-aware ANSI terminal output (stream, reasoning, table)
│   ├── client/
│   │   ├── __init__.py        # Exports ModelProvider, StreamChunk, providers
│   │   ├── base.py            # ModelProvider ABC + StreamChunk dataclass
│   │   ├── nvidia.py          # NvidiaProvider — OpenAI-compatible streaming with retry + thinking tokens
│   │   └── ollama.py          # OllamaProvider — local Ollama streaming via OpenAI-compatible endpoint
│   ├── context/
│   │   ├── __init__.py        # Exports ContextManager, Message
│   │   └── manager.py         # Three-layer context (system + files + conversation), token budgeting, pinning
│   ├── files/
│   │   ├── __init__.py        # Exports FileManager, PatchManager, FileReaders, SnippetManager
│   │   ├── manager.py         # FileManager — load/unload files (12 formats), folder discovery, glob patterns
│   │   ├── patching.py        # PatchManager — extract code blocks, unified diff preview, backup + atomic write
│   │   ├── readers.py         # FileReaders — 12 static format readers (PDF, DOCX, XLSX, CSV, JSON, XML, HTML, RTF, ODT, PPTX, text)
│   │   └── snippets.py        # SnippetManager — in-memory named code snippet storage
│   └── session/
│       ├── __init__.py        # Exports SessionManager
│       └── manager.py         # SessionManager — orchestrates provider streaming + conversation history
└── tests/
    ├── __init__.py
    ├── test_cli/__init__.py    # CLI test package (stub — no tests yet)
    ├── test_client/__init__.py # Client test package (stub)
    ├── test_context/__init__.py # Context test package (stub)
    ├── test_files/__init__.py   # Files test package (stub)
    └── test_session/__init__.py # Session test package (stub)
```

**Architecture pattern:** Layered modular architecture with dependency injection.

**Key files:**
- `src/app.py` — Top-level wiring (creates all components, injects dependencies)
- `src/cli/dispatcher.py` — Command routing layer
- `src/session/manager.py` — Orchestration layer
- `src/client/base.py` — Provider abstraction layer
- `src/files/` — File I/O and patching layer
- `src/context/manager.py` — State management layer

---

## Section 4 · Configuration & Environment

**Primary config:** `.env.local` (loaded by `src/config.py` via python-dotenv from project root)

**Environment variables (from `.env.example`):**

| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_BASE_URL` | `https://integrate.api.nvidia.com/v1` | OpenAI-compatible API endpoint |
| `OPENAI_API_KEY` | (empty — required) | API key for provider |
| `AI_MODEL` | `z-ai/glm4.7` | Model name |
| `AI_TEMPERATURE` | `0.4` | Sampling temperature |
| `MAX_FILES` | `12` | Max files per folder load |
| `MAX_FILE_TOKENS` | `1500` | Max tokens per file in context |
| `MAX_TOTAL_TOKENS` | `4500` | Total context window budget |
| `MAX_CONVO_MESSAGES` | `40` | Max conversation history messages |
| `MAX_RESPONSE_TOKENS` | `4096` | Max tokens per assistant response |
| `ENABLE_SYNTAX_VALIDATION` | `false` | Syntax validation before writes |
| `BACKUP_ON_WRITE` | `true` | Create backups before patches |
| `DIFF_PREVIEW` | `true` | Show unified diff before apply |
| `MAX_RETRIES` | `3` | API retry attempts |
| `RETRY_DELAY` | `1.5` | Base retry delay (exponential backoff) |

**CI/CD:** No GitHub Actions detected. CI is manual via `make ci` or `scripts/check.ps1` (ruff → mypy → safety → pytest).

**Key files:**
- `.env.example` — Environment variable template
- `src/config.py` — Config class with all defaults and env overrides
- `Makefile` — CI command targets
- `scripts/check.ps1` — PowerShell CI pipeline
- `.safety-policy.yml` — Safety false-positive ignores

---

## Section 5 · Entry Points & Data Flow

**Entry point:** `src/__main__.py` → `src.app.main()`

**Data flow (CLI → LLM → Patch):**

```
User types input
    → prompt() with FuzzyCompleter (src/cli/completer.py)
    → CommandDispatcher.dispatch() (src/cli/dispatcher.py)
    → if /command: handler method executes directly
    → if chat: SessionManager.send() (src/session/manager.py)
        → ContextManager.build_messages() (src/context/manager.py)
            → assembles: system_prompt + file_messages + conversation_history
            → enforces token budget (drops oldest convo, compresses files)
        → NvidiaProvider.stream() (src/client/nvidia.py)
            → OpenAI SDK streaming with retry logic
            → yields StreamChunk(content, reasoning)
        → Display.stream() / Display.reasoning() (src/cli/display.py)
        → ContextManager.add_assistant() (saves to conversation)
    → if /patch: PatchManager.extract_code_block() → .apply()
        → unified diff preview → confirmation → backup → atomic write
```

**Key files:**
- `src/__main__.py` — Entry point
- `src/app.py` — `build_app()` wires all components; `main()` runs interactive loop
- `src/cli/dispatcher.py` — Central dispatch
- `src/session/manager.py` — Message flow orchestration
- `src/client/nvidia.py` — LLM streaming
- `src/context/manager.py` — Message assembly + token enforcement
- `src/files/patching.py` — Patch extraction + safe write

---

## Section 6 · Source Code Internals

The codebase follows a clean layered architecture with dependency injection at the top (`app.py`). Each layer has a single responsibility:

```
[module-map]
__main__.py → app.py (build_app + main loop)
    app.py → Config → NvidiaProvider
    app.py → ContextManager (3-layer: system + files + convo)
    app.py → SessionManager (provider + context + display)
    app.py → FileManager (readers + context injection)
    app.py → PatchManager (diff + backup + atomic write)
    app.py → SnippetManager (in-memory storage)
    app.py → CommandDispatcher (routes all /commands)
        dispatcher.py → SessionManager.send() → NvidiaProvider.stream()
        dispatcher.py → FileManager.load() → FileReaders.*()
        dispatcher.py → PatchManager.apply() → atomic write
    app.py → CLICompleter (prompt-toolkit fuzzy autocomplete)
```

**Key modules:**

- **`src/app.py`** — Application factory. Creates Config, NvidiaProvider, ContextManager, SessionManager, FileManager, PatchManager, SnippetManager, CommandDispatcher. Runs the prompt loop.
- **`src/config.py`** — `Config` class. Reads `.env.local` via python-dotenv. Exposes all settings as class attributes with defaults.
- **`src/cli/dispatcher.py`** — `CommandDispatcher`. Routes 19 commands (`/file`, `/folder`, `/fix`, `/refactor`, `/patch`, `/pin`, `/snippet`, etc.). Falls through to chat for non-command input.
- **`src/session/manager.py`** — `SessionManager`. Orchestrates: context build → provider stream → display → history update. Handles interrupts.
- **`src/context/manager.py`** — `ContextManager`. Three-layer context (system prompt, file messages, conversation history). Token budget enforcement with fallback compression. File pinning.
- **`src/client/base.py`** — `ModelProvider` ABC + `StreamChunk` dataclass. Defines the streaming interface.
- **`src/client/nvidia.py`** — `NvidiaProvider`. OpenAI-compatible streaming with exponential backoff retry (APIConnectionError, RateLimitError). Supports reasoning/thinking tokens.
- **`src/client/ollama.py`** — `OllamaProvider`. Local Ollama via OpenAI-compatible endpoint.
- **`src/files/manager.py`** — `FileManager`. Load/unload single files or folders. Glob-based discovery. Delegates reading to `FileReaders`, context injection to `ContextManager`.
- **`src/files/readers.py`** — `FileReaders`. 12 static methods for PDF, DOCX, XLSX, CSV, JSON, XML, HTML, RTF, ODT, PPTX, plain text. Graceful fallback on missing deps.
- **`src/files/patching.py`** — `PatchManager`. Extract fenced code blocks from responses. Unified diff preview (colorized). Backup with rotation (max 5). Atomic write via temp file + rename.
- **`src/files/snippets.py`** — `SnippetManager`. In-memory named code snippet storage.
- **`src/cli/display.py`** — `Display`. TTY-aware ANSI output. Methods: `stream()`, `reasoning()`, `info()`, `success()`, `warning()`, `error()`, `table()`.
- **`src/cli/completer.py`** — `CLICompleter`. Prompt-toolkit completer with command, path, loaded-file, and snippet completions. Wrapped in `FuzzyCompleter`.

**Notable patterns:**
- No god-objects; each class has a focused responsibility
- `ContextManager` enforces token budgets at build time, not per-message
- `PatchManager` uses atomic writes (temp + os.replace) for safety
- `FileReaders` uses lazy imports with graceful fallback on missing dependencies

---

## Section 7 · API Surface

**Transport:** This is a CLI application, not a web server. No HTTP routes, REST, GraphQL, or gRPC endpoints.

**Command interface:** 19 slash commands routed through `CommandDispatcher.dispatch()`:

| Command | Handler | Purpose |
|---|---|---|
| `/exit` | `_cmd_exit` | Quit the application |
| `/help` | `_cmd_help` | Show help text |
| `/reset` | `_cmd_reset` | Clear conversation history |
| `/file <path>` | `_cmd_file` | Load a single file into context |
| `/folder <path>` | `_cmd_folder` | Load files from a folder (up to MAX_FILES) |
| `/list` | `_cmd_list` | List all loaded files |
| `/show <path>` | `_cmd_show` | Print truncated content of a loaded file |
| `/unload <path>` | `_cmd_unload` | Remove a file from context |
| `/unload-all [--force]` | `_cmd_unload_all` | Unload all non-pinned files |
| `/unload-folder <path>` | `_cmd_unload_folder` | Unload all files from a folder |
| `/unload-pattern <glob>` | `_cmd_unload_pattern` | Unload files matching a glob |
| `/pin <path>` | `_cmd_pin` | Pin a file to prevent unloading |
| `/unpin <path>` | `_cmd_unpin` | Remove pin from a file |
| `/fix <path> [instr]` | `_cmd_code_op` | Fix bugs in a file |
| `/refactor <path> [instr]` | `_cmd_code_op` | Refactor a file |
| `/patch <path> [instr]` | `_cmd_code_op` | Generate and optionally apply a patch |
| `/snippet save\|show\|list\|del` | `_cmd_snippet` | Manage named code snippets |
| `/tokens` | `_cmd_tokens` | Show estimated token usage |
| `/context-info` | `_cmd_context_info` | Detailed token and file stats |
| (anything else) | → `SessionManager.send()` | Chat with the AI assistant |

**Key files:**
- `src/cli/dispatcher.py` — All command handlers
- `src/session/manager.py` — Chat message flow
- `src/client/nvidia.py` — LLM streaming provider

---

## Section 8 · Database Schema

[MISSING] — No database, ORM, or persistent storage detected. PatchPilot is stateless between sessions. File content is stored in-memory (`FileManager._store` dict). Code snippets are in-memory (`SnippetManager._snippets` dict). Backups are written to `backups/` directory as `.bak` files with timestamp rotation.

**Key files:**
- `src/files/manager.py` — In-memory file store
- `src/files/snippets.py` — In-memory snippet store
- `src/files/patching.py` — Backup file management

---

## Section 9 · Auth & Security Patterns

**Auth:** None. PatchPilot is a local CLI tool with no authentication layer. API keys are stored in `.env.local` (gitignored) and passed directly to the OpenAI SDK client.

**Security tooling:**
- `bandit` — Python static analysis for common security issues (config in `pyproject.toml`)
- `safety` — Dependency vulnerability scanning (config in `.safety-policy.yml`)
- `defusedxml` — Safe XML parsing (prevents XXE attacks)
- Atomic file writes via temp file + `os.replace` (prevents corruption on crash)

**Key files:**
- `src/config.py` — API key management (from env var, with interactive fallback)
- `.safety-policy.yml` — Safety false-positive ignore list
- `pyproject.toml` — Bandit config (excludes venv, .git, __pycache__)
- `src/files/readers.py` — Uses `defusedxml` for XML parsing

---

## Section 10 · Test Coverage Signals

**Test framework:** pytest + pytest-cov (configured in `pyproject.toml`)

**Current state:** [MISSING] — Test directory structure exists (`tests/test_cli/`, `tests/test_client/`, `tests/test_context/`, `tests/test_files/`, `tests/test_session/`) but all test packages contain only empty `__init__.py` stubs. **No actual test functions exist.**

**What is NOT tested:**
- `src/cli/dispatcher.py` — Command routing logic
- `src/session/manager.py` — Session orchestration
- `src/context/manager.py` — Token budgeting, file pinning, context assembly
- `src/files/manager.py` — File loading, discovery, unloading
- `src/files/readers.py` — All 12 format readers
- `src/files/patching.py` — Diff preview, backup, atomic write
- `src/files/snippets.py` — Snippet CRUD
- `src/client/nvidia.py` — Streaming, retry logic
- `src/client/ollama.py` — Local streaming
- `src/config.py` — Config loading

**Coverage config:** pytest-cov configured with `--cov=src/ --cov-report=term-missing`

**Key files:**
- `tests/` — Empty test stubs
- `pyproject.toml` — Test configuration
- `Makefile` — `make test` target
