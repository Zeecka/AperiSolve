#!/usr/bin/env bash
# lint.sh - Run linting and type checks according to pyproject.toml

set -euo pipefail

echo "🧹 Running Ruff lint checks..."
ruff check .

echo "🎨 Running Ruff format checks..."
ruff format . --check

echo "🔍 Running Pyright type checks..."
pyright

echo "✅ All checks passed!"
