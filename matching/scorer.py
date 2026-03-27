"""Relevance scorer: grades a grant dict against the user's profile."""

from typing import Any


class Scorer:
    """Score a grant dict against a loaded user profile.

    Scoring breakdown (max 1.0):

    * **0.0–0.6** — keyword coverage: fraction of ``keywords`` found in the
      grant's combined text, scaled to the 0–0.6 range.
    * **+0.3** — neutral bonus applied when *no* keywords are configured so
      that all grants receive a baseline score.
    * **0.0–0.2** — boost keywords: fraction of ``boost_keywords`` found,
      scaled to 0–0.2.
    * **+0.2 / ×0.5 / ×0.7** — amount fit: full bonus when the grant's
      ``amount_max`` sits within ``[min_amount, max_amount]``; a penalty
      multiplier when it falls outside that window.

    A grant whose text contains **any** ``exclude_keyword`` receives a hard
    score of ``0.0`` regardless of other criteria.
    """

    def __init__(self, profile: dict[str, Any]) -> None:
        self._keywords = [k.lower() for k in profile.get("keywords", [])]
        self._boost_keywords = [
            k.lower() for k in profile.get("boost_keywords", [])
        ]
        self._exclude_keywords = [
            k.lower() for k in profile.get("exclude_keywords", [])
        ]
        self._max_amount: float | None = profile.get("max_amount")
        self._min_amount: float | None = profile.get("min_amount")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def score(self, grant: dict[str, Any]) -> float:
        """Return a relevance score in the range ``[0.0, 1.0]``.

        Args:
            grant: A normalised grant dict (as returned by any scraper).

        Returns:
            Float score rounded to four decimal places.
        """
        text = self._get_text(grant)

        # Hard exclusion — immediately disqualify.
        for exc in self._exclude_keywords:
            if exc in text:
                return 0.0

        score = 0.0

        # ── Keyword coverage ──────────────────────────────────────────
        if self._keywords:
            hits = sum(1 for kw in self._keywords if kw in text)
            score += 0.6 * (hits / len(self._keywords))
        else:
            # No keywords configured → neutral baseline.
            score += 0.3

        # ── Boost keywords ────────────────────────────────────────────
        if self._boost_keywords:
            boost_hits = sum(
                1 for kw in self._boost_keywords if kw in text
            )
            score += 0.2 * (boost_hits / len(self._boost_keywords))

        # ── Amount fit ────────────────────────────────────────────────
        amount_raw = grant.get("amount_max")
        if amount_raw is not None:
            try:
                amount = float(amount_raw)
            except (ValueError, TypeError):
                amount = None

            if amount is not None:
                min_ok = (
                    self._min_amount is None or amount >= self._min_amount
                )
                max_ok = (
                    self._max_amount is None or amount <= self._max_amount
                )

                if min_ok and max_ok:
                    score += 0.2
                elif not min_ok:
                    # Award is too small — mild penalty.
                    score *= 0.5
                else:
                    # Award is too large — lighter penalty.
                    score *= 0.7

        return min(round(score, 4), 1.0)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_text(self, grant: dict[str, Any]) -> str:
        """Build a single lowercase string from the grant's text fields.

        Args:
            grant: A normalised grant dict.

        Returns:
            Concatenated lowercase string of title, description, and agency.
        """
        parts = [
            grant.get("title") or "",
            grant.get("description") or "",
            grant.get("agency") or "",
        ]
        return " ".join(parts).lower()
