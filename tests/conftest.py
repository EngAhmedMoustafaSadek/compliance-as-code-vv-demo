"""Traceability plugin.

1. Turns Gherkin tags like @REQ-002 and @RC-04 into pytest markers
   (req("REQ-002"), rc("RC-04")), so BDD scenarios and plain unit tests are
   linked to requirements the same way.
2. Records every test's outcome with its linked requirements and risk controls,
   and writes reports/results.json at the end of the run. tools/trace.py turns that
   file into the traceability matrix, the verification report and the gate result.
"""

import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone

import pytest

_records: dict[str, dict] = {}


def pytest_bdd_apply_tag(tag, function):
    for prefix, mark in (("REQ-", pytest.mark.req), ("RC-", pytest.mark.rc)):
        if tag.startswith(prefix):
            mark(tag)(function)
            return True
    return None


def _ids(item, name):
    return sorted({arg for marker in item.iter_markers(name) for arg in marker.args})


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    record = _records.setdefault(
        item.nodeid,
        {
            "test": item.nodeid,
            "requirements": _ids(item, "req"),
            "risk_controls": _ids(item, "rc"),
            "outcome": "passed",
            "duration_s": 0.0,
            "message": "",
        },
    )
    record["duration_s"] = round(record["duration_s"] + report.duration, 4)
    if report.failed:
        record["outcome"] = "failed"
        lines = [line for line in report.longreprtext.strip().splitlines() if line.strip()]
        record["message"] = lines[-1][:300] if lines else "failed"
    elif report.skipped and record["outcome"] != "failed":
        record["outcome"] = "skipped"


def _git_commit():
    if os.environ.get("GITHUB_SHA"):
        return os.environ["GITHUB_SHA"]
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "uncommitted"


def pytest_sessionfinish(session, exitstatus):
    import pulsesig

    report_dir = session.config.rootpath / "reports"
    report_dir.mkdir(exist_ok=True)
    data = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "software": "pulsesig",
        "software_version": pulsesig.__version__,
        "git_commit": _git_commit(),
        "python": sys.version.split()[0],
        "pytest": pytest.__version__,
        "platform": platform.platform(),
        "tests": sorted(_records.values(), key=lambda r: r["test"]),
    }
    (report_dir / "results.json").write_text(json.dumps(data, indent=2))
