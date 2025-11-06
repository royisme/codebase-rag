#!/usr/bin/env python3
"""
Automatic Changelog Generator from Git Commits

Generates changelog entries from git commits following Conventional Commits format:
- feat: New features
- fix: Bug fixes
- docs: Documentation changes
- perf: Performance improvements
- refactor: Code refactoring
- test: Test updates
- chore: Build/tooling changes
"""

import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple


# Conventional Commits types mapping to changelog sections
COMMIT_TYPE_MAP = {
    "feat": "### Added",
    "fix": "### Fixed",
    "docs": "### Documentation",
    "perf": "### Performance",
    "refactor": "### Changed",
    "test": "### Testing",
    "style": "### Changed",
    "build": "### Build System",
    "ci": "### CI/CD",
    "chore": "### Maintenance",
}

# Breaking change marker
BREAKING_CHANGE_MARKERS = ["BREAKING CHANGE:", "BREAKING-CHANGE:", "!:"]


def get_git_commits(from_tag: str = None, to_ref: str = "HEAD") -> List[Tuple[str, str, str]]:
    """
    Get git commits between two references.

    Returns: List of (hash, date, message) tuples
    """
    if from_tag:
        range_spec = f"{from_tag}..{to_ref}"
    else:
        # Get all commits
        range_spec = to_ref

    try:
        result = subprocess.run(
            ["git", "log", range_spec, "--pretty=format:%H|%as|%s%n%b%n---END---"],
            capture_output=True,
            text=True,
            check=True
        )

        commits = []
        current_commit = []

        for line in result.stdout.split('\n'):
            if line == '---END---':
                if current_commit:
                    full_message = '\n'.join(current_commit[1:])
                    hash_date_subject = current_commit[0].split('|')
                    if len(hash_date_subject) >= 3:
                        commits.append((
                            hash_date_subject[0],
                            hash_date_subject[1],
                            full_message
                        ))
                current_commit = []
            else:
                current_commit.append(line)

        return commits
    except subprocess.CalledProcessError as e:
        print(f"Error getting git commits: {e}", file=sys.stderr)
        return []


def parse_commit_message(message: str) -> Dict:
    """
    Parse a conventional commit message.

    Returns dict with: type, scope, subject, body, breaking
    """
    # Match conventional commit format: type(scope): subject
    match = re.match(r'^(\w+)(?:\(([^)]+)\))?(!)?:\s*(.+?)(?:\n\n(.*))?$',
                     message, re.DOTALL)

    if not match:
        # Not a conventional commit, treat as misc
        return {
            "type": "chore",
            "scope": None,
            "subject": message.split('\n')[0],
            "body": '\n'.join(message.split('\n')[1:]),
            "breaking": False
        }

    type_, scope, breaking_mark, subject, body = match.groups()
    body = body or ""

    # Check for breaking changes
    is_breaking = bool(breaking_mark) or any(
        marker in body for marker in BREAKING_CHANGE_MARKERS
    )

    return {
        "type": type_.lower(),
        "scope": scope,
        "subject": subject.strip(),
        "body": body.strip(),
        "breaking": is_breaking
    }


def group_commits(commits: List[Tuple[str, str, str]]) -> Dict[str, List[Dict]]:
    """
    Group commits by type.

    Returns: Dict mapping section name to list of commits
    """
    grouped = defaultdict(list)
    breaking_changes = []

    for hash_, date, message in commits:
        parsed = parse_commit_message(message)
        parsed["hash"] = hash_[:7]  # Short hash
        parsed["date"] = date

        # Handle breaking changes separately
        if parsed["breaking"]:
            breaking_changes.append(parsed)

        # Group by type
        section = COMMIT_TYPE_MAP.get(parsed["type"], "### Other")
        grouped[section].append(parsed)

    # Add breaking changes section at the top if any
    if breaking_changes:
        grouped["### ⚠️ Breaking Changes"] = breaking_changes

    return dict(grouped)


def format_changelog_entry(commits: List[Dict]) -> str:
    """
    Format commits into changelog entry lines.
    """
    lines = []
    for commit in commits:
        scope = f"**{commit['scope']}**: " if commit['scope'] else ""
        subject = commit['subject']

        # Capitalize first letter if not already
        if subject and subject[0].islower():
            subject = subject[0].upper() + subject[1:]

        lines.append(f"- {scope}{subject}")

    return '\n'.join(lines)


def generate_changelog_section(version: str, date: str, grouped_commits: Dict[str, List[Dict]]) -> str:
    """
    Generate a complete changelog section for a version.
    """
    lines = [
        f"## [{version}] - {date}",
        ""
    ]

    # Define preferred order
    preferred_order = [
        "### ⚠️ Breaking Changes",
        "### Added",
        "### Fixed",
        "### Changed",
        "### Performance",
        "### Documentation",
        "### Testing",
        "### Build System",
        "### CI/CD",
        "### Maintenance",
        "### Other",
    ]

    # Add sections in preferred order
    for section in preferred_order:
        if section in grouped_commits:
            lines.append(section)
            lines.append("")
            lines.append(format_changelog_entry(grouped_commits[section]))
            lines.append("")

    return '\n'.join(lines)


def get_latest_tag() -> str:
    """Get the most recent git tag."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def get_current_version() -> str:
    """Get version from pyproject.toml."""
    try:
        with open("pyproject.toml", "r") as f:
            for line in f:
                if line.startswith("version = "):
                    return line.split('"')[1]
    except FileNotFoundError:
        pass
    return "0.1.0"


def main():
    """Main function to generate changelog."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate changelog from git commits"
    )
    parser.add_argument(
        "--from-tag",
        help="Start from this tag (default: latest tag or all commits)"
    )
    parser.add_argument(
        "--to-ref",
        default="HEAD",
        help="End at this ref (default: HEAD)"
    )
    parser.add_argument(
        "--version",
        help="Version for this changelog entry (default: from pyproject.toml)"
    )
    parser.add_argument(
        "--date",
        help="Date for this entry (default: today)"
    )
    parser.add_argument(
        "--output",
        help="Output file (default: print to stdout)"
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update docs/changelog.md by prepending new section"
    )

    args = parser.parse_args()

    # Determine from_tag
    from_tag = args.from_tag
    if not from_tag:
        from_tag = get_latest_tag()
        if from_tag:
            print(f"Using latest tag as starting point: {from_tag}", file=sys.stderr)
        else:
            print("No tags found, processing all commits", file=sys.stderr)

    # Get commits
    commits = get_git_commits(from_tag, args.to_ref)

    if not commits:
        print("No commits found to process", file=sys.stderr)
        return 1

    print(f"Processing {len(commits)} commits...", file=sys.stderr)

    # Group commits
    grouped = group_commits(commits)

    # Determine version and date
    version = args.version or get_current_version()
    date = args.date or datetime.now().strftime("%Y-%m-%d")

    # Generate changelog section
    changelog_section = generate_changelog_section(version, date, grouped)

    # Output
    if args.update:
        # Read existing changelog
        try:
            with open("docs/changelog.md", "r") as f:
                existing_content = f.read()
        except FileNotFoundError:
            print("docs/changelog.md not found, creating new file", file=sys.stderr)
            existing_content = """# Changelog

All notable changes to the Code Graph Knowledge System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

"""

        # Find [Unreleased] section and insert after it
        unreleased_match = re.search(r'## \[Unreleased\].*?\n\n', existing_content, re.DOTALL)

        if unreleased_match:
            insert_pos = unreleased_match.end()
            new_content = (
                existing_content[:insert_pos] +
                changelog_section + "\n\n" +
                existing_content[insert_pos:]
            )
        else:
            # Just prepend after header
            header_end = existing_content.find('\n\n') + 2
            new_content = (
                existing_content[:header_end] +
                changelog_section + "\n\n" +
                existing_content[header_end:]
            )

        # Write back
        with open("docs/changelog.md", "w") as f:
            f.write(new_content)

        print(f"✅ Updated docs/changelog.md with v{version} entries", file=sys.stderr)

    elif args.output:
        with open(args.output, "w") as f:
            f.write(changelog_section)
        print(f"✅ Wrote changelog to {args.output}", file=sys.stderr)

    else:
        print(changelog_section)

    return 0


if __name__ == "__main__":
    sys.exit(main())
