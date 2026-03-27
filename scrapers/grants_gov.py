"""Scraper for Grants.gov opportunity search API."""

import requests

from .base import BaseScraper


class GrantsGovScraper(BaseScraper):
    """Fetch open / forecasted opportunities from the Grants.gov REST API."""

    name = "grants.gov"

    _SEARCH_URL = (
        "https://apply07.grants.gov/grantsws/rest/opportunities/search/"
    )

    def fetch(self, limit: int = 50) -> list[dict]:
        """Return up to *limit* opportunities from Grants.gov.

        Hits the JSON search endpoint and normalises each hit into the
        standard grant dict shape.

        Args:
            limit: Maximum number of opportunity records to request.

        Returns:
            List of normalised grant dicts.
        """
        payload = {
            "rows": limit,
            "oppStatuses": "forecasted|posted",
        }

        response = requests.post(
            self._SEARCH_URL,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()
        opps = data.get("oppHits", [])

        grants: list[dict] = []
        for opp in opps:
            opp_id = opp.get("id", "")
            raw = {
                "id": f"gg-{opp_id}",
                "title": opp.get("title", ""),
                "agency": opp.get("agencyName", ""),
                "amount_max": opp.get("awardCeiling"),
                "amount_min": opp.get("awardFloor"),
                "deadline": opp.get("closeDate", ""),
                "description": opp.get("synopsis", ""),
                "url": (
                    f"https://www.grants.gov/search-results-detail/{opp_id}"
                ),
            }
            grants.append(self._normalize(raw))

        return grants
