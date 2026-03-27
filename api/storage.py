"""SQLite-backed persistence layer for scored grant records."""

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any

_DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "grants.db"
)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS grants (
    id          TEXT PRIMARY KEY,
    title       TEXT,
    agency      TEXT,
    source      TEXT,
    amount_min  REAL,
    amount_max  REAL,
    deadline    TEXT,
    description TEXT,
    url         TEXT,
    score       REAL,
    raw         TEXT,
    first_seen  TEXT,
    last_seen   TEXT
);
"""

_UPSERT_SQL = """
INSERT INTO grants (
    id, title, agency, source,
    amount_min, amount_max, deadline, description, url,
    score, raw, first_seen, last_seen
) VALUES (
    :id, :title, :agency, :source,
    :amount_min, :amount_max, :deadline, :description, :url,
    :score, :raw, :first_seen, :last_seen
)
ON CONFLICT(id) DO UPDATE SET
    title       = excluded.title,
    agency      = excluded.agency,
    source      = excluded.source,
    amount_min  = excluded.amount_min,
    amount_max  = excluded.amount_max,
    deadline    = excluded.deadline,
    description = excluded.description,
    url         = excluded.url,
    score       = excluded.score,
    raw         = excluded.raw,
    last_seen   = excluded.last_seen;
"""

_SELECT_TOP_SQL = """
SELECT id, title, agency, source,
       amount_min, amount_max, deadline, description, url,
       score, raw, first_seen, last_seen
FROM grants
WHERE score >= :min_score
ORDER BY score DESC
LIMIT :n;
"""


class Storage:
    """Thin SQLite wrapper for persisting and querying scored grants.

    The database file is created automatically on first use at
    ``<package-root>/data/grants.db`` (or a custom path passed to the
    constructor).

    Usage::

        storage = Storage()
        new_count = storage.upsert_many(scored_grants)
        top_grants = storage.top(n=10, min_score=0.3)
        storage.close()
    """

    def __init__(self, db_path: str | None = None) -> None:
        resolved = os.path.abspath(
            db_path if db_path is not None else _DEFAULT_DB_PATH
        )
        # Ensure the parent directory exists (e.g. data/ might not yet exist
        # in a fresh checkout).
        os.makedirs(os.path.dirname(resolved), exist_ok=True)

        self._conn = sqlite3.connect(resolved)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute(_CREATE_TABLE_SQL)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def upsert_many(
        self, scored_grants: list[tuple[dict[str, Any], float]]
    ) -> int:
        """Insert or update a batch of scored grants.

        For each ``(grant_dict, score)`` pair the row is inserted on first
        encounter (``first_seen`` is set) or updated in-place on subsequent
        encounters (``last_seen`` is refreshed, ``first_seen`` is preserved
        thanks to the UPSERT semantics).

        Args:
            scored_grants: List of ``(grant_dict, score_float)`` tuples as
                           produced by :class:`~matching.scorer.Scorer`.

        Returns:
            Number of *new* grants inserted (i.e. not previously in the DB).
        """
        now_utc = datetime.now(timezone.utc).isoformat()
        new_count = 0

        cursor = self._conn.cursor()
        for grant, score in scored_grants:
            grant_id = grant.get("id", "")

            # Check whether this grant already exists so we can preserve its
            # original first_seen timestamp.
            cursor.execute(
                "SELECT first_seen FROM grants WHERE id = ?", (grant_id,)
            )
            existing = cursor.fetchone()
            is_new = existing is None

            first_seen = now_utc if is_new else existing["first_seen"]

            params = {
                "id": grant_id,
                "title": grant.get("title", ""),
                "agency": grant.get("agency", ""),
                "source": grant.get("source", ""),
                "amount_min": _to_float(grant.get("amount_min")),
                "amount_max": _to_float(grant.get("amount_max")),
                "deadline": grant.get("deadline", ""),
                "description": grant.get("description", ""),
                "url": grant.get("url", ""),
                "score": score,
                "raw": json.dumps(grant),
                "first_seen": first_seen,
                "last_seen": now_utc,
            }
            cursor.execute(_UPSERT_SQL, params)

            if is_new:
                new_count += 1

        self._conn.commit()
        return new_count

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def top(
        self, n: int = 10, min_score: float = 0.0
    ) -> list[dict[str, Any]]:
        """Return the top-*n* grants ordered by descending score.

        Args:
            n: Maximum number of results to return.
            min_score: Only include grants whose score is at least this value.

        Returns:
            List of grant dicts (all columns included).
        """
        cursor = self._conn.execute(
            _SELECT_TOP_SQL, {"n": n, "min_score": min_score}
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Flush pending writes and close the database connection."""
        self._conn.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_float(value: Any) -> float | None:
    """Coerce *value* to float, returning ``None`` on failure."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
