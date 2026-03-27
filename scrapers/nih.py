"""Scraper for the NIH Reporter Projects API."""

import datetime

import requests

from .base import BaseScraper


class NIHScraper(BaseScraper):
    """Fetch recent project awards from the NIH Reporter API v2."""

    name = "nih"

    _SEARCH_URL = "https://api.reporter.nih.gov/v2/projects/search"

    def fetch(self, limit: int = 50) -> list[dict]:
        """Return up to *limit* projects from the NIH Reporter API.

        Requests projects from the current and previous fiscal year, sorted by
        most-recent start date first.

        Args:
            limit: Maximum number of project records to retrieve (capped at 50
                   by the NIH Reporter API).

        Returns:
            List of normalised grant dicts.
        """
        current_year = datetime.date.today().year
        payload = {
            "criteria": {
                "fiscal_years": [current_year, current_year - 1],
            },
            "offset": 0,
            "limit": min(limit, 50),
            "sort_field": "project_start_date",
            "sort_order": "desc",
        }

        response = requests.post(
            self._SEARCH_URL,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()
        projects = data.get("results", [])

        grants: list[dict] = []
        for project in projects:
            appl_id = project.get("appl_id", "")

            # Description: prefer full abstract, fall back to public health
            # relevance statement.
            description = (
                project.get("abstract_text")
                or project.get("phr_text")
                or ""
            )

            raw = {
                "id": f"nih-{appl_id}",
                "title": project.get("project_title", ""),
                "agency": project.get("agency_code", "NIH"),
                "amount_max": project.get("award_amount"),
                "amount_min": None,
                "deadline": project.get("project_end_date", ""),
                "description": description,
                "url": f"https://reporter.nih.gov/project-details/{appl_id}",
            }
            grants.append(self._normalize(raw))

        return grants
