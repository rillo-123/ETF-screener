from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path


def _latest_file(paths: list[Path]) -> Path | None:
    existing = [p for p in paths if p.exists()]
    if not existing:
        return None
    return max(existing, key=lambda p: p.stat().st_mtime)


def _resolve_quality_log(root: Path, logs_dir: Path, filename: str) -> Path | None:
    """Prefer logs/<file>, then fall back to repo-root <file> for compatibility."""
    candidates = [logs_dir / filename, root / filename]
    existing = [p for p in candidates if p.exists()]
    if not existing:
        return None
    return max(existing, key=lambda p: p.stat().st_mtime)


def _parse_pytest(log_text: str) -> dict[str, object]:
    summary_line = ""
    fail_ids: list[str] = []

    for line in log_text.splitlines():
        if line.startswith("FAILED ") or line.startswith("ERROR "):
            parts = line.split()
            if len(parts) >= 2:
                fail_ids.append(parts[1])
        if re.search(r"=+\s+.+\s+in\s+[0-9.]+s\s+=+", line):
            summary_line = line.strip()

    return {
        "summary": summary_line,
        "failures": sorted(set(fail_ids)),
    }


def _parse_mypy(log_text: str) -> dict[str, object]:
    error_re = re.compile(r"\[(?P<code>[a-z0-9\-]+)\]$", re.IGNORECASE)
    lines = [ln for ln in log_text.splitlines() if ": error:" in ln]
    codes = Counter()
    for line in lines:
        m = error_re.search(line)
        if m:
            codes[m.group("code")] += 1
    return {
        "error_count": len(lines),
        "top_codes": codes.most_common(8),
    }


def _parse_ruff(log_text: str) -> dict[str, object]:
    rule_re = re.compile(r"^([A-Z]\d{3})\b")
    rules = Counter()
    for line in log_text.splitlines():
        m = rule_re.match(line.strip())
        if m:
            rules[m.group(1)] += 1
    return {
        "issue_count": sum(rules.values()),
        "top_rules": rules.most_common(8),
    }


def _parse_bandit(log_text: str) -> dict[str, object]:
    issue_re = re.compile(r"\[([A-Z]\d+)[:\]]")
    sev_re = re.compile(r"Severity:\s+(Low|Medium|High)", re.IGNORECASE)
    issue_counts = Counter()
    severity_counts = Counter()

    for line in log_text.splitlines():
        issue_match = issue_re.search(line)
        if issue_match:
            issue_counts[issue_match.group(1)] += 1
        sev_match = sev_re.search(line)
        if sev_match:
            severity_counts[sev_match.group(1).capitalize()] += 1

    return {
        "issue_count": sum(issue_counts.values()),
        "top_issue_types": issue_counts.most_common(8),
        "severity": dict(severity_counts),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze latest pytest and quality logs and print a concise summary."
    )
    parser.add_argument(
        "root_arg",
        nargs="?",
        type=Path,
        help="Optional repository root path (positional).",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root (default: current working directory)",
    )
    args = parser.parse_args()

    root_candidate = args.root if args.root is not None else args.root_arg
    root = (root_candidate or Path.cwd()).resolve()
    logs_dir = root / "logs"

    candidate_pytest_logs: list[Path] = []
    if logs_dir.exists():
        candidate_pytest_logs.extend(logs_dir.glob("test_results_*.pytest.log"))
        candidate_pytest_logs.append(logs_dir / "pytest_manual_latest.log")

    pytest_log = _latest_file(candidate_pytest_logs)
    mypy_log = _resolve_quality_log(root, logs_dir, "mypy.out.txt")
    ruff_log = _resolve_quality_log(root, logs_dir, "ruff.out.txt")
    bandit_log = _resolve_quality_log(root, logs_dir, "bandit.out.txt")

    print("Test Log Analysis")
    print("=================")
    print(f"Root: {root}")

    if pytest_log and pytest_log.exists():
        pytest_info = _parse_pytest(pytest_log.read_text(encoding="utf-8", errors="replace"))
        print("\n[pytest]")
        print(f"log: {pytest_log.relative_to(root)}")
        print(f"summary: {pytest_info['summary'] or 'summary line not found'}")
        failures = pytest_info["failures"]
        if failures:
            print(f"failing tests ({len(failures)}):")
            for test_id in failures:
                print(f"- {test_id}")
        else:
            print("failing tests: none detected")
    else:
        print("\n[pytest]")
        print("log: not found")

    if mypy_log and mypy_log.exists():
        mypy_info = _parse_mypy(mypy_log.read_text(encoding="utf-8", errors="replace"))
        print("\n[mypy]")
        print(f"log: {mypy_log.relative_to(root)}")
        print(f"errors: {mypy_info['error_count']}")
        top_codes = mypy_info["top_codes"]
        if top_codes:
            print("top codes:")
            for code, count in top_codes:
                print(f"- {code}: {count}")
    else:
        print("\n[mypy]")
        print("log: not found")

    if ruff_log and ruff_log.exists():
        ruff_info = _parse_ruff(ruff_log.read_text(encoding="utf-8", errors="replace"))
        print("\n[ruff]")
        print(f"log: {ruff_log.relative_to(root)}")
        print(f"issues: {ruff_info['issue_count']}")
        top_rules = ruff_info["top_rules"]
        if top_rules:
            print("top rules:")
            for rule, count in top_rules:
                print(f"- {rule}: {count}")
    else:
        print("\n[ruff]")
        print("log: not found")

    if bandit_log and bandit_log.exists():
        bandit_info = _parse_bandit(
            bandit_log.read_text(encoding="utf-8", errors="replace")
        )
        print("\n[bandit]")
        print(f"log: {bandit_log.relative_to(root)}")
        print(f"issues: {bandit_info['issue_count']}")
        severity = bandit_info["severity"]
        if severity:
            print("severity:")
            for level in ("High", "Medium", "Low"):
                if level in severity:
                    print(f"- {level}: {severity[level]}")
        top_issue_types = bandit_info["top_issue_types"]
        if top_issue_types:
            print("top issue types:")
            for issue, count in top_issue_types:
                print(f"- {issue}: {count}")
    else:
        print("\n[bandit]")
        print("log: not found")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
