"""Post grant digests to a Slack channel via Incoming Webhooks."""

import json
import os
import urllib.request
import urllib.error


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


def _score_emoji(score):
    try:
        s = float(score)
        if s >= 0.7:
            return ":large_green_circle:"
        elif s >= 0.4:
            return ":large_yellow_circle:"
        return ":red_circle:"
    except (ValueError, TypeError):
        return ":white_circle:"


class SlackNotifier:
    """Send grant digests to Slack via an Incoming Webhook URL.

    Configure via the ``SLACK_WEBHOOK_URL`` environment variable, or pass
    the URL directly to the constructor.

    Usage::

        notifier = SlackNotifier()
        notifier.send_digest(grants, title="Weekly Grant Digest")
    """

    def __init__(self, webhook_url: str | None = None) -> None:
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL", "")
        if not self.webhook_url:
            raise ValueError(
                "No Slack webhook URL found. Set the SLACK_WEBHOOK_URL "
                "environment variable or pass webhook_url to SlackNotifier()."
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send_digest(
        self,
        grants: list[dict],
        title: str = "Grant Discovery Digest",
        max_cards: int = 10,
    ) -> None:
        """Post a rich Block Kit message summarising the top grants.

        Args:
            grants:    List of grant dicts (as returned by Storage.top).
            title:     Header text for the Slack message.
            max_cards: Show at most this many grant blocks (Slack limit is ~50).
        """
        payload = self._build_payload(grants[:max_cards], title)
        self._post(payload)

    def send_text(self, text: str) -> None:
        """Post a plain-text message (useful for quick alerts)."""
        self._post({"text": text})

    # ------------------------------------------------------------------
    # Payload construction
    # ------------------------------------------------------------------

    def _build_payload(self, grants: list[dict], title: str) -> dict:
        blocks: list[dict] = []

        # ── Header ──────────────────────────────────────────────────────
        blocks.append({
            "type": "header",
            "text": {"type": "plain_text", "text": title, "emoji": True},
        })

        if not grants:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "_No grants found. Run `scan` first._"},
            })
            return {"blocks": blocks}

        # ── Summary context ──────────────────────────────────────────────
        scores = [g.get("score", 0) for g in grants]
        sources = ", ".join(sorted({g.get("source", "?") for g in grants}))
        blocks.append({
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"*{len(grants)} opportunities* | Sources: {sources} | Top score: *{max(scores):.2f}*"},
            ],
        })
        blocks.append({"type": "divider"})

        # ── One section per grant ────────────────────────────────────────
        for rank, g in enumerate(grants, 1):
            score = g.get("score", 0)
            emoji = _score_emoji(score)
            amount = _fmt_amount(g.get("amount_max"))
            deadline = g.get("deadline") or "N/A"
            agency = g.get("agency") or "N/A"
            url = g.get("url", "")
            title_text = g.get("title", "Untitled")

            # Title line: linked if we have a URL
            if url:
                title_md = f"*<{url}|{title_text}>*"
            else:
                title_md = f"*{title_text}*"

            text_md = (
                f"{emoji}  {rank}. {title_md}\n"
                f">Agency: *{agency}* · Amount: *{amount}* · Deadline: {deadline} · Score: `{score:.2f}`"
            )

            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": text_md},
            })

        blocks.append({"type": "divider"})
        blocks.append({
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "Sent by *Grant Discovery Agent* · `python run.py share --slack`"},
            ],
        })

        return {"blocks": blocks}

    # ------------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------------

    def _post(self, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = resp.read().decode()
                if body.strip() != "ok":
                    raise RuntimeError(f"Slack responded with: {body!r}")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise RuntimeError(f"Slack HTTP {exc.code}: {detail}") from exc
