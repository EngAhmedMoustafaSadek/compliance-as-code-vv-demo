"""Build traceability evidence from test results and enforce the verification gate.

Inputs
  regulatory/requirements.yaml   software requirements
  regulatory/risks.yaml          hazards and risk controls (ISO 14971 style)
  reports/results.json           written by the pytest plugin in tests/conftest.py
  reports/llm_review.json        optional, advisory only (tools/llm_review.py)

Outputs (reports/)
  traceability_matrix.md / .csv  requirement -> tests -> result, hazard -> control -> requirement
  verification_report.md         summary, per-requirement results, anomalies, sign-off block

Exit code 1 when the gate fails, so CI blocks the change.
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
VERIFIED, FAILED, NOT_VERIFIED = "VERIFIED", "FAILED", "NOT VERIFIED"


def load_inputs(root: Path):
    reqs = yaml.safe_load((root / "regulatory" / "requirements.yaml").read_text())
    risks = yaml.safe_load((root / "regulatory" / "risks.yaml").read_text())
    results_path = root / "reports" / "results.json"
    if not results_path.exists():
        sys.exit("reports/results.json not found. Run pytest first.")
    results = json.loads(results_path.read_text())
    review_path = root / "reports" / "llm_review.json"
    review = json.loads(review_path.read_text()) if review_path.exists() else None
    return reqs, risks, results, review


def status_of(tests):
    if any(t["outcome"] == "failed" for t in tests):
        return FAILED
    if any(t["outcome"] == "passed" for t in tests):
        return VERIFIED
    return NOT_VERIFIED


def analyse(reqs, risks, results):
    tests = results["tests"]
    requirements = {r["id"]: r for r in reqs["requirements"]}
    controls = {c["id"]: c for c in risks["risk_controls"]}
    problems = []

    req_rows = []
    for rid, req in requirements.items():
        linked = [t for t in tests if rid in t["requirements"]]
        status = status_of(linked)
        req_rows.append({"id": rid, "title": req["title"], "tests": linked, "status": status})
        if status != VERIFIED:
            problems.append(f"{rid} ({req['title']}) is {status}")
    req_status = {row["id"]: row["status"] for row in req_rows}

    rc_rows = []
    for hazard in risks["hazards"]:
        if not hazard.get("risk_controls"):
            problems.append(f"{hazard['id']} has no risk control")
        for cid in hazard.get("risk_controls", []):
            control = controls.get(cid)
            if control is None:
                problems.append(f"{hazard['id']} references unknown risk control {cid}")
                continue
            linked_reqs = control.get("requirements", [])
            unknown = [r for r in linked_reqs if r not in requirements]
            for r in unknown:
                problems.append(f"{cid} references unknown requirement {r}")
            ok = linked_reqs and not unknown and all(req_status[r] == VERIFIED for r in linked_reqs)
            status = VERIFIED if ok else NOT_VERIFIED
            if not ok:
                problems.append(f"{cid} ({hazard['id']}) is {status}")
            rc_rows.append({"hazard": hazard, "control": control, "status": status})

    for t in tests:
        for rid in t["requirements"]:
            if rid not in requirements:
                problems.append(f"test {t['test']} is tagged with unknown requirement {rid}")
        for cid in t["risk_controls"]:
            if cid not in controls:
                problems.append(f"test {t['test']} is tagged with unknown risk control {cid}")

    anomalies = [t for t in tests if t["outcome"] == "failed"]
    untraced = [t for t in tests if not t["requirements"]]
    return req_rows, rc_rows, anomalies, untraced, sorted(set(problems))


def short(test_id: str) -> str:
    return test_id.split("::", 1)[-1]


def write_matrix(out: Path, req_rows, rc_rows):
    lines = [
        "# Traceability Matrix",
        "",
        "## Requirements to tests",
        "",
        "| Requirement | Title | Tests | Result |",
        "|---|---|---|---|",
    ]
    for row in req_rows:
        tests = "<br>".join(f"{short(t['test'])} ({t['outcome']})" for t in row["tests"]) or "none"
        lines.append(f"| {row['id']} | {row['title']} | {tests} | **{row['status']}** |")
    lines += [
        "",
        "## Hazards to risk controls to requirements",
        "",
        "| Hazard | Hazardous situation | Risk control | Requirements | Result |",
        "|---|---|---|---|---|",
    ]
    for row in rc_rows:
        h, c = row["hazard"], row["control"]
        lines.append(
            f"| {h['id']} | {h['hazardous_situation']} | {c['id']}: {c['description']} | "
            f"{', '.join(c['requirements'])} | **{row['status']}** |"
        )
    (out / "traceability_matrix.md").write_text("\n".join(lines) + "\n")

    with (out / "traceability_matrix.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["requirement", "title", "test", "outcome", "requirement_status"])
        for row in req_rows:
            for t in row["tests"] or [{"test": "", "outcome": ""}]:
                writer.writerow([row["id"], row["title"], t["test"], t["outcome"], row["status"]])


def write_report(out: Path, reqs, results, req_rows, rc_rows, anomalies, untraced, problems, review):
    tests = results["tests"]
    counts = {k: sum(t["outcome"] == k for t in tests) for k in ("passed", "failed", "skipped")}
    verdict = "PASS" if not problems else "FAIL"
    lines = [
        "# Software Verification Report",
        "",
        "_Generated automatically by CI. Demo project: synthetic module, not a medical device._",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Software | {results['software']} {results['software_version']} |",
        f"| Commit | `{results['git_commit']}` |",
        f"| Generated | {results['generated_utc']} |",
        f"| Environment | Python {results['python']}, pytest {results['pytest']}, {results['platform']} |",
        f"| Software safety class | IEC 62304 Class {reqs.get('safety_class', '?')} (assumed for demo) |",
        "",
        f"## Gate result: {verdict}",
        "",
        f"- Requirements verified: {sum(r['status'] == VERIFIED for r in req_rows)} of {len(req_rows)}",
        f"- Risk controls verified: {sum(r['status'] == VERIFIED for r in rc_rows)} of {len(rc_rows)}",
        f"- Tests: {len(tests)} run, {counts['passed']} passed, {counts['failed']} failed, {counts['skipped']} skipped",
    ]
    if problems:
        lines += ["", "Blocking findings:", ""] + [f"- {p}" for p in problems]
    lines += [
        "",
        "## Requirement verification",
        "",
        "| Requirement | Title | Tests (passed/total) | Result |",
        "|---|---|---|---|",
    ]
    for row in req_rows:
        passed = sum(t["outcome"] == "passed" for t in row["tests"])
        lines.append(f"| {row['id']} | {row['title']} | {passed}/{len(row['tests'])} | {row['status']} |")
    lines += [
        "",
        "## Risk control verification",
        "",
        "| Hazard | Risk control | Requirements | Result |",
        "|---|---|---|---|",
    ]
    for row in rc_rows:
        c = row["control"]
        lines.append(f"| {row['hazard']['id']} | {c['id']} | {', '.join(c['requirements'])} | {row['status']} |")
    lines += ["", "## Anomalies", ""]
    if anomalies:
        lines += ["| Test | Requirements | Message |", "|---|---|---|"]
        lines += [f"| {short(t['test'])} | {', '.join(t['requirements'])} | {t['message']} |" for t in anomalies]
    else:
        lines.append("None.")
    if untraced:
        lines += ["", "## Tests not linked to a requirement", ""]
        lines += [f"- {short(t['test'])}" for t in untraced]
    lines += ["", "## Advisory LLM review (not verification evidence)", ""]
    if review and review.get("status") == "completed":
        lines.append(f"Model: {review['model']}. Findings are for human review and do not affect the gate.")
        lines += ["", "| Requirement | Verdict | Notes |", "|---|---|---|"]
        lines += [f"| {f['requirement']} | {f['verdict']} | {f['notes']} |" for f in review["findings"]]
    else:
        reason = review.get("reason", "not run") if review else "not run"
        lines.append(f"Skipped: {reason}.")
    lines += [
        "",
        "## Approval",
        "",
        "| Role | Name | Signature | Date |",
        "|---|---|---|---|",
        "| Prepared by | CI pipeline (automated) | n/a | " + results["generated_utc"][:10] + " |",
        "| Reviewed by |  |  |  |",
        "| Approved by |  |  |  |",
    ]
    (out / "verification_report.md").write_text("\n".join(lines) + "\n")
    return verdict, counts


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()

    reqs, risks, results, review = load_inputs(args.root)
    req_rows, rc_rows, anomalies, untraced, problems = analyse(reqs, risks, results)
    out = args.root / "reports"
    write_matrix(out, req_rows, rc_rows)
    verdict, counts = write_report(out, reqs, results, req_rows, rc_rows, anomalies, untraced, problems, review)

    summary = (
        f"Verification gate: {verdict} | requirements "
        f"{sum(r['status'] == VERIFIED for r in req_rows)}/{len(req_rows)} verified | risk controls "
        f"{sum(r['status'] == VERIFIED for r in rc_rows)}/{len(rc_rows)} verified | tests "
        f"{counts['passed']} passed, {counts['failed']} failed"
    )
    print(summary)
    for p in problems:
        print(f"  BLOCKING: {p}")

    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a") as f:
            f.write((out / "verification_report.md").read_text())

    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
