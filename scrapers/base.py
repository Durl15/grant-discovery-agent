"""Abstract base class for all grant scrapers."""

from abc import ABC, abstractmethod
from typing import Any


class BaseScraper(ABC):
    """Base class that all grant source scrapers must inherit from."""

    name: str = "base"

    @abstractmethod
    def fetch(self, limit: int = 50) -> list[dict]:
        """Fetch grants from the source.

        Args:
            limit: Maximum number of grants to retrieve.

        Returns:
            A list of normalised grant dicts.
        """
        raise NotImplementedError

    def _normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Merge *raw* dict with a skeleton of required grant fields.

        Guarantees that every grant dict returned by a scraper contains the
        full set of expected keys, with ``None`` / empty-string defaults for
        anything the raw payload did not supply.

        Args:
            raw: The raw grant dict produced by the concrete scraper.

        Returns:
            A new dict that is the skeleton merged with *raw*.  The ``source``
            field is always overwritten to match ``self.name``.
        """
        skeleton: dict[str, Any] = {
            "id": "",
            "title": "",
            "agency": "",
            "source": self.name,
            "amount_min": None,
            "amount_max": None,
            "deadline": "",
            "description": "",
            "url": "",
        }
        merged = {**skeleton, **raw}
        # Always stamp the source with the scraper's own name so callers can
        # trust it even if the raw dict happened to include a different value.
        merged["source"] = self.name
        return merged
