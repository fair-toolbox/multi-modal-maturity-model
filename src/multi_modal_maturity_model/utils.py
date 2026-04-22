"""
Git repository utilities for cloning and managing repositories.
"""

import logging
import os
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator

logger = logging.getLogger(__name__)


def detect_platform(url: str) -> str:
    """Detect repository platform (github/gitlab) from URL."""
    if url.startswith(("http://", "https://", "git@")):
        url_lower = url.lower()
        if "github.com" in url_lower:
            return "github"
        elif "gitlab" in url_lower:
            return "gitlab"
    raise ValueError(f"Could not detect supported platform from URL: {url}")


def extract_repo_identifier(repo_url: str, platform: str) -> str:
    """
    Extract repository identifier from URL.

    Examples
    --------
    - "https://github.com/owner/repo" -> "owner/repo"
    - "https://gitlab.com/owner/project" -> "owner/project"
    """
    if platform == "github":
        if "github.com/" in repo_url:
            parts = repo_url.split("github.com/")[1].split("/")
            repo = parts[1]
            if repo.endswith(".git"):
                repo = repo[:-4]
            return f"{parts[0]}/{repo}"
    elif platform == "gitlab":
        if "gitlab.com/" in repo_url:
            path = repo_url.split("gitlab.com/")[1]
            if path.endswith(".git"):
                path = path[:-4]
            return path.rstrip("/")
    return repo_url


def clone_repository(repo_url: str, target_dir: str) -> None:
    """
    Clone a git repository.

    Parameters
    ----------
    repo_url : str
        Repository URL to clone
    target_dir : str
        Target directory for clone

    Raises
    ------
    subprocess.CalledProcessError
        If git clone fails
    """
    logger.debug(f"Cloning {repo_url} to {target_dir}")

    result = subprocess.run(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "--single-branch",
            "--filter=blob:none",
            repo_url,
            target_dir,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=300,
    )

    if result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, result.args, result.stdout, result.stderr
        )

    logger.info(f"Successfully cloned {repo_url}")


@contextmanager
def temporary_clone(repo_url: str) -> Generator[str, None, None]:
    """
    Context manager for temporary repository cloning.

    Parameters
    ----------
    repo_url : str
        Repository URL to clone

    Yields
    ------
    str
        Path to cloned repository

    Example
    -------
    >>> with temporary_clone("https://github.com/user/repo") as repo_path:
    ...     # Work with repo
    ...     analyze(repo_path)
    """
    temp_dir = tempfile.mkdtemp(prefix="m4_repo_")
    logger.debug(f"Created temp directory: {temp_dir}")

    try:
        clone_repository(repo_url, temp_dir)
        yield temp_dir
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.debug(f"Cleaned up temp directory: {temp_dir}")


def calculate_days_since_last_commit(last_commit_date: str) -> int | None:
    """Calculate days since last commit."""
    try:
        dt = datetime.fromisoformat(last_commit_date.replace("Z", "+00:00"))
        now = datetime.now(dt.tzinfo or timezone.utc)
        return max(0, (now - dt).days)
    except ValueError:
        return None
