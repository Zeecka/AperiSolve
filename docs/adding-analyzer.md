# Adding a New Analyzer

This guide shows you how to add a new image analysis tool to the system.

## Quick Start

1. Create one file in `analyzers/` (copy `template_analyzer.py`).
2. Install the tool in the `Dockerfile` if it is an external binary.

That's it. Analyzers are auto-discovered: every `SubprocessAnalyzer` subclass
in `aperisolve/analyzers/` registers itself. The worker run list, the
`/download` allow-list and the frontend rendering order are all derived from
the class attributes — there is nothing to edit in `workers.py`, `config.py`
or `aperisolve.js`.

## Basic Template

```python
from .base_analyzer import SubprocessAnalyzer

class MyToolAnalyzer(SubprocessAnalyzer):
    """Analyzer for mytool."""

    name = "mytool"        # results.json key and download URL segment
    display_order = 165    # frontend position (lower renders first)

    def __init__(self, input_img, output_dir):
        super().__init__(input_img, output_dir)
        self.cmd = ["mytool", self.img]
```

You can also see `template_analyzer.py` or check real examples like
`jpseek.py`, `steghide.py`, or `strings.py`.

## Class Attributes

| Attribute | Default | Meaning |
|-----------|---------|---------|
| `name` | *(required)* | Tool name: `results.json` key, CSS class `a-<name>`, download URL |
| `has_archive` | `False` | The tool extracts files, zipped into `<name>.7z` and downloadable |
| `needs_password` | `False` | The tool receives the submission password in `build_cmd()` |
| `deep_only` | `False` | Only run when the user checks "Deep analysis" |
| `display_order` | `1000` | Frontend rendering position (existing tools use 10–160) |
| `register` | `True` | Set to `False` to keep a class out of the registry (templates) |

## Common Scenarios

### Simple Text Output Tool

Like `strings` or `exiftool` - just reads the file and outputs text:

```python
class StringsAnalyzer(SubprocessAnalyzer):
    name = "strings"
    display_order = 160

    def __init__(self, input_img, output_dir):
        super().__init__(input_img, output_dir)
        self.cmd = ["strings", self.img]
```

### Tool That Extracts Files

Like `binwalk` or `foremost` - extracts files that get zipped for download.
Set `has_archive = True`; the download route allow-list is derived from it
automatically:

```python
class ForemostAnalyzer(SubprocessAnalyzer):
    name = "foremost"
    has_archive = True
    display_order = 60

    def __init__(self, input_img, output_dir):
        super().__init__(input_img, output_dir)
        self.cmd = ["foremost", "-o", str(self.get_extracted_dir()), "-i", self.img]
```

### Tool With Password Support

Like `steghide` or `openstego`. Set `needs_password = True` and accept the
password in `build_cmd()`:

```python
class OutguessAnalyzer(SubprocessAnalyzer):
    name = "outguess"
    has_archive = True
    needs_password = True
    deep_only = True
    display_order = 70

    def build_cmd(self, password: str | None = None) -> list[str]:
        out = str(self.get_extracted_dir() / "outguess.data")
        if password:
            return ["outguess", "-k", password, "-r", self.img, out]
        return ["outguess", "-r", self.img, out]
```

> **Security note:** the password is user input. Always pass it as a separate
> argv element (never interpolate it into a shell string). See `jpseek.py`
> for a tool that needs an interactive prompt.

## Customizing Behavior

### Custom Error Detection

Override `is_error()` to define what counts as an error:

```python
def is_error(self, returncode: int, stdout: str, stderr: str, *, zip_exist: bool) -> bool:
    # Only error if no files were extracted
    return len(stderr) > 0 and not zip_exist
```

### Custom Output Formatting

Override `process_output()` to format the results:

```python
def process_output(self, stdout: str, stderr: str) -> dict[str, str]:
    # Parse into key-value pairs
    metadata = {}
    for line in stdout.split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()
    return metadata
```

### User-Friendly Error Messages

Override `process_error()` to provide helpful messages:

```python
def process_error(self, stdout: str, stderr: str) -> str:
    if "not supported" in stdout:
        return "This file format is not supported (PNG only)"
    return stderr
```

## Available Methods to Override

| Method | Purpose | Default Behavior |
|--------|---------|------------------|
| `build_cmd()` | Build command to run | Uses `self.cmd` |
| `is_error()` | Check if result is error | Returns `True` if stderr exists |
| `process_output()` | Format success output | Returns stdout as list of lines |
| `process_error()` | Format error message | Returns stderr as-is |
| `process_note()` | Add informational note | Returns `None` |
| `get_extracted_dir()` | Set extraction directory | Returns `output_dir/toolname/` |
| `get_results()` | Full control (in-process analyzers) | Runs the command pipeline |

## Output Format

Your analyzer produces JSON in `results.json`:

**Success:**
```json
{
  "mytool": {
    "status": "ok",
    "output": "Tool output here",
    "download": "/download/hash/mytool"
  }
}
```

**Error:**
```json
{
  "mytool": {
    "status": "error",
    "error": "Error message"
  }
}
```

## Tests

Add your analyzer's `name` to the expected registry list in
`tests/test_registry.py` (it asserts the exact set of registered analyzers
and their flags). If the tool is available on CI, consider a smoke test in
`tests/test_analyzers.py` running it against `examples/example1.png`.

## Tips

- Use `self.img` in commands (relative path), not `self.input_img`
- Set `has_archive = True` if your tool extracts files
- Tools run in parallel threads - no need to worry about concurrency
- The base class handles timeouts (10 minutes default)
- Extracted files are automatically zipped into `.7z` archives
- All exceptions are caught and logged to Sentry
- Keep analyzers idempotent and write outputs to the provided output directory
- Return structured JSON so the frontend can render links/downloads automatically

## Example: Complete Analyzer

```python
from .base_analyzer import SubprocessAnalyzer

class PngcheckAnalyzer(SubprocessAnalyzer):
    name = "pngcheck"
    display_order = 80

    def __init__(self, input_img, output_dir):
        super().__init__(input_img, output_dir)
        self.cmd = ["pngcheck", "-v", self.img]

    def is_error(self, returncode, stdout, stderr, *, zip_exist):
        return "this is neither a PNG or JNG image" in stdout

    def process_error(self, stdout, stderr):
        if "neither a PNG or JNG" in stdout:
            return "File format not supported (PNG/JNG only)"
        return stdout
```

That's it! Your analyzer will now run in parallel with the others and results will appear in the web interface.
