"""
Git repository utilities for cloning and managing repositories.
"""

import logging
import os
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from typing import Generator

logger = logging.getLogger(__name__)


def is_local_path(path: str) -> bool:
    """
    Check if input is a local path vs a URL.

    Parameters
    ----------
    path : str
        Path or URL to check

    Returns
    -------
    bool
        True if path is a local directory, False if it's a URL
    """
    if os.path.isdir(path):
        return True

    url_schemes = ("http://", "https://", "git://", "ssh://", "git@")
    if path.startswith(url_schemes):
        return False

    return False


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


def resolve_repo_path(repo_url_or_path: str) -> tuple[str, bool]:
    """
    Resolve repository input to a local path.

    Parameters
    ----------
    repo_url_or_path : str
        Either a URL or local path

    Returns
    -------
    tuple[str, bool]
        (path, should_cleanup) - path to use and whether it needs cleanup

    Raises
    ------
    FileNotFoundError
        If local path doesn't exist
    """
    if is_local_path(repo_url_or_path):
        if not os.path.exists(repo_url_or_path):
            raise FileNotFoundError(f"Local path not found: {repo_url_or_path}")
        return repo_url_or_path, False
    else:
        temp_dir = tempfile.mkdtemp(prefix="m4_repo_")
        clone_repository(repo_url_or_path, temp_dir)
        return temp_dir, True
