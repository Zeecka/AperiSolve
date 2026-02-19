"""Base Analyzer class for image analysis tools."""

import asyncio
import fcntl
import json
import threading
from abc import ABC
from pathlib import Path
from shutil import rmtree
from subprocess import CompletedProcess
from typing import Any, overload

from aperisolve.config import MAX_PENDING_TIME

_thread_lock = threading.Lock()


class SubprocessAnalyzer(ABC):
    """Analyzer that runs a subprocess command."""

    name: str
    input_img: Path
    output_dir: Path
    has_archive: bool
    cmd: list[str] | None = None
    img: str
    make_folder: bool = True

    def __init__(
        self,
        name: str,
        input_img: Path,
        output_dir: Path,
        *,
        has_archive: bool = False,
    ) -> None:
        """Initialize analyzer metadata and execution context."""
        self.name = name
        self.input_img = input_img
        self.img = f"../{self.input_img.name}"
        self.output_dir = output_dir
        self.has_archive = has_archive

    def run_command(
        self,
        cmd: list[str],
        cwd: Path | None = None,
    ) -> CompletedProcess[str]:
        """Run a subprocess command."""

        async def _run() -> CompletedProcess[str]:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(cwd) if cwd is not None else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_raw, stderr_raw = await asyncio.wait_for(
                process.communicate(),
                timeout=MAX_PENDING_TIME,
            )
            returncode = process.returncode
            if returncode is None:
                msg = "Subprocess exited without a return code"
                raise RuntimeError(msg)
            return CompletedProcess(
                args=cmd,
                returncode=returncode,
                stdout=stdout_raw.decode("utf-8", errors="replace"),
                stderr=stderr_raw.decode("utf-8", errors="replace"),
            )

        return asyncio.run(_run())

    def generate_archive(self, _output_dir: Path, extracted_dir: Path | None = None) -> str:
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
            self.generate_archive(self.output_dir, extracted_dir)  # keep archive
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
