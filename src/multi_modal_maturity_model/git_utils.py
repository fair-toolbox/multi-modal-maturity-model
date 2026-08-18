"""Git repository utilities for cloning and temporary management."""

import logging
import os
import shutil
import subprocess
import tempfile

from contextlib import contextmanager
from typing import Generator

logger = logging.getLogger(__name__)


def detect_platform(url: str) -> str:
    """Detect repository platform from URL."""
    if url.startswith(("http://", "https://", "git@")):
        url_lower = url.lower()
        if "github.com" in url_lower:
            return "github"
        elif "gitlab.com" in url_lower:
            return "gitlab"
    raise ValueError("unsupported URL. URL must start with http://, https://, or git@.")


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
