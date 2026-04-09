from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

try:
    # Load variables from a local .env file when available. This keeps
    # development convenient while still allowing production to rely on
    # real environment variables or secret managers.
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    # If python-dotenv is not installed or any other error occurs,
    # silently ignore and rely on the existing environment.
    pass


@dataclass(frozen=True)
class EnvConfig:
    """Simple access layer for environment-based configuration.

    It is intentionally minimal so that application code depends on
    this abstraction instead of touching os.environ directly.
    """

    project_function_url: Optional[str]
    access_token: Optional[str]

    @classmethod
    def from_env(cls) -> "EnvConfig":
        return cls(
            project_function_url=os.getenv("PROJECT_FUNCTION_URL"),
            access_token=os.getenv("ACCESS_TOKEN"),
        )
