#!/usr/bin/env bash
# lint.sh - Run linting and type checks according to pyproject.toml

set -euo pipefail

echo "🧹 Running Ruff lint checks..."
ruff check .

echo "🎨 Running Ruff format checks..."
ruff format . --check

echo "🔍 Running ty type checks..."
ty check aperisolve

echo "🧪 Running pytest..."
pytest -q

echo "✅ All checks passed!"
