# Adding a New Analyzer

This guide shows you how to add a new image analysis tool to the system.

## Quick Start

1. Create a new file in `analyzers/` from template file `template_analyzer.py`.
2. Register it in `workers.py`

## Basic Template

```python
from pathlib import Path
from typing import Optional
from .base_analyzer import SubprocessAnalyzer

class MyToolAnalyzer(SubprocessAnalyzer):
    def __init__(self, input_img: Path, output_dir: Path) -> None:
        super().__init__("mytool", input_img, output_dir)
        self.cmd = ["mytool", self.img]

def analyze_mytool(input_img: Path, output_dir: Path) -> None:
    analyzer = MyToolAnalyzer(input_img, output_dir)
    analyzer.analyze()
```

You can also see `template_analyzer.py`.

## Common Scenarios

### Simple Text Output Tool

Like `strings` or `exiftool` - just reads the file and outputs text:

```python
class StringsAnalyzer(SubprocessAnalyzer):
    def __init__(self, input_img: Path, output_dir: Path) -> None:
        super().__init__("strings", input_img, output_dir)
        self.cmd = ["strings", self.img]
```

### Tool That Extracts Files

Like `binwalk` or `foremost` - extracts files that get zipped for download:

```python
class ForemostAnalyzer(SubprocessAnalyzer):
    def __init__(self, input_img: Path, output_dir: Path) -> None:
        super().__init__("foremost", input_img, output_dir, has_archive=True)
        self.cmd = ["foremost", "-o", str(self.get_extracted_dir()), "-i", self.img]
```

Note the `has_archive=True` parameter.

### Tool With Password Support

Like `steghide` or `openstego`:

```python
class OutguessAnalyzer(SubprocessAnalyzer):
    def __init__(self, input_img: Path, output_dir: Path) -> None:
        super().__init__("outguess", input_img, output_dir, has_archive=True)

    def build_cmd(self, password: Optional[str] = None) -> list[str]:
        out = str(self.get_extracted_dir() / "outguess.data")
        if password:
            return ["outguess", "-k", password, "-r", self.img, out]
        return ["outguess", "-r", self.img, out]

def analyze_outguess(input_img: Path, output_dir: Path, password: Optional[str] = None) -> None:
    analyzer = OutguessAnalyzer(input_img, output_dir)
    if password:
        analyzer.analyze(password)
    else:
        analyzer.analyze()
```

## Customizing Behavior

### Custom Error Detection

Override `is_error()` to define what counts as an error:

```python
def is_error(self, returncode: int, stdout: str, stderr: str, zip_exist: bool) -> bool:
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

## Registering Your Analyzer

Add it to `workers.py` in the `analyze_image` function:

```python
# Import at the top
from .analyzers.mytool import analyze_mytool

# Add to analyzers list
analyzers = [
    (analyze_binwalk, img_path, result_path),
    (analyze_exiftool, img_path, result_path),
    # ... other analyzers ...
    (analyze_mytool, img_path, result_path),
]

# If it needs a password, pass submission.password:
# (analyze_mytool, img_path, result_path, submission.password),

# If only for deep analysis, add it conditionally:
if submission.deep_analysis:
    analyzers.extend([
        (analyze_mytool, img_path, result_path),
    ])
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

## Tips

- Use `self.img` in commands (relative path), not `self.input_img`
- Set `has_archive=True` if your tool extracts files
- Tools run in parallel threads - no need to worry about concurrency
- The base class handles timeouts (10 minutes default)
- Extracted files are automatically zipped into `.7z` archives
- All exceptions are caught and logged to Sentry

## Example: Complete Analyzer

```python
from pathlib import Path
from .base_analyzer import SubprocessAnalyzer

class PngcheckAnalyzer(SubprocessAnalyzer):
    def __init__(self, input_img: Path, output_dir: Path) -> None:
        super().__init__("pngcheck", input_img, output_dir)
        self.cmd = ["pngcheck", "-v", self.img]

    def is_error(self, returncode: int, stdout: str, stderr: str, zip_exist: bool) -> bool:
        return "this is neither a PNG or JNG image" in stdout

    def process_error(self, stdout: str, stderr: str) -> str:
        if "neither a PNG or JNG" in stdout:
            return "File format not supported (PNG/JNG only)"
        return stdout

def analyze_pngcheck(input_img: Path, output_dir: Path) -> None:
    analyzer = PngcheckAnalyzer(input_img, output_dir)
    analyzer.analyze()
```

That's it! Your analyzer will now run in parallel with the others and results will appear in the web interface.
