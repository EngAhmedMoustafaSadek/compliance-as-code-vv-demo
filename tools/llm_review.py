"""Advisory LLM review of test coverage against requirements.

Reads the requirements and every test file, asks Claude whether each requirement's
acceptance criteria are actually exercised (boundaries, every clause, negative cases),
and writes reports/llm_review.json and .md.

Advisory by design: LLM output is not reproducible, so it is never verification
evidence and never decides the gate. It points a human reviewer at weak spots.
Skips cleanly when ANTHROPIC_API_KEY is not set, so the pipeline runs without it.

Usage
  python tools/llm_review.py              run the review (needs ANTHROPIC_API_KEY)
  python tools/llm_review.py --dry-run    write the prompt to reports/llm_prompt.txt only
  python tools/llm_review.py --strict     exit 1 if any requirement is judged "missing"
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "claude-sonnet-5"

INSTRUCTIONS = """You are reviewing verification coverage for safety-critical medical device software.
For EACH requirement below, judge whether the tests linked to it (via @REQ-xxx tags or
pytest.mark.req("REQ-xxx")) actually exercise its acceptance criteria: every clause,
stated limits and boundaries, and relevant negative cases.

Answer with ONLY a JSON array, one object per requirement, no prose:
[{"requirement": "REQ-001", "verdict": "adequate" | "weak" | "missing", "notes": "<= 30 words"}]

- adequate: every clause is tested, including boundaries where the requirement states limits
- weak: linked tests exist but a clause, boundary or negative case is untested
- missing: no test meaningfully verifies the requirement
"""


def build_prompt(root: Path) -> str:
    parts = [INSTRUCTIONS, "\n## requirements.yaml\n", (root / "regulatory" / "requirements.yaml").read_text()]
    for path in sorted((root / "tests" / "features").glob("*.feature")):
        parts += [f"\n## {path.relative_to(root)}\n", path.read_text()]
    for path in sorted((root / "tests" / "unit").glob("test_*.py")):
        parts += [f"\n## {path.relative_to(root)}\n", path.read_text()]
    return "".join(parts)


def parse_findings(text: str) -> list[dict]:
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        raise ValueError("model reply did not contain a JSON array")
    findings = json.loads(match.group(0))
    for f in findings:
        if f.get("verdict") not in {"adequate", "weak", "missing"}:
            raise ValueError(f"unexpected verdict in {f}")
    return findings


def write(out: Path, review: dict):
    out.mkdir(exist_ok=True)
    (out / "llm_review.json").write_text(json.dumps(review, indent=2))
    lines = ["# Advisory LLM Coverage Review", "", "_Not verification evidence. For human review only._", ""]
    if review["status"] == "completed":
        lines += [f"Model: {review['model']}", "", "| Requirement | Verdict | Notes |", "|---|---|---|"]
        lines += [f"| {f['requirement']} | {f['verdict']} | {f['notes']} |" for f in review["findings"]]
    else:
        lines.append(f"Skipped: {review['reason']}.")
    (out / "llm_review.md").write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    out = args.root / "reports"
    prompt = build_prompt(args.root)
    model = os.environ.get("LLM_MODEL", DEFAULT_MODEL)

    if args.dry_run:
        out.mkdir(exist_ok=True)
        (out / "llm_prompt.txt").write_text(prompt)
        write(out, {"status": "skipped", "reason": "dry run, prompt written to reports/llm_prompt.txt"})
        print("Dry run: prompt written to reports/llm_prompt.txt")
        return
    if not os.environ.get("ANTHROPIC_API_KEY"):
        write(out, {"status": "skipped", "reason": "ANTHROPIC_API_KEY not set"})
        print("LLM review skipped: ANTHROPIC_API_KEY not set")
        return

    try:
        import anthropic

        client = anthropic.Anthropic()
        message = client.messages.create(
            model=model, max_tokens=2000, messages=[{"role": "user", "content": prompt}]
        )
        text = "".join(block.text for block in message.content if block.type == "text")
        findings = parse_findings(text)
    except Exception as exc:  # advisory step: never crash the pipeline
        write(out, {"status": "skipped", "reason": f"review failed: {type(exc).__name__}: {exc}"})
        print(f"LLM review failed, continuing: {exc}")
        return

    write(out, {"status": "completed", "model": model, "findings": findings})
    flagged = [f for f in findings if f["verdict"] != "adequate"]
    print(f"LLM review: {len(findings)} requirements reviewed, {len(flagged)} flagged for human review")
    for f in flagged:
        print(f"  {f['requirement']}: {f['verdict']} - {f['notes']}")
    if args.strict and any(f["verdict"] == "missing" for f in findings):
        sys.exit(1)


if __name__ == "__main__":
    main()
