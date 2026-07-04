"""End-to-end tests exercising every analyzer through the running web app.

Unlike ``test_analyzers.py`` (which calls analyzers in-process), these drive
the real HTTP path: upload -> RQ worker runs the actual tool binary -> poll
status -> read results. They therefore need the Docker stack running
(``docker compose up``) with Redis, Postgres, the worker and all tool
binaries. When no server is reachable the whole module is skipped, so the
unit test run in CI stays green.

Point the tests at a server with ``APERISOLVE_BASE_URL`` (default
``http://localhost:5000``).

Each password/extraction analyzer has a purpose-built fixture in
``tests/fixtures/`` that actually contains hidden data (generated with the
tool itself and round-trip verified), so a healthy analyzer returns
``status == "ok"`` rather than the "found nothing" error a clean image gives.
"""

import os
import time
from dataclasses import dataclass
from pathlib import Path

import pytest
import requests

from aperisolve.analyzers.registry import tool_order

BASE_URL = os.environ.get("APERISOLVE_BASE_URL", "http://localhost:5000").rstrip("/")
REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "tests" / "fixtures"
PLAIN_IMAGE = REPO_ROOT / "examples" / "example1.png"
STEGO_PASSWORD = "s3cret"  # noqa: S105 — the passphrase baked into the fixtures

RESULT_TIMEOUT_SECONDS = 120
POLL_INTERVAL_SECONDS = 2
CRASH_MARKERS = ("Traceback", "command not found", "No such file", "NameError")


def _server_available() -> bool:
    try:
        requests.get(BASE_URL + "/", timeout=3)
    except requests.RequestException:
        return False
    return True


# Probe once at import; the integration test is gated on this, the coverage
# guard below is not (it is a pure registry check that runs in CI too).
_SERVER_UP = _server_available()
requires_server = pytest.mark.skipif(
    not _SERVER_UP,
    reason=f"AperiSolve server not reachable at {BASE_URL} (start the Docker stack)",
)


@dataclass(frozen=True)
class Upload:
    """A distinct upload: fixture image plus the options that shape analysis."""

    image: Path
    password: str | None = None
    deep: bool = False

    def key(self) -> tuple[str, str | None, bool]:
        """Cache key identifying this distinct upload."""
        return (str(self.image), self.password, self.deep)


# One Upload per distinct (image, password, deep). Several analyzers share the
# plain image; the password/extraction tools each get their own stego fixture.
PLAIN = Upload(PLAIN_IMAGE)
ZSTEG = Upload(FIXTURES / "zsteg_lsb.png")
POLYGLOT = Upload(FIXTURES / "polyglot_zip.png")
STEGHIDE = Upload(FIXTURES / "steghide.jpg", password=STEGO_PASSWORD)
JSTEG = Upload(FIXTURES / "jsteg.jpg")
OPENSTEGO = Upload(FIXTURES / "openstego.png", password=STEGO_PASSWORD)
JPSEEK = Upload(FIXTURES / "jphide.jpg", password=STEGO_PASSWORD)
OUTGUESS = Upload(FIXTURES / "outguess.jpg", password=STEGO_PASSWORD, deep=True)


@dataclass(frozen=True)
class AnalyzerCase:
    """Expected outcome for one analyzer given an upload."""

    name: str
    upload: Upload
    expect_download: bool = False


# Every analyzer, each with a fixture that should make it succeed.
CASES = [
    AnalyzerCase("decomposer", PLAIN),
    AnalyzerCase("color_remapping", PLAIN),
    AnalyzerCase("file", PLAIN),
    AnalyzerCase("exiftool", PLAIN),
    AnalyzerCase("identify", PLAIN),
    AnalyzerCase("strings", PLAIN),
    AnalyzerCase("pngcheck", PLAIN),
    AnalyzerCase("pcrt", PLAIN),
    AnalyzerCase("zsteg", ZSTEG),
    AnalyzerCase("binwalk", POLYGLOT, expect_download=True),
    AnalyzerCase("foremost", POLYGLOT, expect_download=True),
    AnalyzerCase("steghide", STEGHIDE, expect_download=True),
    AnalyzerCase("jsteg", JSTEG),
    AnalyzerCase("openstego", OPENSTEGO, expect_download=True),
    AnalyzerCase("jpseek", JPSEEK, expect_download=True),
    AnalyzerCase("outguess", OUTGUESS, expect_download=True),
]


def _upload(upload: Upload) -> str:
    with upload.image.open("rb") as handle:
        data = {"deep": "true" if upload.deep else "false"}
        if upload.password is not None:
            data["password"] = upload.password
        response = requests.post(
            BASE_URL + "/upload",
            files={"image": (upload.image.name, handle)},
            data=data,
            timeout=30,
        )
    response.raise_for_status()
    return response.json()["submission_hash"]


def _wait_for_results(submission_hash: str) -> dict:
    deadline = time.monotonic() + RESULT_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        status = requests.get(f"{BASE_URL}/status/{submission_hash}", timeout=10).json()["status"]
        if status == "completed":
            result = requests.get(f"{BASE_URL}/result/{submission_hash}", timeout=10)
            return result.json()["results"]
        if status == "error":
            pytest.fail(f"submission {submission_hash} failed with status 'error'")
        time.sleep(POLL_INTERVAL_SECONDS)
    pytest.fail(f"submission {submission_hash} did not complete within {RESULT_TIMEOUT_SECONDS}s")
    raise AssertionError  # unreachable, keeps type checkers happy


# Cache results per distinct upload so N analyzers sharing an image cause one
# upload+analysis, not N. Populated lazily by the fixture below.
_results_cache: dict[tuple[str, str | None, bool], dict] = {}


@pytest.fixture
def results_for(request: pytest.FixtureRequest) -> dict:
    """Return (and cache) the analysis results for an upload (indirect param)."""
    upload: Upload = request.param
    key = upload.key()
    if key not in _results_cache:
        _results_cache[key] = _wait_for_results(_upload(upload))
    return _results_cache[key]


@requires_server
@pytest.mark.parametrize(
    ("case", "results_for"),
    [(case, case.upload) for case in CASES],
    ids=[case.name for case in CASES],
    indirect=["results_for"],
)
def test_analyzer_works_through_webapp(case: AnalyzerCase, results_for: dict) -> None:
    """Each analyzer runs via the web app and reports a successful result."""
    assert case.name in results_for, (
        f"{case.name} produced no result entry (not registered, binary missing, "
        f"or the worker thread crashed). Present: {sorted(results_for)}"
    )
    entry = results_for[case.name]

    payload = str(entry.get("error", "")) + str(entry.get("output", ""))
    for marker in CRASH_MARKERS:
        assert marker not in payload, f"{case.name} looks like it crashed: {entry}"

    assert entry.get("status") == "ok", f"{case.name} did not succeed: {entry}"

    if case.expect_download:
        download = entry.get("download", "")
        assert download.endswith(f"/{case.name}"), (
            f"{case.name} should expose a downloadable archive: {entry}"
        )


def test_all_analyzers_are_covered() -> None:
    """Guard: every registered analyzer has a web-app test case."""
    assert set(tool_order()) == {case.name for case in CASES}
