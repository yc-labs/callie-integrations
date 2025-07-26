"""
Version management for Callie Integrations.
"""

import os
import subprocess
from typing import Optional

# Base version - update this for major releases
BASE_VERSION = "1.0.0"

def get_git_commit_sha() -> Optional[str]:
    """Get the current git commit SHA."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None

def get_git_tag() -> Optional[str]:
    """Get the current git tag if any."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--exact-match"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None

def get_version() -> str:
    """
    Get the current version.
    
    - If there's a git tag, use that
    - Otherwise use base version + git commit SHA
    - Fallback to base version
    """
    # Check for git tag first
    git_tag = get_git_tag()
    if git_tag and git_tag.startswith("v"):
        return git_tag[1:]  # Remove 'v' prefix
    elif git_tag:
        return git_tag
    
    # Use base version + commit SHA
    commit_sha = get_git_commit_sha()
    if commit_sha:
        return f"{BASE_VERSION}-{commit_sha}"
    
    # Fallback
    return BASE_VERSION

def get_docker_tag() -> str:
    """
    Get the Docker tag to use.
    
    - If there's a git tag, use that + 'latest'
    - Otherwise use git commit SHA + 'dev'
    """
    git_tag = get_git_tag()
    if git_tag:
        tag_version = git_tag[1:] if git_tag.startswith("v") else git_tag
        return tag_version
    
    commit_sha = get_git_commit_sha()
    if commit_sha:
        return f"dev-{commit_sha}"
    
    return "dev-latest"

# Export the version
__version__ = get_version()

if __name__ == "__main__":
    print(f"Version: {get_version()}")
    print(f"Docker tag: {get_docker_tag()}") 