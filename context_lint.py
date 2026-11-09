#!/usr/bin/env python3
"""
context-lint — Offline context budget auditor for AI agent prompts.
Measures token count, detects waste, and suggests trim targets.
Zero dependencies. Pure Python 3.8+.

Usage: python context_lint.py <path/to/prompt.md> [--max-tokens 8000]
"""

import sys
import re
import json
from pathlib import Path
from collections import Counter

ESTIMATED_TOKENS_PER_CHAR = 0.25
EMPTY_LINE_THRESHOLD = 3
LONG_LINE_CHARS = 200
INSTRUCTION_MARKERS = [
    "#", "Instructions", "instructions", "## ", "### ",
    "You are", "You must", "Your job", "Role:", "Task:"
]
FILLER_PATTERNS = [
    r"(?i)let me know if you (?:have|need|want)",
    r"(?i)feel free to",
    r"(?i)please (?:note|be aware|keep in mind)",
    r"(?i)it is important to (?:note|mention|remember)",
    r"(?i)as an AI",
    r"(?i)I hope this",
    r"(?i)don't hesitate",
    r"(?i)certainly!",
    r"(?i)of course!",
]


def estimate_tokens(text: str) -> int:
    return max(1, int(len(text) * ESTIMATED_TOKENS_PER_CHAR))


def lint_file(filepath: str, max_tokens: int = 8000) -> dict:
    path = Path(filepath)
    if not path.exists():
        return {"error": f"File not found: {filepath}"}

    content = path.read_text(encoding="utf-8", errors="replace")
    lines = content.split("\n")
    tokens = estimate_tokens(content)
    over_budget = tokens > max_tokens if max_tokens else None
    waste_percent = 0
    findings = []

    consecutive_empty = 0
    empty_ranges = []
    for i, line in enumerate(lines, 1):
        if line.strip() == "":
            consecutive_empty += 1
        else:
            if consecutive_empty >= EMPTY_LINE_THRESHOLD:
                empty_ranges.append((i - consecutive_empty, i - 1, consecutive_empty))
            consecutive_empty = 0
        if len(line) > LONG_LINE_CHARS:
            findings.append({
                "type": "long_line",
                "severity": "LOW",
                "line": i,
                "message": f"Line {i} is {len(line)} chars ({LONG_LINE_CHARS}+). Consider breaking.",
                "waste_estimate": estimate_tokens(line) - estimate_tokens(line[:LONG_LINE_CHARS])
            })

    if consecutive_empty >= EMPTY_LINE_THRESHOLD:
        empty_ranges.append((len(lines) - consecutive_empty + 1, len(lines), consecutive_empty))

    wasted_empty_tokens = sum(estimate_tokens("\n" * c) for _, _, c in empty_ranges)

    filler_findings = []
    for pattern in FILLER_PATTERNS:
        for i, line in enumerate(lines, 1):
            if re.search(pattern, line):
                filler_findings.append({
                    "type": "filler_phrase",
                    "severity": "LOW",
                    "line": i,
                    "message": f"Filler phrase detected at line {i}",
                    "snippet": line.strip()[:100]
                })
    findings.extend(filler_findings)

    duplicate_blocks = []
    seen = {}
    buffer = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped:
            buffer.append(stripped)
        if len(buffer) >= 3 or (not stripped and buffer):
            block = "\n".join(buffer)
            if len(block) > 40 and block in seen:
                duplicate_blocks.append((seen[block], i + 1, block[:80]))
            elif len(block) > 40:
                seen[block] = i + 1
            if not stripped:
                buffer = []

    waste_tokens = wasted_empty_tokens
    waste_tokens += sum(f["waste_estimate"] for f in findings if "waste_estimate" in f)

    if tokens > 0 and waste_tokens > 0:
        waste_percent = round((waste_tokens / tokens) * 100, 1)

    budget_status = "OK" if not over_budget else "OVER BUDGET" if over_budget else "UNLIMITED"

    return {
        "file": str(path.absolute()),
        "budget_status": budget_status,
        "max_tokens": max_tokens,
        "estimated_tokens": tokens,
        "waste_tokens": waste_tokens,
        "waste_percent": waste_percent,
        "stats": {
            "total_lines": len(lines),
            "total_chars": len(content),
            "empty_lines": sum(1 for l in lines if l.strip() == ""),
            "long_lines": sum(1 for l in lines if len(l) > LONG_LINE_CHARS)
        },
        "findings": findings,
        "suggestions": [
            f"Remove {wasted_empty_tokens} wasted tokens from excessive blank lines" if wasted_empty_tokens > 10 else None,
            f"Trim {len(empty_ranges)} sections with 3+ consecutive blank lines" if empty_ranges else None,
            f"Cut {len(duplicate_blocks)} near-duplicate blocks" if duplicate_blocks else None,
            f"Budget: {tokens}/{max_tokens} ({(tokens/max_tokens)*100:.0f}%)" if max_tokens else f"Estimated tokens: {tokens}"
        ]
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python context_lint.py <path/to/prompt.md> [--max-tokens N] [--json]")
        sys.exit(1)

    filepath = sys.argv[1]
    max_tokens = 8000
    as_json = "--json" in sys.argv

    for i, arg in enumerate(sys.argv):
        if arg == "--max-tokens" and i + 1 < len(sys.argv):
            max_tokens = int(sys.argv[i + 1])

    result = lint_file(filepath, max_tokens)

    if "error" in result:
        print(result["error"], file=sys.stderr)
        sys.exit(2)

    if as_json:
        print(json.dumps(result, indent=2))
    else:
        print(f"context-lint v1.0.0")
        print(f"File: {result['file']}")
        print(f"Budget: {result['budget_status']} ({result['estimated_tokens']}/{result['max_tokens']} tokens)")
        if result['waste_tokens'] > 0:
            print(f"Waste: {result['waste_tokens']} tokens ({result['waste_percent']}%)")
        if result['findings']:
            print(f"\n--- Findings ({len(result['findings'])}) ---")
            for f in result['findings'][:20]:
                print(f"  [{f['severity']}] L{f['line']}: {f['message']}")

    sys.exit(0 if result["budget_status"] == "OK" or result["max_tokens"] == 0 else 1)


if __name__ == "__main__":
    main()