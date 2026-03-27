"""Export grant lists to CSV, JSON, or a standalone HTML report."""

import csv
import json
import os
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Helpers shared by all exporters
# ---------------------------------------------------------------------------

def _fmt_amount(amount):
    if amount is None:
        return "N/A"
    try:
        n = float(amount)
        if n >= 1_000_000:
            return f"${n / 1_000_000:.1f}M"
        elif n >= 1_000:
            return f"${n / 1_000:.0f}K"
        return f"${n:.0f}"
    except (ValueError, TypeError):
        return str(amount)


def _now_label():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")


def _default_path(directory, stem, ext):
    os.makedirs(directory, exist_ok=True)
    return os.path.join(directory, f"{stem}_{_now_label()}.{ext}")


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

COLUMNS = ["rank", "score", "title", "agency", "source",
           "amount_min", "amount_max", "deadline", "url", "description"]


class CSVExporter:
    """Write grants to a UTF-8 CSV file."""

    def export(self, grants: list[dict], output_path: str | None = None) -> str:
        path = output_path or _default_path(
            os.path.join(os.path.dirname(__file__), "..", "data"),
            "grants_export",
            "csv",
        )
        path = os.path.abspath(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore")
            writer.writeheader()
            for rank, g in enumerate(grants, 1):
                writer.writerow({
                    "rank": rank,
                    "score": f"{g.get('score', 0):.4f}",
                    "title": g.get("title", ""),
                    "agency": g.get("agency", ""),
                    "source": g.get("source", ""),
                    "amount_min": g.get("amount_min", ""),
                    "amount_max": g.get("amount_max", ""),
                    "deadline": g.get("deadline", ""),
                    "url": g.get("url", ""),
                    "description": (g.get("description", "") or "")[:300],
                })
        return path


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------

class JSONExporter:
    """Write grants to a pretty-printed JSON file."""

    def export(self, grants: list[dict], output_path: str | None = None) -> str:
        path = output_path or _default_path(
            os.path.join(os.path.dirname(__file__), "..", "data"),
            "grants_export",
            "json",
        )
        path = os.path.abspath(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)

        payload = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "count": len(grants),
            "grants": [
                {
                    "rank": rank,
                    "score": g.get("score", 0),
                    "title": g.get("title", ""),
                    "agency": g.get("agency", ""),
                    "source": g.get("source", ""),
                    "amount_min": g.get("amount_min"),
                    "amount_max": g.get("amount_max"),
                    "deadline": g.get("deadline", ""),
                    "url": g.get("url", ""),
                    "description": g.get("description", ""),
                }
                for rank, g in enumerate(grants, 1)
            ],
        }

        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        return path


# ---------------------------------------------------------------------------
# HTML report
# ---------------------------------------------------------------------------

_CARD_TMPL = """\
<div class="card">
  <div class="card-rank">#{rank}</div>
  <div class="card-body">
    <div class="card-title"><a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a></div>
    <div class="card-meta">
      <span class="badge score-{score_tier}">{score}</span>
      <span class="pill agency">{agency}</span>
      <span class="pill amount">{amount}</span>
      {deadline_html}
      <span class="pill source">{source}</span>
    </div>
    <div class="card-desc">{desc}</div>
  </div>
</div>"""

_ROW_TMPL = """\
      <tr>
        <td class="num">{rank}</td>
        <td><a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a></td>
        <td>{agency}</td>
        <td class="num"><span class="badge score-{score_tier}">{score}</span></td>
        <td class="num">{amount}</td>
        <td>{deadline}</td>
      </tr>"""

_PAGE_TMPL = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Grant Report — {date}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: system-ui, sans-serif; background: #f1f5f9; color: #1e293b; line-height: 1.6; }}
    a {{ color: #2563eb; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}

    /* Layout */
    header {{ background: linear-gradient(135deg,#1d4ed8,#1e40af); color:#fff; padding:40px 48px 32px; }}
    header h1 {{ font-size: 28px; font-weight: 800; margin-bottom: 4px; }}
    header p  {{ opacity: .75; font-size: 14px; }}
    .stats {{ display:flex; gap:32px; flex-wrap:wrap; background:#eff6ff; border-bottom:1px solid #bfdbfe; padding:14px 48px; }}
    .stat  {{ font-size:13px; color:#1e40af; font-weight:600; }}
    .stat span {{ color:#1e3a8a; }}
    main {{ max-width: 960px; margin: 32px auto; padding: 0 24px; }}
    section {{ margin-bottom: 48px; }}
    h2 {{ font-size:13px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase;
          color:#64748b; margin-bottom:18px; }}

    /* Cards */
    .card {{ display:flex; gap:16px; background:#fff; border:1px solid #e2e8f0;
             border-radius:10px; padding:20px; margin-bottom:14px;
             box-shadow:0 1px 3px rgba(0,0,0,.05); }}
    .card:hover {{ box-shadow:0 4px 12px rgba(0,0,0,.08); }}
    .card-rank {{ font-size:22px; font-weight:800; color:#cbd5e1; min-width:36px; padding-top:2px; }}
    .card-body {{ flex:1; min-width:0; }}
    .card-title {{ font-size:16px; font-weight:700; color:#0f172a; margin-bottom:8px; }}
    .card-meta  {{ display:flex; flex-wrap:wrap; gap:6px; margin-bottom:10px; }}
    .card-desc  {{ font-size:13px; color:#64748b; display:-webkit-box;
                   -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden; }}

    /* Pills & badges */
    .pill   {{ display:inline-block; border-radius:4px; padding:2px 8px; font-size:12px; font-weight:600; }}
    .agency {{ background:#f1f5f9; color:#475569; }}
    .amount {{ background:#d1fae5; color:#065f46; }}
    .source {{ background:#ede9fe; color:#5b21b6; }}
    .deadline-pill {{ background:#fef3c7; color:#92400e; }}
    .badge  {{ border-radius:999px; padding:2px 9px; font-size:12px; font-weight:700; }}
    .score-high {{ background:#d1fae5; color:#065f46; }}
    .score-mid  {{ background:#fef9c3; color:#78350f; }}
    .score-low  {{ background:#fee2e2; color:#991b1b; }}

    /* Table */
    .table-wrap {{ overflow-x:auto; }}
    table {{ width:100%; border-collapse:collapse; font-size:13px; background:#fff;
             border:1px solid #e2e8f0; border-radius:8px; overflow:hidden; }}
    th {{ background:#1d4ed8; color:#fff; padding:10px 14px; text-align:left;
          font-size:12px; font-weight:700; letter-spacing:.5px; white-space:nowrap; }}
    td {{ padding:10px 14px; border-bottom:1px solid #f1f5f9; vertical-align:top; }}
    tr:last-child td {{ border-bottom:none; }}
    tr:nth-child(even) td {{ background:#f8fafc; }}
    .num {{ text-align:right; white-space:nowrap; }}

    footer {{ text-align:center; padding:32px; font-size:12px; color:#94a3b8; }}
  </style>
</head>
<body>

<header>
  <h1>Grant Discovery Report</h1>
  <p>Generated {date} &nbsp;·&nbsp; {count} opportunities</p>
</header>

<div class="stats">
  <div class="stat">Top score: <span>{top_score}</span></div>
  <div class="stat">Sources: <span>{sources}</span></div>
  <div class="stat">Avg score: <span>{avg_score}</span></div>
</div>

<main>
  <section>
    <h2>Top Opportunities</h2>
    {cards}
  </section>

  <section>
    <h2>Quick Reference</h2>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>#</th><th>Title</th><th>Agency</th>
            <th>Score</th><th>Amount</th><th>Deadline</th>
          </tr>
        </thead>
        <tbody>
{rows}
        </tbody>
      </table>
    </div>
  </section>
</main>

<footer>
  Grant Discovery Agent &nbsp;·&nbsp; {date}
</footer>

</body>
</html>"""


def _score_tier(score):
    try:
        s = float(score)
        if s >= 0.7:
            return "high"
        elif s >= 0.4:
            return "mid"
        return "low"
    except (ValueError, TypeError):
        return "low"


class HTMLExporter:
    """Render grants as a standalone, self-contained HTML report."""

    def export(self, grants: list[dict], output_path: str | None = None) -> str:
        path = output_path or _default_path(
            os.path.join(os.path.dirname(__file__), "..", "data"),
            "grants_report",
            "html",
        )
        path = os.path.abspath(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)

        date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
        scores = [g.get("score", 0) for g in grants]
        sources = ", ".join(sorted({g.get("source", "?") for g in grants})) or "N/A"
        top_score = f"{max(scores):.2f}" if scores else "—"
        avg_score = f"{sum(scores) / len(scores):.2f}" if scores else "—"

        cards_html = "\n".join(
            _CARD_TMPL.format(
                rank=rank,
                url=g.get("url", "#"),
                title=self._esc(g.get("title", "Untitled")),
                score=f"{g.get('score', 0):.2f}",
                score_tier=_score_tier(g.get("score", 0)),
                agency=self._esc(g.get("agency", "N/A")),
                amount=_fmt_amount(g.get("amount_max")),
                deadline_html=(
                    f'<span class="pill deadline-pill">{self._esc(g["deadline"])}</span>'
                    if g.get("deadline") else ""
                ),
                source=self._esc(g.get("source", "")),
                desc=self._esc((g.get("description", "") or "")[:300]),
            )
            for rank, g in enumerate(grants, 1)
        )

        rows_html = "\n".join(
            _ROW_TMPL.format(
                rank=rank,
                url=g.get("url", "#"),
                title=self._esc(g.get("title", "Untitled")),
                agency=self._esc(g.get("agency", "N/A")),
                score=f"{g.get('score', 0):.2f}",
                score_tier=_score_tier(g.get("score", 0)),
                amount=_fmt_amount(g.get("amount_max")),
                deadline=self._esc(g.get("deadline", "") or "N/A"),
            )
            for rank, g in enumerate(grants, 1)
        )

        html = _PAGE_TMPL.format(
            date=date_str,
            count=len(grants),
            top_score=top_score,
            avg_score=avg_score,
            sources=sources,
            cards=cards_html,
            rows=rows_html,
        )

        with open(path, "w", encoding="utf-8") as fh:
            fh.write(html)
        return path

    @staticmethod
    def _esc(text: str) -> str:
        """Minimal HTML escaping."""
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
