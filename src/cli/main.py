"""
CLI interface for Project Sloppenhimer.
"""

import sys
from pathlib import Path
from typing import Optional

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# Configure loguru
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO",
)

app = typer.Typer(
    name="sloppenhimer",
    help="Automated Reddit story video generator with Minecraft gameplay.",
    add_completion=False,
)
console = Console()


@app.command()
def scrape(
    subreddits: Optional[list[str]] = typer.Option(
        None, "--sub", "-s", help="Subreddits to scrape (can specify multiple)"
    ),
    limit: int = typer.Option(25, "--limit", "-l", help="Posts per subreddit"),
    time_filter: str = typer.Option(
        "week", "--time", "-t", help="Time filter: hour/day/week/month/year/all"
    ),
):
    """Scrape stories from Reddit."""
    from src.scrapers import RedditScraper

    scraper = RedditScraper()

    if subreddits:
        scraper.settings.reddit.subreddits = list(subreddits)

    with console.status("[bold green]Scraping Reddit..."):
        stories = scraper.scrape_all(time_filter=time_filter)

    if not stories:
        console.print("[yellow]No stories found matching criteria.[/yellow]")
        return

    saved = scraper.save_stories(stories)
    console.print(f"[green]Scraped and saved {len(saved)} stories![/green]")

    # Show table of stories
    table = Table(title="Scraped Stories")
    table.add_column("ID", style="cyan")
    table.add_column("Subreddit", style="magenta")
    table.add_column("Score", justify="right")
    table.add_column("Words", justify="right")
    table.add_column("Title", max_width=40)

    for story in stories[:10]:
        table.add_row(
            story.id,
            f"r/{story.subreddit}",
            str(story.score),
            str(story.word_count),
            story.title[:40] + "..." if len(story.title) > 40 else story.title,
        )

    if len(stories) > 10:
        table.add_row("...", "...", "...", "...", f"(+{len(stories)-10} more)")

    console.print(table)


@app.command()
def fetch_videos(
    count: int = typer.Option(3, "--count", "-c", help="Number of videos to download"),
    query: Optional[str] = typer.Option(
        None, "--query", "-q", help="Custom search query"
    ),
):
    """Download Minecraft gameplay videos from YouTube."""
    from src.scrapers import YouTubeDownloader

    downloader = YouTubeDownloader()

    console.print(f"[bold]Searching and downloading {count} videos...[/bold]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Downloading...", total=count)

        videos = downloader.download_random(count=count, query=query)

        for _ in videos:
            progress.advance(task)

    if not videos:
        console.print("[yellow]No videos downloaded.[/yellow]")
        return

    console.print(f"[green]Downloaded {len(videos)} videos![/green]")

    for video in videos:
        console.print(f"  - {video.title[:50]}... ({video.duration_seconds:.0f}s)")


@app.command()
def list_stories():
    """List all scraped stories."""
    from src.scrapers import RedditScraper

    scraper = RedditScraper()
    story_ids = scraper.list_stories()

    if not story_ids:
        console.print("[yellow]No stories found. Run 'scrape' first.[/yellow]")
        return

    table = Table(title=f"Available Stories ({len(story_ids)})")
    table.add_column("ID", style="cyan")
    table.add_column("Subreddit", style="magenta")
    table.add_column("Score", justify="right")
    table.add_column("Words", justify="right")
    table.add_column("Title", max_width=50)

    for story_id in story_ids[:20]:
        story = scraper.load_story(story_id)
        if story:
            table.add_row(
                story.id,
                f"r/{story.subreddit}",
                str(story.score),
                str(story.word_count),
                story.title[:50] + "..." if len(story.title) > 50 else story.title,
            )

    if len(story_ids) > 20:
        console.print(f"[dim](Showing first 20 of {len(story_ids)} stories)[/dim]")

    console.print(table)


@app.command()
def list_videos():
    """List all downloaded videos."""
    from src.scrapers import YouTubeDownloader

    downloader = YouTubeDownloader()
    videos = downloader.list_videos()

    if not videos:
        console.print("[yellow]No videos found. Run 'fetch-videos' first.[/yellow]")
        return

    table = Table(title=f"Available Videos ({len(videos)})")
    table.add_column("ID", style="cyan")
    table.add_column("Duration", justify="right")
    table.add_column("Title", max_width=50)

    for video in videos:
        table.add_row(
            video.id,
            f"{video.duration_seconds:.0f}s",
            video.title[:50] + "..." if len(video.title) > 50 else video.title,
        )

    console.print(table)


@app.command()
def process(
    story_id: str = typer.Argument(help="Story ID to process"),
    quick: bool = typer.Option(
        False, "--quick", "-q", help="Quick mode (simpler captions, faster render)"
    ),
):
    """Process a story through the full pipeline."""
    from src.video import Pipeline

    pipeline = Pipeline()

    console.print(f"[bold]Processing story: {story_id}[/bold]")

    with console.status("[bold green]Running pipeline..."):
        output = pipeline.process_story(story_id, quick_mode=quick)

    if output:
        console.print(f"[green]Success! Video saved to:[/green]")
        console.print(f"  {output}")
    else:
        console.print("[red]Pipeline failed. Check logs for details.[/red]")


@app.command()
def check():
    """Check system dependencies and configuration."""
    from config.settings import get_settings

    settings = get_settings()

    console.print("[bold]Checking system dependencies...[/bold]\n")

    # Check FFmpeg
    import shutil
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        console.print(f"[green]✓[/green] FFmpeg: {ffmpeg_path}")
    else:
        console.print("[red]✗[/red] FFmpeg: Not found (run: brew install ffmpeg)")

    # Check Ollama
    try:
        import ollama
        models = ollama.list()
        model_names = [m.get("name", "") for m in models.get("models", [])]
        console.print(f"[green]✓[/green] Ollama: {len(model_names)} models available")
        if model_names:
            for name in model_names[:3]:
                console.print(f"    - {name}")
    except Exception as e:
        console.print(f"[red]✗[/red] Ollama: Not running (run: ollama serve)")

    # Check Reddit (YARS - no API needed)
    console.print(f"[green]✓[/green] Reddit: Using YARS (no API key required)")

    # Check directories
    console.print(f"\n[bold]Data directories:[/bold]")
    for name, path in [
        ("Stories", settings.stories_dir),
        ("Videos", settings.videos_dir),
        ("Audio", settings.audio_dir),
        ("Output", settings.output_dir),
    ]:
        exists = path.exists()
        files = len(list(path.glob("*"))) if exists else 0
        status = "[green]✓[/green]" if exists else "[yellow]![/yellow]"
        console.print(f"  {status} {name}: {path} ({files} files)")


@app.command()
def voices():
    """List available TTS voices."""
    from src.processors import TTSEngine

    console.print("[bold]Fetching available voices...[/bold]")

    with console.status("Loading..."):
        voices = TTSEngine.list_voices("en")

    table = Table(title=f"English TTS Voices ({len(voices)})")
    table.add_column("Voice ID", style="cyan")
    table.add_column("Gender")
    table.add_column("Locale")

    for voice in voices:
        table.add_row(
            voice["ShortName"],
            voice.get("Gender", "Unknown"),
            voice.get("Locale", ""),
        )

    console.print(table)


@app.callback()
def main():
    """
    Project Sloppenhimer - Reddit Story Video Generator

    Automatically creates short-form videos from Reddit stories
    with Minecraft gameplay backgrounds and TTS narration.
    """
    pass


if __name__ == "__main__":
    app()
