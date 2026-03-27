"""Email notifier: sends a plain-text grant digest via SMTP/STARTTLS."""

import os
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any


class EmailNotifier:
    """Send a grant digest to a configured recipient over SMTP with STARTTLS.

    All configuration is read from environment variables so that credentials
    are never hard-coded in source.

    Required environment variables::

        SMTP_HOST   — e.g. smtp.gmail.com
        SMTP_PORT   — e.g. 587
        SMTP_USER   — sender account username
        SMTP_PASS   — sender account password / app password
        NOTIFY_FROM — From: address (often same as SMTP_USER)
        NOTIFY_TO   — Recipient address

    Copy ``.env.example`` → ``.env`` and fill in your credentials, then run
    ``python run.py notify``.
    """

    def __init__(self) -> None:
        self._host = os.environ.get("SMTP_HOST", "")
        self._port = int(os.environ.get("SMTP_PORT", "587"))
        self._user = os.environ.get("SMTP_USER", "")
        self._password = os.environ.get("SMTP_PASS", "")
        self._from_addr = os.environ.get("NOTIFY_FROM", self._user)
        self._to_addr = os.environ.get("NOTIFY_TO", "")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def send_digest(self, grants: list[dict[str, Any]]) -> None:
        """Build and send a grant digest email.

        Args:
            grants: List of grant dicts (as returned by
                    :meth:`~api.storage.Storage.top`).

        Raises:
            ValueError: If required SMTP configuration is missing.
            smtplib.SMTPException: On any SMTP-level error.
        """
        self._validate_config()

        subject = self._build_subject(grants)
        body_plain = self._build_body(grants)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._from_addr
        msg["To"] = self._to_addr
        msg["X-Mailer"] = "grant-discovery-agent"

        msg.attach(MIMEText(body_plain, "plain", "utf-8"))

        with smtplib.SMTP(self._host, self._port, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(self._user, self._password)
            smtp.sendmail(self._from_addr, [self._to_addr], msg.as_string())

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _validate_config(self) -> None:
        """Raise :class:`ValueError` if any required env var is missing."""
        missing = []
        for name, value in [
            ("SMTP_HOST", self._host),
            ("SMTP_USER", self._user),
            ("SMTP_PASS", self._password),
            ("NOTIFY_TO", self._to_addr),
        ]:
            if not value:
                missing.append(name)
        if missing:
            raise ValueError(
                f"Missing required environment variable(s): "
                f"{', '.join(missing)}. "
                f"Copy .env.example → .env and fill in your SMTP credentials."
            )

    def _build_subject(self, grants: list[dict[str, Any]]) -> str:
        """Return the email subject line."""
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return (
            f"Grant Digest [{date_str}] — "
            f"{len(grants)} top opportunit{'y' if len(grants) == 1 else 'ies'}"
        )

    def _build_body(self, grants: list[dict[str, Any]]) -> str:
        """Build a plain-text digest body.

        Args:
            grants: Ordered list of grant dicts.

        Returns:
            Multi-line plain-text string suitable for an email body.
        """
        lines: list[str] = []
        lines.append("=" * 60)
        lines.append("GRANT DISCOVERY DIGEST")
        lines.append(
            datetime.now(timezone.utc).strftime("%A, %B %d %Y  %H:%M UTC")
        )
        lines.append("=" * 60)
        lines.append("")

        for rank, grant in enumerate(grants, start=1):
            score = grant.get("score", 0.0)
            amount_max = grant.get("amount_max")
            amount_str = _fmt_amount(amount_max)

            lines.append(f"#{rank}  {grant.get('title', 'Untitled')}")
            lines.append(f"    Score   : {score:.2f}")
            lines.append(f"    Agency  : {grant.get('agency', 'N/A')}")
            lines.append(f"    Amount  : {amount_str}")
            lines.append(
                f"    Deadline: {grant.get('deadline', 'N/A') or 'N/A'}"
            )
            lines.append(f"    Source  : {grant.get('source', 'N/A')}")
            lines.append(f"    URL     : {grant.get('url', 'N/A')}")
            lines.append("")

        lines.append("-" * 60)
        lines.append(
            "You are receiving this digest because you set up the "
            "grant-discovery-agent."
        )
        lines.append(
            "To change preferences edit data/profile.json and re-run "
            "'python run.py scan'."
        )
        lines.append("")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _fmt_amount(amount: Any) -> str:
    """Format a numeric amount for human display."""
    if amount is None:
        return "N/A"
    try:
        n = float(amount)
        if n >= 1_000_000:
            return f"${n / 1_000_000:.1f}M"
        if n >= 1_000:
            return f"${n / 1_000:.0f}K"
        return f"${n:.0f}"
    except (ValueError, TypeError):
        return str(amount)
