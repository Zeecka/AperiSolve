#!/usr/bin/env bash
# lint.sh - Run all formatters, linters, and type checks according to pyproject.toml

set -euo pipefail

echo "🖤 Running Black..."
black .

echo "📦 Running Isort..."
isort .

echo "🐍 Running Flake8..."
flake8 --max-line-length 100 --extend-ignore=E203,E501,W503 .

echo "🔍 Running Mypy..."
mypy .

echo "⚡ Running Pylint..."
pylint aperisolve/

echo "✅ All checks passed!"
