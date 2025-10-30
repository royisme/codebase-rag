"""Utilities for synchronizing Git repositories used as knowledge sources."""

from __future__ import annotations

import asyncio
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlparse, urlunparse

from loguru import logger

from config import settings


@dataclass
class GitSyncResult:
    """Result metadata for a git synchronization step."""

    repository_path: Path
    commit_sha: str
    branch: str
    fetched: bool


class GitSyncService:
    """Service responsible for cloning and updating repositories."""

    def __init__(self, repo_root: Optional[Path] = None, depth: Optional[int] = None):
        self.repo_root = Path(repo_root or settings.code_repo_root)
        self.repo_root.mkdir(parents=True, exist_ok=True)
        self.depth = depth if depth is not None else settings.code_git_depth

    async def clone_or_pull(
        self,
        repo_url: str,
        branch: str,
        target_folder: Path,
        *,
        auth_type: str = "none",
        access_token: Optional[str] = None,
    ) -> GitSyncResult:
        """Clone the repository (or update it) into ``target_folder``."""

        repo_url_with_auth, sanitized_url = _build_authenticated_url(
            repo_url, auth_type=auth_type, access_token=access_token
        )
        target_folder = Path(target_folder)
        target_folder.parent.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env.setdefault("GIT_TERMINAL_PROMPT", "0")

        if not target_folder.exists():
            logger.info(
                "Cloning repository %s into %s (branch=%s, depth=%s)",
                sanitized_url,
                target_folder,
                branch,
                self.depth,
            )
            cmd = [
                "git",
                "clone",
                "--depth",
                str(self.depth),
                "--branch",
                branch,
                repo_url_with_auth,
                str(target_folder),
            ]
            await _run_command(cmd, env=env)
            fetched = True
        else:
            logger.info(
                "Updating repository %s in %s (branch=%s)",
                sanitized_url,
                target_folder,
                branch,
            )
            await _run_command(["git", "fetch", "origin", branch], cwd=target_folder, env=env)
            await _run_command([
                "git",
                "reset",
                "--hard",
                f"origin/{branch}",
            ], cwd=target_folder, env=env)
            fetched = False

        commit_sha = await _run_command(
            ["git", "rev-parse", "HEAD"], cwd=target_folder, env=env, capture_output=True
        )

        return GitSyncResult(
            repository_path=target_folder,
            commit_sha=commit_sha.strip(),
            branch=branch,
            fetched=fetched,
        )


async def validate_git_connection(
    repo_url: str,
    *,
    auth_type: str = "none",
    access_token: Optional[str] = None,
    branch: Optional[str] = None,
) -> Tuple[bool, str, List[str]]:
    """Validate that a git repository can be reached with the provided credentials."""

    repo_url_with_auth, sanitized_url = _build_authenticated_url(
        repo_url, auth_type=auth_type, access_token=access_token
    )
    env = os.environ.copy()
    env.setdefault("GIT_TERMINAL_PROMPT", "0")

    cmd = ["git", "ls-remote", "--heads", repo_url_with_auth]
    if branch:
        cmd.append(f"refs/heads/{branch}")

    try:
        output = await _run_command(cmd, env=env, capture_output=True, check=False)
        if hasattr(output, "stdout"):
            exit_code = output.returncode
            stdout = output.stdout or ""
            stderr = output.stderr or ""
        else:  # pragma: no cover - defensive branch
            exit_code = 0
            stdout = str(output)
            stderr = ""
    except subprocess.SubprocessError as exc:  # pragma: no cover - subprocess failure path
        message = _sanitize_message(str(exc), sanitized_url)
        return False, message, []

    if exit_code != 0:
        message = _sanitize_message(stderr or stdout or "git ls-remote failed", sanitized_url)
        return False, message, []

    branches = _parse_branches(stdout)
    if branch and f"refs/heads/{branch}" not in branches:
        return False, f"Branch '{branch}' not found for {sanitized_url}", _strip_branch_refs(branches)

    return True, f"Successfully validated {sanitized_url}", _strip_branch_refs(branches)


async def _run_command(
    command: List[str],
    *,
    cwd: Optional[Path] = None,
    env: Optional[dict] = None,
    capture_output: bool = False,
    check: bool = True,
):
    """Execute a shell command asynchronously."""

    loop = asyncio.get_running_loop()

    def _run_sync():
        sanitized_parts = []
        for part in command:
            if "@" in part and part.startswith("http"):
                parsed = urlparse(part)
                if parsed.username:
                    masked_netloc = part.replace(parsed.username, "***")
                    sanitized_parts.append(masked_netloc)
                    continue
            sanitized_parts.append(part)

        logger.debug("Executing command: %s", " ".join(sanitized_parts))
        result = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            env=env,
            capture_output=capture_output,
            text=True,
            check=check,
        )
        return result

    result = await loop.run_in_executor(None, _run_sync)

    if capture_output and check:
        return result.stdout  # type: ignore[return-value]
    return result


def _build_authenticated_url(
    repo_url: str,
    *,
    auth_type: str = "none",
    access_token: Optional[str] = None,
) -> Tuple[str, str]:
    """Inject token credentials into the repo URL if required."""

    parsed = urlparse(repo_url)
    sanitized = urlunparse(parsed._replace(netloc=parsed.hostname or ""))

    if auth_type != "token" or not access_token:
        return repo_url, sanitized

    token = access_token.strip()
    if not token:
        return repo_url, sanitized

    netloc = f"{token}@{parsed.hostname}" if parsed.hostname else token
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"

    repo_with_auth = urlunparse(parsed._replace(netloc=netloc))
    return repo_with_auth, sanitized


def _sanitize_message(message: str, sanitized_url: str) -> str:
    """Remove repository credentials from log messages."""

    if "@" in message:
        parts = message.split("@")
        if parts:
            prefix = parts[0]
            if "https://" in prefix:
                message = message.replace(prefix + "@", "https://***@")
    return message.replace(sanitized_url.replace("https://", ""), sanitized_url)


def _parse_branches(stdout: str) -> List[str]:
    branches: List[str] = []
    for line in stdout.splitlines():
        if "refs/heads/" in line:
            parts = line.split()
            if len(parts) == 2:
                branches.append(parts[1])
    return branches


def _strip_branch_refs(branches: List[str]) -> List[str]:
    return [branch.replace("refs/heads/", "") for branch in branches]


__all__ = ["GitSyncService", "GitSyncResult", "validate_git_connection"]
