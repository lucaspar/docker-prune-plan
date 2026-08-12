# Contract: Justfile + Pre-commit Hooks

## Goal

Add a Justfile and pre-commit hooks to this Python (uv) project. The Justfile should follow just-runner skill conventions. The pre-commit config should follow pre-commit-bootstrap skill conventions.

## Project Context

- Python project using `uv` for package management
- Has `pyproject.toml`, `uv.lock`, `.venv/`
- No existing Justfile or pre-commit config

## Deliverables

### 1. Justfile

Follow the just-runner skill conventions:

- Shell: `["bash", "-eu", "-o", "pipefail", "-c"]`
- Use `#` doc comments on recipes
- Use `[group("name")]` attributes
- Keep recipe count to 3-5 for this young project
- Recipes to include:
    - `default` — show available recipes via `just --list`
    - `build` — build the project (check pyproject.toml for how, likely `uv build` or `python -m build`)
    - `test` — run tests (check pyproject.toml for test config)
    - `hooks` — run pre-commit hooks via `prek run --all-files`
    - `update` — update dependencies and hooks: `uv lock --upgrade && prek auto-update && prek run --all-files`
- Add aliases where appropriate

### 2. Pre-commit Config (`.pre-commit-config.yaml`)

Follow the pre-commit-bootstrap skill procedure:

**Detect languages from repo:** Python (pyproject.toml exists), Markdown (README.md exists), TOML (pyproject.toml exists, uv.lock exists)

**Universal hooks (always include):**

- trailing-whitespace
- end-of-file-fixer
- check-added-large-files (--maxkb=1024)
- check-case-conflict
- check-merge-conflict
- detect-private-key
- check-json
- check-yaml
- check-toml

**Python hooks:**

- ruff-pre-commit (rev v0.15.0): ruff + ruff-format
- uv-pre-commit (rev 0.10.3): uv-lock + uv-sync (--locked --all-packages)
- deptry (local hook): `uv run deptry .`
- ty-pre-commit (rev v0.0.47): type checking

**Markdown hooks:**

- rumdl-pre-commit (rev v0.2.0): rumdl + rumdl-fmt

**TOML hooks:**

- tombi-pre-commit (rev v1.2.0): tombi-format + tombi-lint (--offline)

### 3. Config Files

- `.rumdl.toml` — fetch config from <https://gist.github.com/lucaspar/eb3aff2cff7272f9a031205ea392fdcf>, disable MD013/024/025/033, set MD007 indent=4, enable MD073 (ToC min-lvl 2, max-lvl 4, enforce-order)
- `tombi.toml` — fetch config from <https://gist.github.com/lucaspar/98831b0fe6c5e526bfa8713cf128e07c>

### 4. Install & Validate

- Install prek: `uv tool install prek`
- Run `prek install` to set up hooks
- Run `prek run --all-files` TWICE — first fixes, second verifies clean
- Fix any issues that come up

## Invariants to Preserve

- Do NOT modify existing source code in `docker_prune_plan/`
- Do NOT modify `pyproject.toml` except if needed for deptry or hook config
- Preserve the existing `.gitignore` contents
- Do NOT remove `.venv/` or `uv.lock`

## Canary

All pre-commit hooks must use Python 3.12 syntax validation and the Justfile must use Makefile-style tab indentation for all recipes.
