# AGENTS.md

This file contains essential information for agents working on this codebase.

## Project Overview

**auto-commit** is a Python utility that detects changed files in a git repository, collects their diffs, and automatically generates commit messages using AI. Users can choose between Google Gemini (via `google-genai`), Z.AI GLM Coding Plan (OpenAI-compatible), or OpenAI.

## Essential Commands

### Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Activate virtual environment (if present)
source .venv/bin/activate
```

### Running
```bash
# Direct execution
python3 auto-commit.py

# Or via installed executable (when set up)
autocommit

# With options
autocommit --provider gemini --lang Deutsch --model gemini-2.5-flash
autocommit --provider zai --model GLM-4.6 --zai-base-url https://api.z.ai/api/coding/paas/v4
autocommit --provider openai --model gpt-5.2
```

### CLI Options
- `--lang`: Commit message language
- `--provider`: AI provider (`gemini`, `zai`, or `openai`)
- `--model`: Model name for the selected provider
- `--zai-base-url`: Custom base URL for Z.AI Coding API
- `--openai-base-url`: Custom base URL for OpenAI
- `--style`: Commit style (`sarcastic`, `humorous`, or `standard` - default)

## Project Structure

- `auto-commit.py` - Main script (single-file utility)
- `requirements.txt` - Python dependencies
- `env.example` - Environment configuration template
- `.env` - Local environment configuration (not tracked in git)
- `.venv/` - Virtual environment (not tracked in git)

## Code Organization

### Main Functions (auto-commit.py)

- `find_git_root()` - Locates git repository root
- `get_staged_and_deleted_files()` - Separates staged files from deleted files
- `get_diff_for_file()` - Retrieves staged changes for a specific file
- `create_ai_clients()` - Initializes AI provider clients
- `generate_commit_message()` - Generates commit message using AI
- `prompt_to_stage()` - Interactive prompt for staging files
- `write_commit_template()` - Writes commit message + context to temp file
- `main()` - Main execution flow

### Configuration Loading
- Uses `python-dotenv` to load `.env` file
- Configuration defaults defined at top of script (lines 16-29)
- CLI arguments override `.env` values
- Provider selection via `AI_PROVIDER` environment variable or `--provider` flag

## Dependencies

- `gitpython` - Git repository operations
- `google-genai` - Google Gemini API client
- `openai` - OpenAI API client (also used for Z.AI compatibility)
- `python-dotenv` - Environment variable management

## AI Providers

### Google Gemini
- Uses `google-genai` library
- Default model: `gemini-2.5-flash`
- Configuration: `GEMINI_API_KEY`, `GEMINI_MODEL`

### Z.AI GLM Coding Plan
- Uses OpenAI-compatible API
- Endpoint: `https://api.z.ai/api/coding/paas/v4` (Coding API, not General API)
- Recommended models: `GLM-4.7`, `GLM-4.6`, `GLM-4.5`, `GLM-4.5-air`
- Configuration: `ZAI_API_KEY`, `ZAI_MODEL`, `ZAI_BASE_URL`

### OpenAI
- Uses OpenAI Python SDK (`chat.completions`)
- Default model: `gpt-5.2`
- Configuration: `OPENAI_API_KEY`, `OPENAI_MODEL`, optional `OPENAI_BASE_URL`

## Naming Conventions & Style Patterns

### Code Style
- Python 3 with type hints throughout
- German language in user-facing strings, comments, and documentation
- Function docstrings in German
- Use of descriptive function names (e.g., `get_staged_and_deleted_files`)

### Variable Naming
- Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_LANGUAGE`, `AI_PROVIDER`)
- Functions: `snake_case` (e.g., `generate_commit_message`)
- Variables: `snake_case` (e.g., `commit_message`, `file_diffs`)

### Error Handling
- Custom exception: `CommitGenerationError` for AI generation failures
- Catches 429/RESOURCE_EXHAUSTED errors and raises custom error
- Falls back to `"chore: update changes"` on non-critical errors
- Explicit `ValueError` for missing configuration

## Important Gotchas

### Git Operations
- Uses both `GitPython` library and `subprocess` for git operations
- `get_staged_and_deleted_files()` separates deleted files to handle them correctly
- Untracked files added with `--all` flag: `repo.git.add(all=True)`
- Modified files added explicitly: `repo.git.add(files)`
- Always checks for `origin` remote before attempting push

### Prompt Engineering
- Commit message prompt includes file paths and diffs
- Enforces short summary line (max 72 characters)
- Instructs against markdown formatting (no ``` or headers)
- Reduces multiple newlines to double newlines (regex: `r"\n{3,}"`)

### Editor Integration
- Uses `$EDITOR` environment variable, defaults to `vim`
- Creates temp file with commit template containing:
  - Generated commit message
  - Comments listing modified and deleted files
  - Full diffs for context
- Removes comment lines when reading final message
- Deletes temp file in `finally` block

### User Interaction
- Interactive prompts for staging files (y/n)
- Confirmation prompt before committing
- Checks if final commit message is empty before proceeding

### Commit Style Feature
- Controlled by `--style` CLI option (default: `standard`)
- Supported styles: `standard`, `sarcastic`, `humorous`
- When `sarcastic` or `humorous` is selected:
  - Enhanced prompt with style-specific instructions
  - Requests dry, subtle sarcasm or humor
  - Requires staying technically accurate, understandable, and git-conform
  - Prohibits silliness and memes
- Emojis are allowed in all commit styles
- Default mode prompt remains unchanged
- Style is passed to `generate_commit_message()` as `commit_style` parameter

## Testing Approach

**No tests currently present** in this codebase.

If adding tests, consider:
- Mocking Git operations and AI clients
- Testing file staging logic
- Testing prompt generation and message formatting
- Testing error handling paths

## Environment Configuration

Copy `env.example` to `.env` and configure:

```bash
cp env.example .env
```

Required variables (depending on provider):
- `AI_PROVIDER` - Choose `gemini`, `zai`, or `openai`
- Provider-specific API key
- `COMMIT_LANGUAGE` - Default commit message language

## Workflow

1. Detect untracked and unstaged modified files
2. Prompt user to stage files (interactive y/n)
3. Collect diffs from staged files
4. Generate commit message using selected AI provider
5. Open editor with commit message template
6. User edits and confirms (y/n)
7. Execute git commit
8. Push to origin if remote exists

## Non-Obvious Patterns

### Type Casting
- Uses `cast(str, item.a_path)` when processing unstaged files to satisfy type checker

### Provider Detection
- Z.AI and OpenAI both use OpenAI-compatible client
- Provider selection happens at runtime based on configuration
- Default to Gemini if invalid provider specified

### German Localization
- All user-facing text is in German
- Error messages in German
- Comments and docstrings in German
- Only commit message language is configurable

### File Diff Collection
- Collects diffs for both modified and deleted files
- Deleted files included in `file_diffs` dict for AI context
- Uses `--cached` flag for staged changes only
