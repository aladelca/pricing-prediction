#!/usr/bin/env python3
"""
Helpers for a branch-first pull request workflow with self-review artifacts.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


def sanitize_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug[:48].strip("-") or "change"


def run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        check=False,
        text=True,
        capture_output=True,
    )


def command_branch(args: argparse.Namespace) -> int:
    slug = sanitize_slug(args.title)
    pieces = [args.kind.rstrip("/")]
    if args.ticket:
        pieces.append(sanitize_slug(args.ticket))
    pieces.append(slug)
    branch_name = "/".join([pieces[0], "-".join(pieces[1:])])
    print(branch_name)

    if not args.create:
        return 0

    status = run_git(["status", "--short"])
    if status.returncode != 0:
        print(status.stderr.strip(), file=sys.stderr)
        return status.returncode

    if status.stdout.strip() and not args.allow_dirty:
        print(
            "Refusing to create branch from a dirty worktree. Use --allow-dirty if intentional.",
            file=sys.stderr,
        )
        return 2

    current = run_git(["branch", "--show-current"])
    if current.returncode != 0:
        print(current.stderr.strip(), file=sys.stderr)
        return current.returncode

    if current.stdout.strip() != args.base:
        checkout_base = run_git(["checkout", args.base])
        if checkout_base.returncode != 0:
            print(checkout_base.stderr.strip(), file=sys.stderr)
            return checkout_base.returncode

    create_branch = run_git(["checkout", "-b", branch_name])
    if create_branch.returncode != 0:
        print(create_branch.stderr.strip(), file=sys.stderr)
        return create_branch.returncode

    return 0


def build_markdown_list(items: list[str], empty_text: str) -> str:
    if not items:
        return f"- {empty_text}"
    return "\n".join(f"- {item}" for item in items)


def current_branch_name() -> str:
    branch = run_git(["branch", "--show-current"])
    if branch.returncode != 0:
        return "UNKNOWN"
    return branch.stdout.strip() or "UNKNOWN"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def command_pr_body(args: argparse.Namespace) -> int:
    issue_value = args.issue or "Not linked"
    head_branch = args.head_branch or current_branch_name()
    content = f"""# Summary

{args.summary}

# PR Title

- {args.title}

# Scope

{build_markdown_list(args.scope, "Scope not provided.")}

# Validation

{build_markdown_list(args.tests, "Validation not provided.")}

# Risks And Follow-Ups

{build_markdown_list(args.risk, "No explicit risks or follow-ups recorded.")}

# Traceability

- Issue: {issue_value}
- Head branch: {head_branch}
- Base branch: {args.base_branch}
"""
    write_text(Path(args.output), content)
    print(args.output)
    return 0


def command_review_body(args: argparse.Namespace) -> int:
    findings = Path(args.findings_file).read_text().strip()
    if not findings:
        findings = "No findings."

    content = f"""# Self-Review Summary

{args.summary}

# Verdict

- Proposed verdict: {args.verdict.upper()}

# Findings

{findings}
"""
    write_text(Path(args.output), content)
    print(args.output)
    return 0


def command_verdict(args: argparse.Namespace) -> int:
    status = args.status.upper()
    content = f"""# {status}

{args.summary}

- Blocking status: {args.blocking}
- Next step: {args.next_step}
"""
    write_text(Path(args.output), content)
    print(args.output)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate branch names and PR review artifacts."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    branch = subparsers.add_parser("branch", help="Print or create a branch.")
    branch.add_argument("--title", required=True, help="Work item title.")
    branch.add_argument(
        "--ticket",
        help="Issue or ticket id to include in the branch name.",
    )
    branch.add_argument(
        "--kind",
        default="feature",
        choices=("feature", "fix", "chore", "refactor"),
        help="Branch prefix.",
    )
    branch.add_argument(
        "--base",
        default="main",
        help="Base branch used when creating the branch.",
    )
    branch.add_argument(
        "--create",
        action="store_true",
        help="Create the branch instead of only printing its name.",
    )
    branch.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow branch creation from a dirty worktree.",
    )
    branch.set_defaults(func=command_branch)

    pr_body = subparsers.add_parser("pr-body", help="Generate a PR body markdown file.")
    pr_body.add_argument("--title", required=True, help="PR title. Stored for traceability.")
    pr_body.add_argument("--summary", required=True, help="Top-level PR summary.")
    pr_body.add_argument(
        "--scope",
        action="append",
        default=[],
        help="Scope line. Repeat the flag for multiple entries.",
    )
    pr_body.add_argument(
        "--tests",
        action="append",
        default=[],
        help="Validation command or result. Repeat the flag for multiple entries.",
    )
    pr_body.add_argument(
        "--risk",
        action="append",
        default=[],
        help="Risk or follow-up line. Repeat the flag for multiple entries.",
    )
    pr_body.add_argument("--issue", help="Issue or task id.")
    pr_body.add_argument("--head-branch", default="")
    pr_body.add_argument("--base-branch", default="main")
    pr_body.add_argument("--output", required=True, help="Output markdown path.")
    pr_body.set_defaults(func=command_pr_body)

    review_body = subparsers.add_parser(
        "review-body", help="Generate a review markdown file."
    )
    review_body.add_argument("--summary", required=True, help="Review summary.")
    review_body.add_argument(
        "--verdict",
        required=True,
        choices=("go", "no-go"),
        help="Proposed verdict.",
    )
    review_body.add_argument(
        "--findings-file",
        required=True,
        help="Markdown or text file containing severity-ranked findings.",
    )
    review_body.add_argument("--output", required=True, help="Output markdown path.")
    review_body.set_defaults(func=command_review_body)

    verdict = subparsers.add_parser(
        "verdict", help="Generate a final verdict comment markdown file."
    )
    verdict.add_argument(
        "--status",
        required=True,
        choices=("go", "no-go"),
        help="Final status.",
    )
    verdict.add_argument("--summary", required=True, help="Verdict summary.")
    verdict.add_argument(
        "--blocking",
        required=True,
        help="Blocking findings summary.",
    )
    verdict.add_argument("--next-step", required=True, help="Next action.")
    verdict.add_argument("--output", required=True, help="Output markdown path.")
    verdict.set_defaults(func=command_verdict)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
