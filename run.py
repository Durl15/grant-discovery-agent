#!/usr/bin/env python3
"""Grant Discovery Agent CLI"""

import click
from dotenv import load_dotenv
load_dotenv()

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich import box

from scrapers import get_all_scrapers
from matching import Scorer, load_profile
from api import Storage

console = Console()

@click.group()
def cli():
    """Grant Discovery Agent - Find and rank funding opportunities."""
    pass

@cli.command()
@click.option('--sources', '-s', multiple=True, default=['all'], show_default=True, help='Sources: all, grants.gov, nsf, nih')
@click.option('--limit', '-l', default=50, show_default=True, help='Max grants per source')
def scan(sources, limit):
    """Scan grant sources and score against your profile."""
    profile = load_profile()
    storage = Storage()
    scorer = Scorer(profile)
    scrapers = get_all_scrapers(sources)

    console.print(Panel(f"[bold]Scanning {len(scrapers)} source(s)[/bold] | Profile: [cyan]{profile.get('organization','Default')}[/cyan]", style="blue"))

    total_new = 0
    total_seen = 0

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console, transient=False) as progress:
        for scraper in scrapers:
            task = progress.add_task(f"[cyan]Scanning {scraper.name}...[/cyan]", total=None)
            try:
                grants = scraper.fetch(limit=limit)
                scored = [(g, scorer.score(g)) for g in grants]
                new_count = storage.upsert_many(scored)
                total_new += new_count
                total_seen += len(grants)
                progress.update(task, description=f"[green]✓ {scraper.name}[/green]: {len(grants)} grants, {new_count} new")
            except Exception as e:
                progress.update(task, description=f"[red]✗ {scraper.name}[/red]: {e}")
            finally:
                progress.stop_task(task)

    console.print(f"\n[bold green]Scan complete.[/bold green] Processed [cyan]{total_seen}[/cyan] grants, [bold]{total_new} new[/bold] added to database.")
    storage.close()

@cli.command()
@click.option('--n', '-n', default=10, show_default=True, help='Number of top grants to show')
@click.option('--min-score', default=0.0, show_default=True, help='Minimum relevance score (0.0–1.0)')
def top(n, min_score):
    """Show top-ranked grants from last scan."""
    storage = Storage()
    grants = storage.top(n=n, min_score=min_score)
    storage.close()

    if not grants:
        console.print("[yellow]No grants found. Run:[/yellow] [bold]python run.py scan[/bold]")
        return

    table = Table(
        title=f"Top {len(grants)} Grant Opportunities",
        box=box.ROUNDED,
        show_lines=True,
        header_style="bold magenta",
    )
    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("Score", style="bold cyan", width=6, justify="center")
    table.add_column("Title", style="bold white", max_width=42)
    table.add_column("Agency", style="magenta", width=14)
    table.add_column("Amount", style="green", width=10, justify="right")
    table.add_column("Deadline", style="yellow", width=12)
    table.add_column("Source", style="dim", width=10)

    for i, g in enumerate(grants, 1):
        score = g.get('score', 0)
        score_str = f"{score:.2f}"
        if score >= 0.7:
            score_str = f"[green]{score_str}[/green]"
        elif score >= 0.4:
            score_str = f"[yellow]{score_str}[/yellow]"
        else:
            score_str = f"[red]{score_str}[/red]"

        table.add_row(
            str(i),
            score_str,
            g.get('title', 'N/A'),
            g.get('agency', 'N/A'),
            _fmt_amount(g.get('amount_max')),
            g.get('deadline', 'N/A') or 'N/A',
            g.get('source', 'N/A'),
        )

    console.print(table)
    console.print(f"\n[dim]Showing {len(grants)} of your stored grants. Use --n and --min-score to filter.[/dim]")

@cli.command()
@click.option('--format', '-f', 'fmt',
              type=click.Choice(['csv', 'json', 'html'], case_sensitive=False),
              default='html', show_default=True, help='Export format')
@click.option('--n', '-n', default=20, show_default=True, help='Number of grants to export')
@click.option('--min-score', default=0.0, show_default=True, help='Minimum score filter')
@click.option('--output', '-o', default=None, help='Output file path (auto-named if omitted)')
@click.option('--slack', 'send_slack', is_flag=True, default=False, help='Also post to Slack')
def share(fmt, n, min_score, output, send_slack):
    """Export top grants to CSV / JSON / HTML, and optionally post to Slack."""
    from sharing import CSVExporter, JSONExporter, HTMLExporter, SlackNotifier

    storage = Storage()
    grants = storage.top(n=n, min_score=min_score)
    storage.close()

    if not grants:
        console.print("[yellow]No grants found. Run:[/yellow] [bold]python run.py scan[/bold]")
        return

    # ── File export ────────────────────────────────────────────────────────
    exporter_map = {'csv': CSVExporter, 'json': JSONExporter, 'html': HTMLExporter}
    exporter = exporter_map[fmt.lower()]()
    try:
        path = exporter.export(grants, output_path=output)
        console.print(f"[green]✓[/green] Exported {len(grants)} grants → [bold]{path}[/bold]")
        if fmt.lower() == 'html':
            console.print(f"[dim]  Open in browser: file://{path}[/dim]")
    except Exception as e:
        console.print(f"[red]✗ Export failed:[/red] {e}")

    # ── Slack ──────────────────────────────────────────────────────────────
    if send_slack:
        try:
            notifier = SlackNotifier()
            notifier.send_digest(grants, title="Grant Discovery Digest")
            console.print(f"[green]✓[/green] Posted {len(grants)} grants to Slack.")
        except Exception as e:
            console.print(f"[red]✗ Slack failed:[/red] {e}")
            console.print("[dim]  Set SLACK_WEBHOOK_URL in your .env file.[/dim]")


@cli.command()
@click.option('--n', '-n', default=10, help='Number of grants to include in digest')
def notify(n):
    """Send a grant digest email (configure SMTP env vars first)."""
    from notifications import EmailNotifier
    storage = Storage()
    grants = storage.top(n=n)
    storage.close()

    if not grants:
        console.print("[yellow]No grants to send. Run scan first.[/yellow]")
        return

    notifier = EmailNotifier()
    try:
        notifier.send_digest(grants)
        console.print(f"[green]✓ Digest sent with {len(grants)} grants.[/green]")
    except Exception as e:
        console.print(f"[red]✗ Failed to send: {e}[/red]")
        console.print("[dim]Check your .env file or copy .env.example → .env[/dim]")

def _fmt_amount(amount):
    if amount is None:
        return 'N/A'
    try:
        n = float(amount)
        if n >= 1_000_000:
            return f"${n/1_000_000:.1f}M"
        elif n >= 1_000:
            return f"${n/1_000:.0f}K"
        return f"${n:.0f}"
    except (ValueError, TypeError):
        return str(amount)

if __name__ == '__main__':
    cli()
