"""Scrapers package — import all sources and expose helper utilities."""

from .grants_gov import GrantsGovScraper
from .nih import NIHScraper
from .nsf import NSFScraper

# Canonical list of every available scraper class.
ALL_SCRAPERS = [GrantsGovScraper, NIHScraper, NSFScraper]


def get_all_scrapers(sources=("all",)):
    """Return a list of instantiated scrapers based on the *sources* selector.

    Args:
        sources: An iterable of source name strings.  Pass ``("all",)`` (the
                 default) to get one instance of every scraper.  Otherwise
                 each entry is matched case-insensitively against the
                 ``name`` class attribute of each scraper.

    Returns:
        List of instantiated :class:`~scrapers.base.BaseScraper` objects.

    Example::

        scrapers = get_all_scrapers(["nsf", "nih"])
    """
    sources_lower = [s.lower() for s in sources]

    if "all" in sources_lower:
        return [cls() for cls in ALL_SCRAPERS]

    selected = []
    for cls in ALL_SCRAPERS:
        if cls.name.lower() in sources_lower:
            selected.append(cls())
    return selected
