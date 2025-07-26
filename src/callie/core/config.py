"""Configuration management for inventory sync."""

import os
import logging
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


def setup_logging(level: str = "INFO") -> None:
    """Set up logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def load_environment(env_file: Optional[str] = None) -> None:
    """Load environment variables from .env file.
    
    Args:
        env_file: Path to .env file. If None, looks for .env in current directory.
    """
    if env_file:
        env_path = Path(env_file)
    else:
        env_path = Path('.env')
    
    if env_path.exists():
        load_dotenv(env_path)
        logging.info(f"Loaded environment from {env_path}")
    else:
        logging.warning(f"No .env file found at {env_path}")


def get_required_env(key: str) -> str:
    """Get a required environment variable.
    
    Args:
        key: Environment variable name
        
    Returns:
        Environment variable value
        
    Raises:
        ValueError: If the environment variable is not set
    """
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Required environment variable {key} is not set")
    return value


def get_optional_env(key: str, default: str = "") -> str:
    """Get an optional environment variable.
    
    Args:
        key: Environment variable name
        default: Default value if not set
        
    Returns:
        Environment variable value or default
    """
    return os.getenv(key, default) 