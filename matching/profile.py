"""Load and merge the user's grant-matching profile from disk."""

import json
import os
from typing import Any

# Sensible defaults used when the profile file is absent or incomplete.
DEFAULT_PROFILE: dict[str, Any] = {
    "organization": "My Organization",
    "keywords": [],
    "boost_keywords": [],
    "exclude_keywords": [],
    "max_amount": 500_000,
    "min_amount": 5_000,
}

# Path to the profile file relative to *this* source file.
_DEFAULT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "profile.json"
)


def load_profile(path: str | None = None) -> dict[str, Any]:
    """Load the user profile from *path* and merge with :data:`DEFAULT_PROFILE`.

    If *path* is ``None`` the default location
    ``<package-root>/data/profile.json`` is used.  Missing keys in the file
    are filled in from :data:`DEFAULT_PROFILE`, so callers can always rely on
    the full set of expected keys being present.

    Args:
        path: Optional explicit path to a JSON profile file.

    Returns:
        Merged profile dict guaranteed to contain all default keys.
    """
    resolved = os.path.abspath(path if path is not None else _DEFAULT_PATH)

    # Start from a fresh copy of the defaults so we never mutate the module-
    # level constant.
    profile = dict(DEFAULT_PROFILE)

    if os.path.isfile(resolved):
        try:
            with open(resolved, "r", encoding="utf-8") as fh:
                file_data: dict[str, Any] = json.load(fh)
            # Shallow merge: file values win over defaults.
            profile.update(file_data)
        except (json.JSONDecodeError, OSError):
            # Silently fall back to defaults if the file is unreadable or
            # malformed — better to run with defaults than to crash.
            pass

    return profile
