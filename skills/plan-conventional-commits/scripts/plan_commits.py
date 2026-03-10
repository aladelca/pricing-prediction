#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

DOC_EXTENSIONS = {".md", ".mdx", ".rst", ".txt", ".adoc"}
ASSET_EXTENSIONS = {
    ".avif",
    ".csv",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".jsonl",
    ".pdf",
    ".png",
    ".svg",
    ".webp",
    ".woff",
    ".woff2",
    ".zip",
}
TEST_MARKERS = {"test", "tests", "spec", "specs", "__tests__", "e2e"}
CONTAINER_DIRS = {"apps", "modules", "packages", "services"}
GENERIC_SCOPE_TOKENS = {
    "app",
    "apps",
    "agents",
    "bin",
    "build",
    "client",
    "cmd",
    "config",
    "configs",
    "doc",
    "docs",
    "e2e",
    "examples",
    "gitkeep",
    "helper",
    "helpers",
    "index",
    "internal",
    "lock",
    "lib",
    "libs",
    "main",
    "module",
    "modules",
    "package",
    "packages",
    "public",
    "readme",
    "resources",
    "scripts",
    "server",
    "shared",
    "skill",
    "skills",
    "spec",
    "specs",
    "src",
    "test",
    "tests",
    "tmp",
    "types",
    "util",
    "utils",
    "vendor",
    "web",
    "www",
}
DEPENDENCY_FILES = {
    "bun.lockb",
    "cargo.lock",
    "composer.json",
    "composer.lock",
    "gemfile",
    "gemfile.lock",
    "go.mod",
    "go.sum",
    "package-lock.json",
    "package.json",
    "pipfile",
    "pipfile.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "requirements-dev.txt",
    "requirements.txt",
    "yarn.lock",
}
BUILD_FILES = {
    ".dockerignore",
    ".editorconfig",
    ".eslintignore",
    ".gitignore",
    ".gitkeep",
    ".prettierignore",
    "docker-compose.yaml",
    "docker-compose.yml",
    "dockerfile",
    "eslint.config.cjs",
    "eslint.config.js",
    "eslint.config.mjs",
    "makefile",
    "mypy.ini",
    "nx.json",
    "prettier.config.cjs",
    "prettier.config.js",
    "pyproject.toml",
    "pytest.ini",
    "ruff.toml",
    "setup.cfg",
    "setup.py",
    "skills-lock.json",
    "tox.ini",
    "tsconfig.json",
    "turbo.json",
}


@dataclass
class FileChange:
    path: str
    raw_status: str
    staged_state: str
    change_kind: str
    category: str
    scope_hint: str


def run_git(repo: Path, args: list[str], check: bool = True) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if check and completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
    return completed.stdout


def normalize_token(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    value = re.sub(r"-{2,}", "-", value)
    return value or "repo"


def split_tokens(value: str) -> list[str]:
    return [token for token in re.split(r"[^a-z0-9]+", value.lower()) if token]


def classify_category(path: str) -> str:
    parts = [part.lower() for part in Path(path).parts]
    name = parts[-1]
    ext = Path(name).suffix.lower()

    if len(parts) > 1 and parts[0] == ".github" and parts[1] == "workflows":
        return "ci"
    if any(part in TEST_MARKERS for part in parts[:-1]):
        return "test"
    if re.search(r"(^|[._-])(test|spec|e2e)([._-]|$)", name):
        return "test"
    if ext in DOC_EXTENSIONS or (parts and parts[0] in {"doc", "docs"}):
        return "docs"
    if name in DEPENDENCY_FILES:
        return "dependency"
    if name in BUILD_FILES or re.search(r"(^|[._-])(config|rc)([._-]|$)", name):
        return "build"
    if ext in ASSET_EXTENSIONS:
        return "asset"
    if parts and parts[0] in {"bin", "script", "scripts", "tools"}:
        return "tooling"
    return "source"


def derive_scope(path: str, category: str) -> str:
    parts = list(Path(path).parts)
    lowered = [part.lower() for part in parts]
    name = lowered[-1]

    if len(lowered) > 2 and lowered[0] == ".agents" and lowered[1] == "skills":
        return normalize_token(lowered[2])
    if len(lowered) > 1 and lowered[0] == "skills":
        return normalize_token(lowered[1])
    if category == "ci" and len(lowered) > 2:
        return normalize_token(Path(name).stem)

    search_parts: list[str]
    if len(lowered) > 1 and lowered[0] in CONTAINER_DIRS:
        search_parts = lowered[1:]
    elif len(lowered) > 1 and lowered[0] in GENERIC_SCOPE_TOKENS:
        search_parts = lowered[1:]
    else:
        search_parts = lowered

    candidates: list[str] = []
    for part in search_parts[:-1]:
        candidates.extend(split_tokens(part))
    candidates.extend(split_tokens(Path(name).stem))

    for token in candidates:
        if token in GENERIC_SCOPE_TOKENS:
            continue
        if len(token) == 1 and not token.isdigit():
            continue
        return normalize_token(token)
    return "repo"


def staged_state(raw_status: str) -> str:
    if raw_status == "??":
        return "unstaged"
    x, y = raw_status[0], raw_status[1]
    if x != " " and y != " ":
        return "mixed"
    if x != " ":
        return "staged"
    return "unstaged"


def change_kind(raw_status: str, raw_path: str) -> str:
    if raw_status == "??":
        return "added"
    if "U" in raw_status:
        return "unmerged"
    if " -> " in raw_path or "R" in raw_status or "C" in raw_status:
        return "renamed"
    if "A" in raw_status:
        return "added"
    if "D" in raw_status:
        return "deleted"
    if "M" in raw_status:
        return "modified"
    return "changed"


def parse_status(repo: Path) -> list[FileChange]:
    output = run_git(repo, ["status", "--porcelain=v1", "--untracked-files=all"])
    changes: list[FileChange] = []
    for line in output.splitlines():
        if not line:
            continue
        raw_status = line[:2]
        raw_path = line[3:]
        path = raw_path.split(" -> ", 1)[1] if " -> " in raw_path else raw_path
        category = classify_category(path)
        changes.append(
            FileChange(
                path=path,
                raw_status=raw_status,
                staged_state=staged_state(raw_status),
                change_kind=change_kind(raw_status, raw_path),
                category=category,
                scope_hint=derive_scope(path, category),
            )
        )
    return sorted(changes, key=lambda item: item.path)


def group_key(change: FileChange) -> str:
    if change.scope_hint != "repo":
        return change.scope_hint
    if change.category in {"build", "dependency", "tooling"}:
        return "repo-tooling"
    if change.category == "docs":
        return "repo-docs"
    if change.category == "test":
        return "repo-tests"
    if change.category == "ci":
        return "repo-ci"
    if change.category == "asset":
        return "repo-assets"
    return "repo-source"


def infer_type(entries: list[FileChange]) -> tuple[str, list[str]]:
    categories = {entry.category for entry in entries}
    kinds = {entry.change_kind for entry in entries}

    if categories == {"ci"}:
        return "ci", []
    if categories == {"docs"}:
        return "docs", []
    if categories == {"test"}:
        return "test", []
    if categories <= {"build", "dependency"}:
        return "build", ["chore"]
    if categories <= {"tooling"}:
        return "chore", ["build"]
    if categories <= {"asset"}:
        return "chore", []
    if categories <= {"docs", "test"}:
        return ("docs", ["test"]) if "docs" in categories else ("test", ["docs"])
    if "source" in categories:
        if kinds <= {"deleted"}:
            return "refactor", ["chore"]
        if "added" in kinds or "renamed" in kinds:
            return "feat", ["fix", "refactor"]
        if "test" in categories:
            return "fix", ["refactor"]
        return "refactor", ["fix"]
    return "chore", []


def infer_confidence(entries: list[FileChange], scope: str) -> str:
    if any(entry.change_kind == "unmerged" for entry in entries):
        return "low"

    categories = {entry.category for entry in entries}
    score = 0
    if scope != "repo":
        score += 1
    if len(categories) == 1 or categories <= {"source", "test", "docs"}:
        score += 1
    if len(entries) == 1 and scope != "repo":
        score += 1
    if scope == "repo" and "source" in categories:
        score -= 1
    if scope == "repo" and categories <= {"build", "dependency", "tooling", "docs", "test", "ci"}:
        score += 1
    if len(categories) > 3:
        score -= 1

    if score >= 2:
        return "high"
    if score >= 1:
        return "medium"
    return "low"


def infer_subject(commit_type: str, scope: str, entries: list[FileChange]) -> str:
    only_deleted = {entry.change_kind for entry in entries} == {"deleted"}
    scope_label = scope if scope != "repo" else "repo"

    if commit_type == "feat":
        return f"add {scope_label} support"
    if commit_type == "fix":
        return f"fix {scope_label} behavior"
    if commit_type == "refactor":
        return (
            f"remove obsolete {scope_label} code"
            if only_deleted
            else f"refactor {scope_label} module"
        )
    if commit_type == "perf":
        return f"improve {scope_label} performance"
    if commit_type == "docs":
        return "update repo docs" if scope == "repo" else f"document {scope_label}"
    if commit_type == "test":
        return "cover repo changes" if scope == "repo" else f"cover {scope_label}"
    if commit_type == "build":
        return "update repo tooling" if scope == "repo" else f"update {scope_label} build config"
    if commit_type == "ci":
        return "update ci pipeline" if scope == "repo" else f"update {scope_label} workflow"
    if commit_type == "chore":
        return "update repo maintenance" if scope == "repo" else f"update {scope_label} maintenance"
    return f"update {scope_label}"


def build_rationale(entries: list[FileChange], scope: str) -> str:
    categories = sorted({entry.category for entry in entries})
    kinds = sorted({entry.change_kind for entry in entries})
    label = f"{len(entries)} files share scope '{scope}'" if scope != "repo" else f"{len(entries)} repo-wide files"
    category_text = ", ".join(categories)
    kind_text = ", ".join(kinds)
    return f"{label}; categories: {category_text}; changes: {kind_text}."


def build_notes(entries: list[FileChange], scope: str, confidence: str) -> list[str]:
    notes: list[str] = []
    states = {entry.staged_state for entry in entries}
    categories = {entry.category for entry in entries}

    if "mixed" in states or len(states) > 1:
        notes.append("Contains both staged and unstaged work.")
    if scope == "repo" and "source" in categories:
        notes.append("Repo-wide source changes may hide more than one objective.")
    if confidence == "low":
        notes.append("Inspect the diff before approving this group.")
    return notes


def build_plan(repo: Path, changes: list[FileChange]) -> dict:
    if not changes:
        return {
            "repo_root": str(repo),
            "blocked": False,
            "warnings": [],
            "summary": "No changed files found.",
            "file_count": 0,
            "files": [],
            "groups": [],
        }

    if any(change.change_kind == "unmerged" for change in changes):
        return {
            "repo_root": str(repo),
            "blocked": True,
            "warnings": ["Unresolved merge conflicts detected. Resolve them before planning commits."],
            "summary": "Commit planning is blocked by merge conflicts.",
            "file_count": len(changes),
            "files": [change.__dict__ for change in changes],
            "groups": [],
        }

    grouped: dict[str, list[FileChange]] = defaultdict(list)
    for change in changes:
        grouped[group_key(change)].append(change)

    groups = []
    for index, key in enumerate(sorted(grouped), start=1):
        entries = sorted(grouped[key], key=lambda item: item.path)
        scope = entries[0].scope_hint if key not in {
            "repo-tooling",
            "repo-docs",
            "repo-tests",
            "repo-ci",
            "repo-assets",
            "repo-source",
        } else "repo"
        commit_type, alternatives = infer_type(entries)
        confidence = infer_confidence(entries, scope)
        subject = infer_subject(commit_type, scope, entries)
        groups.append(
            {
                "id": f"commit-{index}",
                "message": f"{commit_type}({scope}): {subject}",
                "type_hint": commit_type,
                "alternative_types": alternatives,
                "scope": scope,
                "subject_hint": subject,
                "confidence": confidence,
                "why": build_rationale(entries, scope),
                "notes": build_notes(entries, scope, confidence),
                "files": [entry.path for entry in entries],
                "categories": dict(Counter(entry.category for entry in entries)),
            }
        )

    order = {
        "build": 0,
        "ci": 1,
        "chore": 2,
        "feat": 3,
        "fix": 4,
        "refactor": 5,
        "perf": 6,
        "test": 7,
        "docs": 8,
    }
    groups.sort(key=lambda item: (order.get(item["type_hint"], 99), item["scope"], item["message"]))
    for index, group in enumerate(groups, start=1):
        group["id"] = f"commit-{index}"

    warnings = []
    if any(group["confidence"] == "low" for group in groups):
        warnings.append("At least one proposed commit has low confidence and should be checked with git diff.")

    return {
        "repo_root": str(repo),
        "blocked": False,
        "warnings": warnings,
        "summary": f"Planned {len(groups)} commit groups from {len(changes)} changed files.",
        "file_count": len(changes),
        "files": [change.__dict__ for change in changes],
        "groups": groups,
    }


def render_markdown(plan: dict) -> str:
    lines = ["## Proposed Commit Plan", ""]
    lines.append(f"Repo: `{plan['repo_root']}`")
    lines.append(plan["summary"])
    lines.append("")

    for warning in plan["warnings"]:
        lines.append(f"- Warning: {warning}")
    if plan["warnings"]:
        lines.append("")

    if plan["blocked"]:
        lines.append("Planning is blocked. Resolve the warning above and rerun the analyzer.")
        return "\n".join(lines)

    if not plan["groups"]:
        lines.append("No commit plan is needed.")
        return "\n".join(lines)

    for index, group in enumerate(plan["groups"], start=1):
        lines.append(f"{index}. `{group['message']}`")
        lines.append(f"Why: {group['why']}")
        lines.append(f"Confidence: {group['confidence']}")
        if group["alternative_types"]:
            lines.append("Alternative types: " + ", ".join(group["alternative_types"]))
        lines.append("Files:")
        for path in group["files"]:
            lines.append(f"- {path}")
        for note in group["notes"]:
            lines.append(f"Note: {note}")
        lines.append("")

    lines.append("Waiting for approval before staging or committing.")
    return "\n".join(lines).rstrip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Group git worktree changes into approval-ready Conventional Commit suggestions."
    )
    parser.add_argument("--repo", default=".", help="Path to the target git repository.")
    parser.add_argument(
        "--format",
        choices={"json", "markdown"},
        default="markdown",
        help="Output format.",
    )
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    try:
        repo_root = Path(run_git(repo, ["rev-parse", "--show-toplevel"]).strip())
        changes = parse_status(repo_root)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    plan = build_plan(repo_root, changes)
    if args.format == "json":
        print(json.dumps(plan, indent=2))
    else:
        print(render_markdown(plan))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
