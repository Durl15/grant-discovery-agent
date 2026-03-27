"""Scraper for the NSF Awards API."""

import requests

from .base import BaseScraper


class NSFScraper(BaseScraper):
    """Fetch recent awards from the NSF public awards API."""

    name = "nsf"

    _AWARDS_URL = "https://api.nsf.gov/services/v1/awards.json"

    def fetch(self, limit: int = 50) -> list[dict]:
        """Return up to *limit* awards from the NSF awards API.

        The NSF API caps individual responses at 25 records, so *limit* is
        clamped accordingly.

        Args:
            limit: Maximum number of award records to retrieve.

        Returns:
            List of normalised grant dicts.
        """
        params = {
            "offset": 1,
            "limit": min(limit, 25),
            "printFields": (
                "id,title,agency,fundsObligatedAmt,"
                "abstractText,awardee,date,expDate"
            ),
        }

        response = requests.get(
            self._AWARDS_URL,
            params=params,
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()
        awards = data.get("response", {}).get("award", [])

        grants: list[dict] = []
        for award in awards:
            award_id = award.get("id", "")

            # fundsObligatedAmt may come back as a string or None; coerce
            # carefully to avoid crashing on bad data.
            amount_raw = award.get("fundsObligatedAmt")
            try:
                amount_max = float(amount_raw) if amount_raw is not None else None
            except (ValueError, TypeError):
                amount_max = None

            raw = {
                "id": f"nsf-{award_id}",
                "title": award.get("title", ""),
                "agency": "NSF",
                "amount_max": amount_max,
                "amount_min": None,
                "deadline": award.get("expDate", ""),
                "description": award.get("abstractText", ""),
                "url": (
                    f"https://www.nsf.gov/awardsearch/showAward"
                    f"?AWD_ID={award_id}"
                ),
            }
            grants.append(self._normalize(raw))

        return grants
