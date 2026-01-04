u# Contributing to Aperi'Solve

Thank you for your interest in contributing! We welcome all contributions, whether it's bug fixes, new features, or documentation improvements.

## Getting Started

> [!TIP]
> New to the project? Adding a new analyzer is a great first contribution! Check out our [Adding a New Analyzer Guide](docs/adding-analyzer.md).

### Quick Steps

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Make your changes**
4. **Test your changes**
5. **Commit with clear messages** (`git commit -m 'Add amazing feature'`)
6. **Push to your fork** (`git push origin feature/amazing-feature`)
7. **Open a Pull Request** describing your changes

## What Can You Contribute?

### 🔧 Adding New Analyzers

Want to add support for a new steganography or forensics tool? We'd love that!

> [!NOTE]
> Check out our detailed tutorial: [Adding a New Analyzer](docs/adding-analyzer.md)

**Quick checklist for new analyzers:**
- [ ] Create analyzer file in `analyzers/`
- [ ] Extend `SubprocessAnalyzer` base class
- [ ] Register in `workers.py`
- [ ] Add tool to Docker setup if needed
- [ ] Test with sample images
- [ ] Update documentation

### 🐛 Bug Fixes

Found a bug? Please:
- Check if it's already reported in [Issues](../../issues)
- If not, open a new issue with reproduction steps
- Feel free to submit a PR with the fix!

### 📚 Documentation

Help us improve:
- Fix typos or unclear explanations
- Add examples and use cases
- Improve installation instructions
- Translate documentation

### 🎨 UI/UX Improvements

Contributions to the web interface are welcome:
- Better error messages
- Improved result presentation
- Mobile responsiveness
- Accessibility improvements

## Code Style & Quality

> [!IMPORTANT]
> Please follow the code style and run linters before submitting.

The project adheres to:

- **Black** (line length 100)
- **Isort** (profile black)
- **Flake8** (ignoring E203, E501, W503)
- **Pylint** (ignoring W0718, R0903, R0801)
- **Mypy** (ignoring unused-awaitable)

See [.pre-commit-config.yaml](.pre-commit-config.yaml) for exact configuration.

### Running Linters Locally

> [!TIP]
> Install pre-commit hooks to automatically check your code before commits:
> ```bash
> pip install pre-commit
> pre-commit install
> ```

**Manual checks:**
```bash
# Format code
black . --line-length 100
isort . --profile black

# Check for issues
flake8 .
pylint **/*.py
mypy .
```

> [!NOTE]
> CI will automatically run these checks on every PR. Make sure they pass!

## Pull Request Guidelines

Use clear, descriptive titles:
- ✅ `Add stegdetect analyzer`
- ✅ `Fix binwalk extraction error handling`
- ✅ `Update documentation for password-protected tools`
- ❌ `Update code`
- ❌ `Fix bug`


### Commit Messages

Write clear, concise commit messages:
```bash
# Good
git commit -m "Add zsteg analyzer for PNG steganography detection"
git commit -m "Fix foremost error detection when no files extracted"

# Not so good
git commit -m "updates"
git commit -m "fix"
```

## Adding New Dependencies

> [!CAUTION]
> Adding new dependencies requires careful consideration.

If your contribution needs new dependencies:

1. **Python packages**: Add to `requirements.txt`
2. **System tools**: Add to `Dockerfile`
3. **Explain why** in your PR description
4. **Keep dependencies minimal** - avoid adding large libraries for small features


## Useful commands

```bash
# development environment (hot reload and local volumes)
docker compose -f compose.dev.yml up --build

# Stop and remove containers, networks and volumes (results are stored in a volume)
docker compose down -v

# Enter web container shell
docker exec -it aperisolve-web bash

# Enter Postgres shell (from host)
docker exec -it postgres psql -U aperiuser -d aperisolve

# Backup all uploaded files
docker cp -r aperisolve-web:/aperisolve/results /path/to/backup/location

# Backup a single uploaded file
docker cp aperisolve-web:/aperisolve/results/filename.ext /path/to/backup/filename.ext
```

> [!WARNING]
> If switching between dev and production compose files, remove the `results` directory or mounted volume to avoid conflicts:
> ```bash
> rm -rf aperisolve/results
> ```

## Docker and Tool Installation

When adding a new analyzer that requires a new tool:

```dockerfile
# In Dockerfile
RUN apt-get update && apt-get install -y \
    your-new-tool \
    && rm -rf /var/lib/apt/lists/*
```

Or for tools requiring compilation:
```dockerfile
RUN git clone https://github.com/tool/repo.git /tmp/tool && \
    cd /tmp/tool && \
    make && make install && \
    rm -rf /tmp/tool
```

> [!NOTE]
> Test the Docker build locally before submitting!

## Code Review Process

1. **Automated checks** run first (linters, tests)
2. **Maintainer review** - we'll provide feedback
3. **Address feedback** - update your PR as needed
4. **Approval & merge** - once everything looks good!

> [!TIP]
> Don't worry if you need to make changes - it's a normal part of the process!

## Need Help?

- 💬 **Questions?** Open a [Discussion](../../discussions)
- 🐛 **Found a bug?** Open an [Issue](../../issues)
- 💡 **Ideas?** We'd love to hear them in Discussions!

## Recognition

> [!NOTE]
> All contributors will be recognized in our [Contributors](../../graphs/contributors) page and in release notes!

---

**Thank you for contributing! 🎉**

Your efforts help make this tool better for the entire security and CTF community!
