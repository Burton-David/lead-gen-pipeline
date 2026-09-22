"""Command-line interface for lead-gen-pipeline.

Commands:
    run         Scrape individual business websites listed in a CSV.
    chambers    Crawl Chamber of Commerce directories with the local LLM.
    test        Extract data from a single URL (no model required).
    export      Export stored leads to CSV.
    stats       Show database statistics.
    init        Initialize the database.
    config      Show the active configuration.
    setup-llm   Download the Qwen2-7B GGUF model.
"""

import asyncio
import csv
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from sqlalchemy import select

from lead_gen_pipeline.chamber_pipeline import run_chamber_pipeline
from lead_gen_pipeline.config import settings
from lead_gen_pipeline.database import get_async_session_local, init_db
from lead_gen_pipeline.models import Lead
from lead_gen_pipeline.pipeline import main_pipeline
from lead_gen_pipeline.utils import logger

app = typer.Typer(
    name="lead-gen",
    help="Extract structured business data from web pages and chamber directories.",
    add_completion=False,
)
console = Console()


def _spinner(description: str) -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    )


@app.command()
def run(
    input_file: Path | None = typer.Option(
        None,
        "--input",
        "-i",
        help="CSV of URLs to process (default: data/urls_seed.csv)",
    ),
    max_concurrency: int | None = typer.Option(
        None, "--concurrency", "-c", help="Maximum concurrent requests"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
) -> None:
    """Process individual business websites for data extraction."""
    if input_file:
        settings.INPUT_URLS_CSV = input_file
    if max_concurrency:
        settings.MAX_PIPELINE_CONCURRENCY = max_concurrency
    if verbose:
        settings.logging.LOG_LEVEL = "DEBUG"

    console.print("Starting business data extraction pipeline", style="bold green")
    console.print(f"Input file: {settings.INPUT_URLS_CSV}")
    console.print(f"Max concurrency: {settings.MAX_PIPELINE_CONCURRENCY}")
    console.print(f"Database: {settings.database.DATABASE_URL}")

    try:
        with _spinner("Processing websites...") as progress:
            task = progress.add_task("Processing websites...", total=None)
            asyncio.run(main_pipeline())
            progress.update(task, description="Pipeline completed")
        console.print("Pipeline completed successfully", style="bold green")
    except KeyboardInterrupt:
        console.print("Pipeline interrupted by user", style="bold red")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"Pipeline failed: {e}", style="bold red")
        logger.error(f"Pipeline execution failed: {e}")
        raise typer.Exit(1) from e


@app.command("chambers")
def run_chambers(
    input_file: Path | None = typer.Option(
        None,
        "--input",
        "-i",
        help="CSV of chamber URLs (default: data/chamber_urls.csv)",
    ),
    urls: list[str] | None = typer.Option(
        None, "--url", "-u", help="Individual chamber URLs to process"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
) -> None:
    """Process Chamber of Commerce directories with the local LLM."""
    if verbose:
        settings.logging.LOG_LEVEL = "DEBUG"

    console.print("Starting chamber directory processing", style="bold green")

    chamber_urls: list[str] = []
    if urls:
        chamber_urls = list(urls)
        console.print(f"Processing {len(chamber_urls)} chamber URLs from command line")
    elif input_file and input_file.exists():
        try:
            with open(input_file, encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    url = (row.get("url") or "").strip()
                    if url.startswith(("http://", "https://")):
                        chamber_urls.append(url)
            console.print(f"Loaded {len(chamber_urls)} chamber URLs from {input_file}")
        except Exception as e:
            console.print(f"Error loading chamber URLs: {e}", style="bold red")
            raise typer.Exit(1) from e
    else:
        console.print(
            "No chamber URLs provided. Use --input or --url.", style="bold red"
        )
        raise typer.Exit(1)

    if not chamber_urls:
        console.print("No valid chamber URLs found", style="bold red")
        raise typer.Exit(1)

    try:
        with _spinner("Processing chambers...") as progress:
            task = progress.add_task("Processing chambers...", total=None)
            result = asyncio.run(run_chamber_pipeline(chamber_urls))
            progress.update(task, description="Chamber processing completed")

        if result["success"]:
            console.print(
                "Chamber processing completed successfully", style="bold green"
            )
            console.print(
                f"Processed: {result['successful_chambers']}/"
                f"{result['total_chambers_attempted']} chambers"
            )
            console.print(
                f"Total businesses extracted: {result['total_businesses_extracted']}"
            )
            console.print(
                f"Processing time: {result['total_processing_time_seconds']:.1f}s"
            )
            console.print(
                f"Database total leads: "
                f"{result['database_stats'].get('total_leads', 0)}"
            )
        else:
            console.print(
                f"Chamber processing failed: {result.get('error')}", style="bold red"
            )
            raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("Chamber processing interrupted by user", style="bold red")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"Chamber processing failed: {e}", style="bold red")
        logger.error(f"Chamber processing failed: {e}")
        raise typer.Exit(1) from e


@app.command("setup-llm")
def setup_llm() -> None:
    """Download and configure the Qwen2-7B Instruct GGUF model."""
    model_file = settings.llm.MODEL_PATH
    model_file.parent.mkdir(parents=True, exist_ok=True)

    if model_file.exists():
        console.print(f"Model already present: {model_file}", style="green")
        return

    console.print("Downloading Qwen2-7B Instruct model (~4 GB)...", style="bold blue")
    try:
        from huggingface_hub import hf_hub_download
    except ImportError as e:
        console.print(
            "huggingface-hub not installed. Install with "
            "`pip install 'lead-gen-pipeline[llm]'`.",
            style="bold red",
        )
        raise typer.Exit(1) from e

    try:
        with _spinner("Downloading model...") as progress:
            task = progress.add_task("Downloading model...", total=None)
            downloaded_path = hf_hub_download(
                repo_id="Qwen/Qwen2-7B-Instruct-GGUF",
                filename=model_file.name,
                local_dir=str(model_file.parent),
            )
            progress.update(task, description="Download completed")
        console.print(f"Model downloaded: {downloaded_path}", style="bold green")
    except Exception as e:
        console.print(f"Error downloading model: {e}", style="bold red")
        console.print(
            "Download it manually from "
            "https://huggingface.co/Qwen/Qwen2-7B-Instruct-GGUF and place it at "
            f"{model_file}."
        )
        raise typer.Exit(1) from e


@app.command()
def export(
    output_file: Path = typer.Option(
        "business_data.csv", "--output", "-o", help="Output CSV file"
    ),
    limit: int | None = typer.Option(
        None, "--limit", "-l", help="Maximum number of records to export"
    ),
) -> None:
    """Export stored leads to CSV."""

    async def export_data() -> None:
        await init_db()
        session_factory = get_async_session_local()
        async with session_factory() as session:
            query = select(Lead).order_by(Lead.created_at.desc())
            if limit:
                query = query.limit(limit)
            leads = (await session.execute(query)).scalars().all()

            if not leads:
                console.print("No data found in database", style="yellow")
                return

            fieldnames = [
                "id",
                "company_name",
                "website",
                "scraped_from_url",
                "canonical_url",
                "description",
                "phone_numbers",
                "emails",
                "addresses",
                "social_media_links",
                "industry_tags",
                "chamber_name",
                "chamber_url",
                "created_at",
            ]
            with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for lead in leads:
                    writer.writerow(
                        {
                            "id": lead.id,
                            "company_name": lead.company_name,
                            "website": lead.website,
                            "scraped_from_url": lead.scraped_from_url,
                            "canonical_url": lead.canonical_url,
                            "description": lead.description,
                            "phone_numbers": ", ".join(lead.phone_numbers or []),
                            "emails": ", ".join(lead.emails or []),
                            "addresses": "; ".join(lead.addresses or []),
                            "social_media_links": str(lead.social_media_links or {}),
                            "industry_tags": ", ".join(lead.industry_tags or []),
                            "chamber_name": lead.chamber_name,
                            "chamber_url": lead.chamber_url,
                            "created_at": lead.created_at,
                        }
                    )
            console.print(
                f"Exported {len(leads)} records to {output_file}", style="bold green"
            )

    try:
        asyncio.run(export_data())
    except Exception as e:
        console.print(f"Export failed: {e}", style="bold red")
        raise typer.Exit(1) from e


@app.command()
def stats() -> None:
    """Show database statistics."""

    async def show_stats() -> None:
        await init_db()
        session_factory = get_async_session_local()
        async with session_factory() as session:
            all_leads = (await session.execute(select(Lead))).scalars().all()

            if not all_leads:
                console.print("No data found in database", style="yellow")
                return

            total = len(all_leads)

            def pct(n: int) -> str:
                return f"{n} ({n / total * 100:.1f}%)"

            table = Table(title="Lead database statistics")
            table.add_column("Metric", style="cyan", no_wrap=True)
            table.add_column("Count", style="magenta")
            table.add_row("Total records", str(total))
            table.add_row(
                "From chamber directories",
                pct(sum(1 for x in all_leads if x.chamber_name)),
            )
            table.add_row("With emails", pct(sum(1 for x in all_leads if x.emails)))
            table.add_row(
                "With phone numbers", pct(sum(1 for x in all_leads if x.phone_numbers))
            )
            table.add_row(
                "With addresses", pct(sum(1 for x in all_leads if x.addresses))
            )
            table.add_row(
                "With social media",
                pct(sum(1 for x in all_leads if x.social_media_links)),
            )
            table.add_row(
                "With industry tags", pct(sum(1 for x in all_leads if x.industry_tags))
            )
            console.print(table)

    try:
        asyncio.run(show_stats())
    except Exception as e:
        console.print(f"Failed to get statistics: {e}", style="bold red")
        raise typer.Exit(1) from e


@app.command()
def init() -> None:
    """Initialize the database."""

    async def init_database() -> None:
        await init_db()
        console.print("Database initialized successfully", style="bold green")

    try:
        asyncio.run(init_database())
    except Exception as e:
        console.print(f"Database initialization failed: {e}", style="bold red")
        raise typer.Exit(1) from e


@app.command()
def config() -> None:
    """Show the active configuration."""
    table = Table(title="Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="magenta")
    table.add_row("Project name", settings.PROJECT_NAME)
    table.add_row("Input CSV", str(settings.INPUT_URLS_CSV))
    table.add_row("Database URL", settings.database.DATABASE_URL)
    table.add_row("Max concurrency", str(settings.MAX_PIPELINE_CONCURRENCY))
    table.add_row("Log level", settings.logging.LOG_LEVEL)
    table.add_row("Default timeout", f"{settings.crawler.DEFAULT_TIMEOUT_SECONDS}s")
    table.add_row("Respect robots.txt", str(settings.crawler.RESPECT_ROBOTS_TXT))
    table.add_row("Use Playwright", str(settings.crawler.USE_PLAYWRIGHT_BY_DEFAULT))
    table.add_row("LLM model path", str(settings.llm.MODEL_PATH))
    table.add_row("LLM context size", str(settings.llm.CONTEXT_SIZE))
    console.print(table)


@app.command("test")
def test_scraper(
    url: str = typer.Argument(..., help="URL to test data extraction on"),
    playwright: bool = typer.Option(
        False, "--playwright", "-p", help="Use Playwright instead of HTTPX"
    ),
) -> None:
    """Extract data from a single URL (no model required)."""
    from lead_gen_pipeline.crawler import AsyncWebCrawler
    from lead_gen_pipeline.scraper import HTMLScraper

    async def test_single_url() -> None:
        console.print(f"Testing data extraction on: {url}")
        crawler = AsyncWebCrawler()
        try:
            with _spinner("Fetching page...") as progress:
                task = progress.add_task("Fetching page...", total=None)
                html_content, status_code, final_url = await crawler.fetch_page(
                    url, use_playwright=playwright
                )
                if not html_content or not (200 <= status_code < 300):
                    console.print(
                        f"Failed to fetch page. Status: {status_code}", style="bold red"
                    )
                    return
                progress.update(task, description="Extracting data...")
                data = HTMLScraper(html_content, final_url).scrape()

            console.print(f"Extracted data from {final_url}", style="bold green")
            table = Table(title="Extracted data")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="magenta")
            for key, value in data.items():
                display = str(value) if value not in (None, [], {}) else "None"
                if len(display) > 100:
                    display = display[:100] + "..."
                table.add_row(key.replace("_", " ").title(), display)
            console.print(table)
        finally:
            await crawler.close()

    try:
        asyncio.run(test_single_url())
    except Exception as e:
        console.print(f"Test failed: {e}", style="bold red")
        raise typer.Exit(1) from e


def main() -> None:
    """Console-script entry point."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\nInterrupted.", style="bold yellow")
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()
