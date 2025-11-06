"""Utilities for synchronizing Git repositories used as knowledge sources."""

from __future__ import annotations

import asyncio
import io
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple
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


@dataclass
class GitDiffResult:
    """Result of git diff operation showing file changes."""

    added_files: List[str]
    modified_files: List[str]
    deleted_files: List[str]
    renamed_files: List[Tuple[str, str]]  # (old_path, new_path)
    previous_sha: str
    current_sha: str


class RepositoryClientError(RuntimeError):
    """Base error for repository client failures."""

    def __init__(self, message: str, sanitized_url: str) -> None:
        super().__init__(message)
        self.sanitized_url = sanitized_url


class RepositoryAuthenticationError(RepositoryClientError):
    """Authentication or authorization failure."""


class MissingDependencyError(RepositoryClientError):
    """Raised when a required third-party library is not installed."""

    def __init__(self, dependency: str, sanitized_url: str) -> None:
        super().__init__(
            (
                f"Dependency '{dependency}' is required to manage repository {sanitized_url}. "
                f"Install it with `pip install {dependency}`."
            ),
            sanitized_url,
        )
        self.dependency = dependency


class RepositoryClient:
    """Abstract base class for repository operations."""

    def __init__(self, sanitized_url: str) -> None:
        self.sanitized_url = sanitized_url

    def download_branch(
        self,
        branch: str,
        target_folder: Path,
        *,
        depth: Optional[int] = None,
    ) -> str:
        raise NotImplementedError

    def list_branches(self) -> List[str]:
        raise NotImplementedError


class GithubRepositoryClient(RepositoryClient):
    """Repository client backed by ghapi for GitHub repositories."""

    def __init__(self, repo_url: str, *, token: Optional[str] = None) -> None:
        parsed = urlparse(repo_url)
        scheme = parsed.scheme or "https"
        host = parsed.hostname or "github.com"
        path = parsed.path.strip("/")
        if path.endswith(".git"):
            path = path[:-4]
        if "/" not in path:
            sanitized_url = (
                f"{scheme}://{host}/{path}" if path else f"{scheme}://{host}"
            )
            raise RepositoryClientError("Invalid GitHub repository URL", sanitized_url)

        owner, repo = path.split("/", 1)
        sanitized_url = f"{scheme}://{host}/{owner}/{repo}"

        try:
            from ghapi.all import GhApi  # type: ignore
        except (
            ImportError
        ) as exc:  # pragma: no cover - exercised in environments missing ghapi
            raise MissingDependencyError("ghapi", sanitized_url) from exc

        super().__init__(sanitized_url)
        self._api = GhApi(token=token)
        self._owner = owner
        self._repo = repo
        self._token = token

    def download_branch(
        self,
        branch: str,
        target_folder: Path,
        *,
        depth: Optional[int] = None,
    ) -> str:
        try:
            branch_info = self._api.repos.get_branch(
                owner=self._owner, repo=self._repo, branch=branch
            )
        except Exception as exc:
            raise RepositoryAuthenticationError(
                _sanitize_message(str(exc), self.sanitized_url), self.sanitized_url
            ) from exc

        commit_sha = _extract_commit_sha(branch_info, self.sanitized_url)

        download_tarball = getattr(self._api.repos, "download_tarball", None)
        if not callable(download_tarball):
            logger.warning(
                "GhApi download_tarball unavailable for {}, falling back to git CLI",
                self.sanitized_url,
            )
            return self._clone_with_git(branch, target_folder, depth)

        try:
            archive_response = download_tarball(
                owner=self._owner, repo=self._repo, ref=branch
            )
            archive_bytes = _coerce_archive_bytes(archive_response, self.sanitized_url)
            _extract_archive_bytes(archive_bytes, target_folder, self.sanitized_url)
            return commit_sha
        except Exception as exc:
            logger.warning(
                "GhApi download failed for {} (fallback to git): {}",
                self.sanitized_url,
                exc,
            )
            return self._clone_with_git(branch, target_folder, depth)

    def _clone_with_git(
        self,
        branch: str,
        target_folder: Path,
        depth: Optional[int],
    ) -> str:
        repo_url = f"https://github.com/{self._owner}/{self._repo}.git"
        auth_type = "token" if self._token else "none"
        cli_client = GitCliRepositoryClient(
            repo_url,
            auth_type=auth_type,
            access_token=self._token,
        )
        return cli_client.download_branch(
            branch,
            target_folder,
            depth=depth,
        )

    def list_branches(self) -> List[str]:
        try:
            paginate = getattr(self._api, "paginate", None)
            if callable(paginate):
                branch_items = list(
                    paginate(
                        self._api.repos.list_branches,
                        owner=self._owner,
                        repo=self._repo,
                        per_page=100,
                    )
                )
            else:
                branch_items = self._api.repos.list_branches(
                    owner=self._owner, repo=self._repo, per_page=100
                )
                if not isinstance(branch_items, list):
                    branch_items = list(branch_items)
        except Exception as exc:
            raise RepositoryAuthenticationError(
                _sanitize_message(str(exc), self.sanitized_url), self.sanitized_url
            ) from exc

        return _extract_branch_names(branch_items)


class GitlabRepositoryClient(RepositoryClient):
    """Repository client backed by python-gitlab for GitLab repositories."""

    def __init__(self, repo_url: str, *, token: Optional[str] = None) -> None:
        parsed = urlparse(repo_url)
        scheme = parsed.scheme or "https"
        host = parsed.netloc or parsed.hostname or "gitlab.com"
        base_url = f"{scheme}://{host}"

        path = parsed.path.strip("/")
        if path.endswith(".git"):
            path = path[:-4]
        if not path:
            raise RepositoryClientError("Invalid GitLab repository URL", base_url)

        sanitized_url = f"{base_url}/{path}"

        try:
            import gitlab  # type: ignore
        except (
            ImportError
        ) as exc:  # pragma: no cover - exercised when dependency missing
            raise MissingDependencyError("python-gitlab", sanitized_url) from exc

        super().__init__(sanitized_url)
        self._gitlab = gitlab
        self._base_url = base_url
        self._project_path = path
        self._token = token

    def _get_project(self):
        gl = self._gitlab.Gitlab(self._base_url, private_token=self._token)
        if self._token:
            try:
                gl.auth()
            except Exception as exc:
                raise RepositoryAuthenticationError(
                    _sanitize_message(str(exc), self.sanitized_url), self.sanitized_url
                ) from exc
        try:
            return gl.projects.get(self._project_path)
        except Exception as exc:
            raise RepositoryAuthenticationError(
                _sanitize_message(str(exc), self.sanitized_url), self.sanitized_url
            ) from exc

    def download_branch(
        self,
        branch: str,
        target_folder: Path,
        *,
        depth: Optional[int] = None,
    ) -> str:
        project = self._get_project()
        try:
            branch_obj = project.branches.get(branch)
        except Exception as exc:
            raise RepositoryAuthenticationError(
                _sanitize_message(str(exc), self.sanitized_url), self.sanitized_url
            ) from exc

        commit_sha = _extract_commit_sha(branch_obj, self.sanitized_url)

        try:
            archive_response = project.repository_archive(sha=branch, format="tar.gz")
        except Exception as exc:
            raise RepositoryClientError(
                _sanitize_message(str(exc), self.sanitized_url), self.sanitized_url
            ) from exc

        archive_bytes = _coerce_archive_bytes(archive_response, self.sanitized_url)
        _extract_archive_bytes(archive_bytes, target_folder, self.sanitized_url)
        return commit_sha

    def list_branches(self) -> List[str]:
        project = self._get_project()
        try:
            branch_items = project.branches.list(all=True)
        except Exception as exc:
            raise RepositoryAuthenticationError(
                _sanitize_message(str(exc), self.sanitized_url), self.sanitized_url
            ) from exc

        if not isinstance(branch_items, list):
            branch_items = list(branch_items)
        return _extract_branch_names(branch_items)


class GitCliRepositoryClient(RepositoryClient):
    """Fallback repository client using local git CLI operations."""

    def __init__(
        self,
        repo_url: str,
        *,
        auth_type: str = "none",
        access_token: Optional[str] = None,
    ) -> None:
        repo_with_auth, sanitized_url = _build_authenticated_url(
            repo_url, auth_type=auth_type, access_token=access_token
        )
        super().__init__(sanitized_url)
        self._repo_with_auth = repo_with_auth
        self._auth_type = auth_type
        self._access_token = access_token

    def download_branch(
        self,
        branch: str,
        target_folder: Path,
        *,
        depth: Optional[int] = None,
    ) -> str:
        target_folder = Path(target_folder)
        target_folder.parent.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env.setdefault("GIT_TERMINAL_PROMPT", "0")

        if not target_folder.exists():
            logger.info(
                "Cloning repository {} into {} (branch={}, depth={})",
                self.sanitized_url,
                target_folder,
                branch,
                depth,
            )
            cmd: List[str] = ["git", "clone"]
            if depth:
                cmd.extend(["--depth", str(depth)])
            cmd.extend(["--branch", branch, self._repo_with_auth, str(target_folder)])
            _run_git_command(cmd, env=env)
        else:
            logger.info(
                "Updating repository {} in {} (branch={})",
                self.sanitized_url,
                target_folder,
                branch,
            )
            _run_git_command(
                ["git", "fetch", "origin", branch], cwd=target_folder, env=env
            )
            _run_git_command(
                ["git", "reset", "--hard", f"origin/{branch}"],
                cwd=target_folder,
                env=env,
            )

        commit_result = _run_git_command(
            ["git", "rev-parse", "HEAD"],
            cwd=target_folder,
            env=env,
            capture_output=True,
        )
        commit_sha = (commit_result.stdout or "").strip()
        if not commit_sha:
            raise RepositoryClientError(
                f"Failed to resolve commit SHA for {self.sanitized_url}",
                self.sanitized_url,
            )
        return commit_sha

    def list_branches(self) -> List[str]:
        env = os.environ.copy()
        env.setdefault("GIT_TERMINAL_PROMPT", "0")

        result = _run_git_command(
            ["git", "ls-remote", "--heads", self._repo_with_auth],
            env=env,
            capture_output=True,
            check=False,
        )

        exit_code = getattr(result, "returncode", 0)
        stdout = getattr(result, "stdout", "") or ""
        stderr = getattr(result, "stderr", "") or ""
        if exit_code != 0:
            raise RepositoryAuthenticationError(
                _sanitize_message(
                    stderr or stdout or "git ls-remote failed", self.sanitized_url
                ),
                self.sanitized_url,
            )

        branches = _parse_branches(stdout)
        return _strip_branch_refs(branches)


class GitSyncService:
    """Service responsible for cloning and updating repositories."""

    def __init__(self, repo_root: Optional[Path] = None, depth: Optional[int] = None):
        base_root = (
            Path(repo_root) if repo_root is not None else settings.code_repo_root_path
        )
        base_root.mkdir(parents=True, exist_ok=True)
        self.repo_root = base_root
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

        target_folder = Path(target_folder)
        target_folder.parent.mkdir(parents=True, exist_ok=True)
        client = _resolve_repository_client(
            repo_url,
            auth_type=auth_type,
            access_token=access_token,
        )

        previous_sha = _read_commit_marker(target_folder)
        logger.info(
            "Syncing repository {} into {} (branch={})",
            client.sanitized_url,
            target_folder,
            branch,
        )

        commit_sha = await asyncio.to_thread(
            client.download_branch,
            branch,
            target_folder,
            depth=self.depth,
        )

        fetched = previous_sha != commit_sha
        _write_commit_marker(target_folder, commit_sha)

        return GitSyncResult(
            repository_path=target_folder,
            commit_sha=commit_sha,
            branch=branch,
            fetched=fetched,
        )

    async def get_changed_files(
        self,
        repo_path: Path,
        previous_sha: str,
        current_sha: Optional[str] = None,
    ) -> GitDiffResult:
        """
        Get the list of changed files between two commits using git diff.

        Args:
            repo_path: Path to the git repository
            previous_sha: Previous commit SHA to compare from
            current_sha: Current commit SHA to compare to (defaults to HEAD)

        Returns:
            GitDiffResult containing lists of added, modified, deleted, and renamed files
        """
        repo_path = Path(repo_path)

        if not repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")

        # If current_sha is not provided, use HEAD
        if not current_sha:
            result = await asyncio.to_thread(
                _run_git_command,
                ["git", "rev-parse", "HEAD"],
                cwd=repo_path,
                capture_output=True,
            )
            current_sha = (result.stdout or "").strip()

        logger.info(
            "Getting changed files between {} and {} in {}",
            previous_sha[:8],
            current_sha[:8],
            repo_path,
        )

        # Get diff with file status
        # --name-status shows: A (added), M (modified), D (deleted), R (renamed)
        result = await asyncio.to_thread(
            _run_git_command,
            ["git", "diff", "--name-status", previous_sha, current_sha],
            cwd=repo_path,
            capture_output=True,
        )

        diff_output = (result.stdout or "").strip()

        added_files = []
        modified_files = []
        deleted_files = []
        renamed_files = []

        if diff_output:
            for line in diff_output.split("\n"):
                line = line.strip()
                if not line:
                    continue

                parts = line.split("\t")
                if len(parts) < 2:
                    continue

                status = parts[0]

                if status.startswith("A"):
                    # Added file
                    added_files.append(parts[1])
                elif status.startswith("M"):
                    # Modified file
                    modified_files.append(parts[1])
                elif status.startswith("D"):
                    # Deleted file
                    deleted_files.append(parts[1])
                elif status.startswith("R"):
                    # Renamed file (format: R100\told_path\tnew_path)
                    if len(parts) >= 3:
                        renamed_files.append((parts[1], parts[2]))
                    elif len(parts) == 2:
                        # Sometimes git shows rename as "R\told_path -> new_path"
                        if " -> " in parts[1]:
                            old_path, new_path = parts[1].split(" -> ", 1)
                            renamed_files.append((old_path.strip(), new_path.strip()))

        logger.info(
            "Changed files: {} added, {} modified, {} deleted, {} renamed",
            len(added_files),
            len(modified_files),
            len(deleted_files),
            len(renamed_files),
        )

        return GitDiffResult(
            added_files=added_files,
            modified_files=modified_files,
            deleted_files=deleted_files,
            renamed_files=renamed_files,
            previous_sha=previous_sha,
            current_sha=current_sha,
        )


async def validate_git_connection(
    repo_url: str,
    *,
    auth_type: str = "none",
    access_token: Optional[str] = None,
    branch: Optional[str] = None,
) -> Tuple[bool, str, List[str]]:
    """Validate that a git repository can be reached with the provided credentials."""

    try:
        client = _resolve_repository_client(
            repo_url,
            auth_type=auth_type,
            access_token=access_token,
        )
    except MissingDependencyError as exc:
        return False, str(exc), []
    except RepositoryClientError as exc:
        return False, str(exc), []

    def _check() -> Tuple[bool, str, List[str]]:
        try:
            branches = client.list_branches()
        except RepositoryAuthenticationError as exc:
            return False, str(exc), []
        except RepositoryClientError as exc:
            return False, str(exc), []

        if branch and branch not in branches:
            return (
                False,
                f"Branch '{branch}' not found for {client.sanitized_url}",
                branches,
            )

        return True, f"Successfully validated {client.sanitized_url}", branches

    return await asyncio.to_thread(_check)


def _resolve_repository_client(
    repo_url: str,
    *,
    auth_type: str,
    access_token: Optional[str],
) -> RepositoryClient:
    parsed = urlparse(repo_url)
    host = (parsed.hostname or "").lower()
    token = access_token if auth_type == "token" and access_token else None

    if "github.com" in host:
        return GithubRepositoryClient(repo_url, token=token)
    if "gitlab" in host:
        return GitlabRepositoryClient(repo_url, token=token)

    return GitCliRepositoryClient(
        repo_url, auth_type=auth_type, access_token=access_token
    )


def _read_commit_marker(target_folder: Path) -> Optional[str]:
    marker = target_folder / ".code_index_commit"
    try:
        if marker.exists():
            return marker.read_text().strip() or None
    except OSError:
        return None
    return None


def _write_commit_marker(target_folder: Path, commit_sha: str) -> None:
    marker = target_folder / ".code_index_commit"
    try:
        marker.write_text(commit_sha)
    except OSError:
        logger.debug("Failed to write commit marker for {}", target_folder)


def _extract_commit_sha(branch_info, sanitized_url: str) -> str:
    commit = None
    if isinstance(branch_info, dict):
        commit = branch_info.get("commit")
    else:
        commit = getattr(branch_info, "commit", None)
    if isinstance(commit, dict):
        sha = commit.get("sha") or commit.get("id")
    else:
        sha = getattr(commit, "sha", None) or getattr(commit, "id", None)
    if not sha:
        raise RepositoryClientError(
            f"Unable to determine commit SHA for {sanitized_url}", sanitized_url
        )
    return str(sha)


def _extract_branch_names(items: Sequence) -> List[str]:
    names: List[str] = []
    for item in items:
        if isinstance(item, dict):
            name = item.get("name")
        else:
            name = getattr(item, "name", None)
        if name:
            names.append(str(name))
    return names


def _coerce_archive_bytes(value, sanitized_url: str) -> bytes:
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value)
    if hasattr(value, "read") and callable(value.read):
        data = value.read()
        if isinstance(data, (bytes, bytearray, memoryview)):
            return bytes(data)
    if hasattr(value, "content"):
        content = value.content
        if isinstance(content, (bytes, bytearray, memoryview)):
            return bytes(content)
    raise RepositoryClientError(
        f"Unsupported archive payload type from repository {sanitized_url}",
        sanitized_url,
    )


def _extract_archive_bytes(
    archive_bytes: bytes, target_folder: Path, sanitized_url: str
) -> None:
    try:
        with tempfile.TemporaryDirectory(prefix="repo-archive-") as tmp_dir:
            tmp_path = Path(tmp_dir)
            if not _try_extract_tar(archive_bytes, tmp_path, sanitized_url):
                if not _try_extract_zip(archive_bytes, tmp_path, sanitized_url):
                    raise RepositoryClientError(
                        f"Unsupported archive format returned for {sanitized_url}",
                        sanitized_url,
                    )

            extracted_root = _determine_archive_root(tmp_path)
            if target_folder.exists():
                shutil.rmtree(target_folder)
            shutil.copytree(extracted_root, target_folder)
    except RepositoryClientError:
        raise
    except Exception as exc:
        raise RepositoryClientError(
            _sanitize_message(str(exc), sanitized_url), sanitized_url
        ) from exc


def _try_extract_tar(
    archive_bytes: bytes, destination: Path, sanitized_url: str
) -> bool:
    buffer = io.BytesIO(archive_bytes)
    try:
        with tarfile.open(fileobj=buffer, mode="r:*") as archive:
            _safe_extract_tar(archive, destination, sanitized_url)
        return True
    except RepositoryClientError:
        raise
    except tarfile.TarError:
        return False


def _try_extract_zip(
    archive_bytes: bytes, destination: Path, sanitized_url: str
) -> bool:
    buffer = io.BytesIO(archive_bytes)
    try:
        with zipfile.ZipFile(buffer) as archive:
            _safe_extract_zip(archive, destination, sanitized_url)
        return True
    except RepositoryClientError:
        raise
    except zipfile.BadZipFile:
        return False


def _safe_extract_tar(
    archive: tarfile.TarFile, destination: Path, sanitized_url: str
) -> None:
    destination = destination.resolve()
    for member in archive.getmembers():
        member_path = (destination / member.name).resolve()
        if not _is_within_directory(destination, member_path):
            raise RepositoryClientError(
                f"Archive contains unsafe paths for {sanitized_url}", sanitized_url
            )
    archive.extractall(destination)


def _safe_extract_zip(
    archive: zipfile.ZipFile, destination: Path, sanitized_url: str
) -> None:
    destination = destination.resolve()
    for member in archive.namelist():
        member_path = (destination / member).resolve()
        if not _is_within_directory(destination, member_path):
            raise RepositoryClientError(
                f"Archive contains unsafe paths for {sanitized_url}", sanitized_url
            )
    archive.extractall(destination)


def _determine_archive_root(tmp_path: Path) -> Path:
    entries = [entry for entry in tmp_path.iterdir() if entry.name not in {".", ".."}]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return tmp_path


def _is_within_directory(directory: Path, target: Path) -> bool:
    abs_directory = directory.resolve()
    abs_target = target.resolve()
    common = os.path.commonpath([str(abs_directory), str(abs_target)])
    return common == str(abs_directory)


def _run_git_command(
    command: Sequence[str],
    *,
    cwd: Optional[Path] = None,
    env: Optional[dict] = None,
    capture_output: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess:
    def sanitize_command_parts(parts: Iterable[str]) -> List[str]:
        return [_mask_sensitive_text(part) for part in parts]

    if isinstance(command, (list, tuple)):
        sanitized_parts = sanitize_command_parts(command)
        debug_command = " ".join(sanitized_parts)
    else:  # pragma: no cover - defensive branch for unexpected command types
        command = [str(command)]
        sanitized_parts = sanitize_command_parts(command)
        debug_command = " ".join(sanitized_parts)

    logger.debug("Executing command: {}", debug_command)

    try:
        result = subprocess.run(
            list(command),
            cwd=str(cwd) if cwd else None,
            env=env,
            capture_output=capture_output,
            text=True,
            check=check,
        )
    except subprocess.CalledProcessError as exc:
        sanitized_exc = subprocess.CalledProcessError(
            exc.returncode,
            sanitized_parts,
            output=exc.output,
            stderr=exc.stderr,
        )
        raise sanitized_exc from None

    return result


_URL_WITH_CREDS_PATTERN = re.compile(r"https?://[^\s]+", re.IGNORECASE)
_BASIC_AUTH_FRAGMENT = re.compile(r"(https?://)([^/@]+@)")


def _mask_sensitive_text(value: str) -> str:
    """Mask credentials within any Git-style URLs contained in ``value``."""

    if not isinstance(value, str):
        return str(value)

    def _replace(match: re.Match[str]) -> str:
        return _mask_url_credentials(match.group(0))

    return _URL_WITH_CREDS_PATTERN.sub(_replace, value)


def _mask_url_credentials(url: str) -> str:
    """Replace the credential portion of a URL with masked placeholders."""

    try:
        parsed = urlparse(url)
    except ValueError:  # pragma: no cover - defensive for malformed URLs
        return _BASIC_AUTH_FRAGMENT.sub(r"\1***@", url)

    if parsed.scheme not in {"http", "https"}:
        return url

    netloc = parsed.netloc
    if "@" not in netloc:
        return url

    hostname = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""

    if parsed.password is not None:
        userinfo = "***:***@"
    elif parsed.username is not None or "@" in netloc:
        userinfo = "***@"
    else:  # pragma: no cover - should be covered by previous checks
        userinfo = ""

    masked_netloc = f"{userinfo}{hostname}{port}" if userinfo else f"{hostname}{port}"
    return urlunparse(parsed._replace(netloc=masked_netloc))


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

    masked = _mask_sensitive_text(message)
    sanitized_host = sanitized_url.replace("https://", "").replace("http://", "")
    if sanitized_host:
        return masked.replace(sanitized_host, sanitized_url)
    return masked


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
