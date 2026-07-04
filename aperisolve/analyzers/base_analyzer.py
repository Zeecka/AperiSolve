"""Base Analyzer class for image analysis tools."""

import asyncio
import fcntl
import json
import threading
from abc import ABC
from pathlib import Path
from shutil import rmtree
from subprocess import CompletedProcess
from typing import Any, ClassVar, overload

from aperisolve.config import SUBPROCESS_TIMEOUT

_thread_lock = threading.Lock()

# Bytes kept from each of a subprocess's stdout/stderr. Output beyond this is
# drained (so the child never blocks on a full pipe) but discarded, keeping
# adversarial tool output from ballooning memory and results.json.
MAX_CAPTURED_OUTPUT = 1_000_000

# All concrete analyzer classes, registered automatically on class creation.
# Use aperisolve.analyzers.registry to consume this (it imports every module).
REGISTRY: list[type["SubprocessAnalyzer"]] = []


class SubprocessAnalyzer(ABC):
    """Analyzer that runs a subprocess command.

    Subclasses declare their behavior with class attributes; creating the class
    is enough to register it — no other file needs to change:

    - ``name``: tool name, used as the ``results.json`` key and download URL.
    - ``has_archive``: the tool extracts files zipped into ``<name>.7z``.
    - ``needs_password``: the tool receives the submission password.
    - ``deep_only``: only run when the user requests a deep analysis.
    - ``display_order``: frontend rendering position (lower renders first).
    - ``register``: opt-out flag for templates/abstract intermediates.
    """

    name: ClassVar[str]
    has_archive: ClassVar[bool] = False
    needs_password: ClassVar[bool] = False
    deep_only: ClassVar[bool] = False
    display_order: ClassVar[int] = 1000
    register: ClassVar[bool] = True
    # Tools with several command variants (e.g. OpenStego's two crypt
    # algorithms) set this >1; ``analyze`` re-runs ``get_results`` while the
    # previous attempt errored, and ``build_cmd`` supplies the next variant.
    max_attempts: ClassVar[int] = 1

    input_img: Path
    output_dir: Path
    cmd: list[str] | None = None
    img: str
    make_folder: bool = True

    def __init_subclass__(cls, **kwargs: Any) -> None:  # noqa: ANN401
        """Register concrete analyzer subclasses declaring a ``name``."""
        super().__init_subclass__(**kwargs)
        if cls.register and getattr(cls, "name", None):
            REGISTRY.append(cls)

    def __init__(self, input_img: Path, output_dir: Path) -> None:
        """Initialize analyzer execution context."""
        self.input_img = input_img
        self.img = f"../{self.input_img.name}"
        self.output_dir = output_dir

    @classmethod
    def execute(cls, input_img: Path, output_dir: Path, password: str | None = None) -> None:
        """Instantiate and run this analyzer, applying the password if supported."""
        analyzer = cls(input_img, output_dir)
        if cls.needs_password and password:
            analyzer.analyze(password)
        else:
            analyzer.analyze()

    def run_command(
        self,
        cmd: list[str],
        cwd: Path | None = None,
    ) -> CompletedProcess[str]:
        """Run a subprocess command."""

        async def _read_capped(stream: asyncio.StreamReader) -> str:
            chunks: list[bytes] = []
            total = 0
            truncated = False
            while chunk := await stream.read(65536):
                take = chunk[: max(0, MAX_CAPTURED_OUTPUT - total)]
                if take:
                    chunks.append(take)
                    total += len(take)
                if len(take) < len(chunk):
                    truncated = True
            text = b"".join(chunks).decode("utf-8", errors="replace")
            if truncated:
                text += "\n[output truncated]"
            return text

        async def _run() -> CompletedProcess[str]:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(cwd) if cwd is not None else None,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            if process.stdout is None or process.stderr is None:
                msg = "Subprocess pipes were not created"
                raise RuntimeError(msg)
            try:
                stdout, stderr, _ = await asyncio.wait_for(
                    asyncio.gather(
                        _read_capped(process.stdout),
                        _read_capped(process.stderr),
                        process.wait(),
                    ),
                    timeout=SUBPROCESS_TIMEOUT,
                )
            except TimeoutError:
                process.kill()
                await process.wait()
                msg = f"Command timed out after {SUBPROCESS_TIMEOUT}s: {cmd[0]}"
                raise TimeoutError(msg) from None
            returncode = process.returncode
            if returncode is None:
                msg = "Subprocess exited without a return code"
                raise RuntimeError(msg)
            return CompletedProcess(
                args=cmd,
                returncode=returncode,
                stdout=stdout,
                stderr=stderr,
            )

        return asyncio.run(_run())

    def generate_archive(self, extracted_dir: Path | None = None) -> str:
        """Zip the extracted files and remove the directory."""
        if extracted_dir is None:
            extracted_dir = self.get_extracted_dir()
        zip_data = self.run_command(["7z", "a", f"../{self.name}.7z", "*"], cwd=extracted_dir)
        rmtree(extracted_dir)
        return zip_data.stderr

    def update_result(self, result: dict[str, Any]) -> None:
        """Thread-safe and process-safe JSON update using lock file and atomic replace."""
        json_file = self.output_dir / "results.json"
        new_data = {self.name: result}
        lock_file = json_file.with_suffix(json_file.suffix + ".lock")
        tmp_file = json_file.with_suffix(json_file.suffix + ".tmp")

        json_file.parent.mkdir(parents=True, exist_ok=True)

        with _thread_lock, lock_file.open("w", encoding="utf-8") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)  # synchronizes across processes

            try:
                # Read existing JSON
                data: dict[Any, Any] = {}
                if json_file.exists():
                    try:
                        with json_file.open(encoding="utf-8") as f:
                            data = json.load(f)
                    except json.JSONDecodeError:
                        data = {}

                # Update with new data
                data.update(new_data)

                # Write safely to a temp file
                with tmp_file.open("w", encoding="utf-8") as f:
                    json.dump(data, f, sort_keys=False)

                tmp_file.replace(json_file)  # ensures file write is atomic
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def get_extracted_dir(self) -> Path:
        """Get the extracted directory path. Can be overridden but work as it is."""
        return self.output_dir / self.name

    @overload
    def build_cmd(self) -> list[str]: ...

    @overload
    def build_cmd(self, password: str) -> list[str]: ...

    def build_cmd(self, password: str | None = None) -> list[str]:
        """Build the command to run. Can be overridden."""
        _ = password
        if self.cmd is None:
            msg = "cmd must be set or build_cmd overridden"
            raise NotImplementedError(msg)
        return self.cmd

    def get_results(self, password: str | None = None) -> dict[str, Any]:
        """Get results of command before returning."""
        result: dict[str, Any]
        extracted_dir = None
        if self.has_archive:
            extracted_dir = self.get_extracted_dir()
            if self.make_folder:
                extracted_dir.mkdir(parents=True, exist_ok=True)

        cmd: list[str]
        if password:
            cmd = list(map(str, self.build_cmd(password)))
        else:
            cmd = list(map(str, self.build_cmd()))
        data = self.run_command(cmd, cwd=self.output_dir)
        returncode = data.returncode
        stderr = data.stderr
        stdout = data.stdout

        zip_exists = False
        if extracted_dir and extracted_dir.exists() and any(extracted_dir.iterdir()):
            self.generate_archive(extracted_dir)  # keep archive
            zip_exists = True

        if self.is_error(returncode, stdout, stderr, zip_exist=zip_exists):
            result = {
                "status": "error",
            }
            result["error"] = self.process_error(stdout, stderr)
        else:
            result = {
                "status": "ok",
                "output": self.process_output(stdout, stderr),
            }
            note: str | None = self.process_note(stdout, stderr)
            if note:
                result["note"] = note
            if zip_exists:
                result["download"] = f"/download/{self.output_dir.name}/{self.name}"
        return result

    @overload
    def analyze(self) -> None: ...

    @overload
    def analyze(self, password: str) -> None: ...

    def analyze(self, password: str | None = None) -> None:
        """Run the subprocess command and handle results."""
        result: dict[str, Any]
        try:
            result = self.get_results(password)
            for _ in range(1, self.max_attempts):
                if result["status"] != "error":
                    break
                result = self.get_results(password)
            self.update_result(result)
        except (RuntimeError, ValueError, OSError, TimeoutError) as e:
            self.update_result({"status": "error", "error": str(e)})
            raise

    def is_error(self, returncode: int, stdout: str, stderr: str, *, zip_exist: bool) -> bool:
        """Check if the result is an error."""
        _ = returncode, stdout, zip_exist
        return len(stderr) > 0

    def process_output(self, stdout: str, stderr: str) -> str | list[str] | dict[str, str]:
        """Process the stdout into a list of lines."""
        _ = stderr
        return [line for line in stdout.split("\n") if line] if stdout else []

    def process_error(self, stdout: str, stderr: str) -> str:
        """Process the stderr."""
        _ = stdout
        return stderr

    def process_note(self, stdout: str, stderr: str) -> str | None:
        """Process the stdout for informational purposes."""
        _ = stdout, stderr
        return None
