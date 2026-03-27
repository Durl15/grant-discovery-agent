"""Quick smoke-test that can be run without network access."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))

from matching.profile import load_profile, DEFAULT_PROFILE
from matching.scorer import Scorer
from api.storage import Storage

# ── Profile ──────────────────────────────────────────────────────────────────
profile = load_profile()
assert "organization" in profile
assert isinstance(profile["keywords"], list)
print("load_profile OK  org=%s" % profile["organization"])

# ── Scorer ───────────────────────────────────────────────────────────────────
scorer = Scorer(profile)

high_match = {
    "id": "t-1",
    "title": "Machine Learning for Climate Change",
    "agency": "NSF",
    "source": "nsf",
    "amount_min": 10_000,
    "amount_max": 250_000,
    "deadline": "2026-06-30",
    "description": (
        "Artificial intelligence and sustainability for "
        "renewable energy and public health."
    ),
    "url": "https://example.com/1",
}
score = scorer.score(high_match)
print("score (high match) = %.4f" % score)
assert score > 0.5, "Expected score > 0.5, got %s" % score

excluded = dict(high_match, title="Defense Military Project",
                description="military defense operations")
excl_score = scorer.score(excluded)
assert excl_score == 0.0, "Excluded grant should score 0, got %s" % excl_score
print("exclude_keywords  OK")

# ── Storage ──────────────────────────────────────────────────────────────────
fd, db_path = tempfile.mkstemp(suffix=".db")
os.close(fd)
try:
    s = Storage(db_path=db_path)
    n1 = s.upsert_many([(high_match, score)])
    n2 = s.upsert_many([(high_match, score)])
    rows = s.top(n=5)
    s.close()
    assert n1 == 1, "First upsert should return 1 new, got %s" % n1
    assert n2 == 0, "Second upsert should return 0 new, got %s" % n2
    assert len(rows) == 1
    assert rows[0]["title"] == high_match["title"]
    print("Storage roundtrip OK  rows=%d" % len(rows))
finally:
    os.unlink(db_path)

# ── Scrapers package import ───────────────────────────────────────────────────
from scrapers import ALL_SCRAPERS, get_all_scrapers
assert len(ALL_SCRAPERS) == 3
all_s = get_all_scrapers(["all"])
assert len(all_s) == 3
nsf_only = get_all_scrapers(["nsf"])
assert len(nsf_only) == 1 and nsf_only[0].name == "nsf"
print("scrapers import   OK  count=%d" % len(ALL_SCRAPERS))

# ── Notifications import ──────────────────────────────────────────────────────
from notifications import EmailNotifier
n = EmailNotifier()
body = n._build_body([high_match])
assert "Machine Learning" in body
print("EmailNotifier     OK")

print("\nAll smoke tests passed.")
