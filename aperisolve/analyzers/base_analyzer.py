# flake8: noqa: E203,E501,W503
# pylint: disable=C0413,W0718,W0613,R0903,R0801
# mypy: disable-error-code=unused-awaitable
"""Base Analyzer class for image analysis tools."""

import fcntl
import json
import os
import subprocess
import threading
from abc import ABC
from pathlib import Path
from shutil import rmtree
from typing import Any, Optional, overload

_thread_lock = threading.Lock()
MAX_PENDING_TIME = int(os.getenv("MAX_PENDING_TIME", "600"))  # 10 minutes by default


class SubprocessAnalyzer(ABC):
    """Analyzer that runs a subprocess command."""

    name: str
    input_img: Path
    output_dir: Path
    has_archive: bool
    cmd: list[str] | None = None
    img: str
    make_folder: bool = True

    def __init__(self, name: str, input_img: Path, output_dir: Path, has_archive: bool = False):
        self.name = name
        self.input_img = input_img
        self.img = f"../{self.input_img.name}"
        self.output_dir = output_dir
        self.has_archive = has_archive

    def run_command(
        self, cmd: list[str], cwd: Optional[Path] = None
    ) -> subprocess.CompletedProcess[str]:
        """Run a subprocess command."""
        return subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=MAX_PENDING_TIME,
        )

    def generate_archive(self, output_dir: Path, extracted_dir: Path) -> str:
        """Zip the extracted files and remove the directory."""
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

        with _thread_lock:  # synchronizes across threads
            with open(lock_file, "w", encoding="utf-8") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)  # synchronizes across processes

                try:
                    # Read existing JSON
                    data: dict[Any, Any] = {}
                    if json_file.exists():
                        try:
                            with open(json_file, "r", encoding="utf-8") as f:
                                data = json.load(f)
                        except json.JSONDecodeError:
                            data = {}

                    # Update with new data
                    data.update(new_data)

                    # Write safely to a temp file
                    with open(tmp_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, sort_keys=False)

                    os.replace(tmp_file, json_file)  # ensures file write is atomic
                finally:
                    fcntl.flock(lock, fcntl.LOCK_UN)

    def get_extracted_dir(self) -> Path:
        """Get the extracted directory path. Can be overridden but work as it is."""
        return self.output_dir / self.name

    @overload
    def build_cmd(self) -> list[str]: ...

    @overload
    def build_cmd(self, password: str) -> list[str]: ...

    def build_cmd(self, password: Optional[str] = None) -> list[str]:
        """Build the command to run. Can be overridden."""
        if self.cmd is None:
            raise NotImplementedError("cmd must be set or build_cmd overridden")
        return self.cmd

    def get_results(self, password: Optional[str] = None) -> dict[str, Any]:
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

        zip_exist = False
        if extracted_dir and extracted_dir.exists() and any(extracted_dir.iterdir()):
            self.generate_archive(self.output_dir, extracted_dir)  # keep archive
            zip_exist = True

        if self.is_error(returncode, stdout, stderr, zip_exist):
            result = {
                "status": "error",
            }
            result["error"] = self.process_error(stdout, stderr)
        else:
            result = {
                "status": "ok",
                "output": self.process_output(stdout, stderr),
            }
            note: Optional[str] = self.process_note(stdout, stderr)
            if note:
                result["note"] = note
            if zip_exist:
                result["download"] = f"/download/{self.output_dir.name}/{self.name}"
        return result

    @overload
    def analyze(self) -> None: ...

    @overload
    def analyze(self, password: str) -> None: ...

    def analyze(self, password: Optional[str] = None) -> None:
        """Run the subprocess command and handle results."""
        result: dict[str, Any]
        try:
            result = self.get_results(password)
            self.update_result(result)
        except Exception as e:
            self.update_result({"status": "error", "error": str(e)})

    def is_error(self, returncode: int, stdout: str, stderr: str, zip_exist: bool) -> bool:
        """Check if the result is an error."""
        return len(stderr) > 0

    def process_output(self, stdout: str, stderr: str) -> str | list[str] | dict[str, str]:
        """Process the stdout into a list of lines."""
        return [line for line in stdout.split("\n") if line] if stdout else []

    def process_error(self, stdout: str, stderr: str) -> str:
        """Process the stderr."""
        return stderr

    def process_note(self, stdout: str, stderr: str) -> Optional[str]:
        """Process the stdout for informational purposes."""
        return None
