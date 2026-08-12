# Settings — always use -euo pipefail for safety
set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

# Aliases — shortcuts
alias h := hooks

# Default — show available recipes
default:
    @just --list

# Build the wheel
[group("build")]
build:
    @echo "Building wheel..."
    uv build

# Run tests
[group("qa")]
test *args:
    @echo "Running tests..."
    uv run pytest {{ args }}

# Run pre-commit hooks on all files
[group("qa")]
hooks:
    @echo "Running pre-commit hooks..."
    prek run --all-files

# Update dependencies and hooks
[group("maintenance")]
update:
    @echo "Updating dependencies..."
    uv lock --upgrade
    @echo "Updating hooks..."
    prek auto-update
    prek run --all-files
