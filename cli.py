#!/usr/bin/env python3
# cli.py - Command-line interface for B2B Intelligence Platform

import asyncio
import sys
from pathlib import Path
from typing import Optional, List
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
import csv

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from lead_gen_pipeline.config import settings
    from lead_gen_pipeline.utils import logger
    from lead_gen_pipeline.run_pipeline_mvp import main_pipeline
    from lead_gen_pipeline.chamber_pipeline import run_chamber_pipeline, ChamberPipeline
    from lead_gen_pipeline.database import init_db, get_async_session_local
    from lead_gen_pipeline.models import Lead
    from sqlalchemy import select
except ImportError as e:
    typer.echo(f"Error importing modules: {e}", err=True)
    typer.echo("Make sure you're running from the project root directory", err=True)
    raise typer.Exit(1)

app = typer.Typer(
    name="b2b-intelligence",
    help="B2B Intelligence Platform - Extract business data from web sources",
    add_completion=False
)
console = Console()

@app.command()
def run(
    input_file: Optional[Path] = typer.Option(
        None,
        "--input", "-i",
        help="CSV file with URLs to process (default: data/urls_seed.csv)"
    ),
    max_concurrency: Optional[int] = typer.Option(
        None,
        "--concurrency", "-c",
        help="Maximum concurrent requests"
    ),
    region: Optional[str] = typer.Option(
        "US",
        "--region", "-r",
        help="Default region for phone number parsing"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Enable verbose logging"
    )
):
    """Process individual business websites for data extraction."""
    
    if input_file:
        settings.INPUT_URLS_CSV = input_file
    if max_concurrency:
        settings.MAX_PIPELINE_CONCURRENCY = max_concurrency
        
    if verbose:
        settings.logging.LOG_LEVEL = "DEBUG"
        
    console.print("🚀 Starting Business Data Extraction Pipeline", style="bold green")
    console.print(f"Input file: {settings.INPUT_URLS_CSV}")
    console.print(f"Max concurrency: {settings.MAX_PIPELINE_CONCURRENCY}")
    console.print(f"Database: {settings.database.DATABASE_URL}")
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Processing websites...", total=None)
            
            asyncio.run(main_pipeline())
            
            progress.update(task, description="Pipeline completed!")
            
        console.print("✅ Pipeline completed successfully!", style="bold green")
        
    except KeyboardInterrupt:
        console.print("❌ Pipeline interrupted by user", style="bold red")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"❌ Pipeline failed: {e}", style="bold red")
        logger.error(f"Pipeline execution failed: {e}")
        raise typer.Exit(1)

@app.command("chambers")
def run_chambers(
    input_file: Optional[Path] = typer.Option(
        None,
        "--input", "-i",
        help="CSV file with chamber URLs (default: data/chamber_urls.csv)"
    ),
    urls: Optional[List[str]] = typer.Option(
        None,
        "--url", "-u",
        help="Individual chamber URLs to process"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Enable verbose logging"
    )
):
    """Process Chamber of Commerce directories for business intelligence."""
    
    if verbose:
        settings.logging.LOG_LEVEL = "DEBUG"
    
    console.print("Starting Chamber Directory Processing", style="bold green")
    
    chamber_urls = []
    
    if urls:
        chamber_urls = list(urls)
        console.print(f"Processing {len(chamber_urls)} chamber URLs from command line")
    elif input_file and input_file.exists():
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    url = row.get('url', '').strip()
                    if url and url.startswith(('http://', 'https://')):
                        chamber_urls.append(url)
            console.print(f"Loaded {len(chamber_urls)} chamber URLs from {input_file}")
        except Exception as e:
            console.print(f"❌ Error loading chamber URLs: {e}", style="bold red")
            raise typer.Exit(1)
    else:
        console.print("No chamber URLs provided. Use --input file or --url options")
        raise typer.Exit(1)
    
    if not chamber_urls:
        console.print("❌ No valid chamber URLs found", style="bold red")
        raise typer.Exit(1)
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Processing chambers...", total=None)
            
            result = asyncio.run(run_chamber_pipeline(chamber_urls))
            
            progress.update(task, description="Chamber processing completed!")
        
        if result['success']:
            console.print("✓ Chamber processing completed successfully!", style="bold green")
            console.print(f"Processed: {result['successful_chambers']}/{result['total_chambers_attempted']} chambers")
            console.print(f"Total businesses extracted: {result['total_businesses_extracted']}")
            console.print(f"Processing time: {result['total_processing_time_seconds']:.1f} seconds")
            console.print(f"Database total leads: {result['database_stats'].get('total_leads', 0)}")
        else:
            console.print("X Chamber processing failed", style="bold red")
            raise typer.Exit(1)
        
    except KeyboardInterrupt:
        console.print("X Chamber processing interrupted by user", style="bold red")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"X Chamber processing failed: {e}", style="bold red")
        logger.error(f"Chamber processing failed: {e}")
        raise typer.Exit(1)

@app.command("setup-llm")
def setup_llm():
    """Download and configure the required LLM model (Qwen2 Instruct 7B)."""
    console.print("Setting up LLM model for chamber directory processing", style="bold blue")
    
    model_dir = Path("./models")
    model_dir.mkdir(exist_ok=True)
    
    model_file = model_dir / "qwen2-7b-instruct-q4_k_m.gguf"
    
    if model_file.exists():
        console.print(f"✓ Model already exists: {model_file}")
        return
    
    console.print("Downloading Qwen2 Instruct 7B model...")
    console.print("This may take several minutes depending on your internet connection.")
    
    try:
        from huggingface_hub import hf_hub_download
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Downloading model...", total=None)
            
            downloaded_path = hf_hub_download(
                repo_id="Qwen/Qwen2-7B-Instruct-GGUF",
                filename="qwen2-7b-instruct-q4_k_m.gguf",
                local_dir=str(model_dir),
                local_dir_use_symlinks=False
            )
            
            progress.update(task, description="Download completed!")
        
        console.print(f"✓ Model downloaded successfully: {downloaded_path}", style="bold green")
        console.print("Chamber directory processing is now available!")
        
    except ImportError:
        console.print("X huggingface-hub not installed. Install with: pip install huggingface-hub", style="bold red")
        console.print("Then manually download the model from:")
        console.print("https://huggingface.co/Qwen/Qwen2-7B-Instruct-GGUF/blob/main/qwen2-7b-instruct-q4_k_m.gguf")
        console.print(f"Save it to: {model_file}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"X Error downloading model: {e}", style="bold red")
        console.print("Manual download instructions:")
        console.print("1. Go to: https://huggingface.co/Qwen/Qwen2-7B-Instruct-GGUF")
        console.print("2. Download: qwen2-7b-instruct-q4_k_m.gguf")
        console.print(f"3. Save to: {model_file}")
        raise typer.Exit(1)

@app.command()
def export(
    output_file: Path = typer.Option(
        "business_data.csv",
        "--output", "-o",
        help="Output CSV file for exported data"
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit", "-l",
        help="Maximum number of records to export"
    )
):
    """Export business data from database to CSV."""
    
    async def export_data():
        try:
            await init_db()
            
            session_factory = get_async_session_local()
            async with session_factory() as session:
                query = select(Lead).order_by(Lead.created_at.desc())
                if limit:
                    query = query.limit(limit)
                    
                result = await session.execute(query)
                leads = result.scalars().all()
                
                if not leads:
                    console.print("No data found in database", style="yellow")
                    return
                    
                with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = [
                        'id', 'company_name', 'website', 'scraped_from_url',
                        'canonical_url', 'description', 'phone_numbers', 'emails',
                        'addresses', 'social_media_links', 'industry_tags', 
                        'chamber_name', 'chamber_url', 'created_at'
                    ]
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for lead in leads:
                        writer.writerow({
                            'id': lead.id,
                            'company_name': lead.company_name,
                            'website': lead.website,
                            'scraped_from_url': lead.scraped_from_url,
                            'canonical_url': lead.canonical_url,
                            'description': lead.description,
                            'phone_numbers': ', '.join(lead.phone_numbers or []),
                            'emails': ', '.join(lead.emails or []),
                            'addresses': '; '.join(lead.addresses or []),
                            'social_media_links': str(lead.social_media_links or {}),
                            'industry_tags': ', '.join(lead.industry_tags or []),
                            'chamber_name': lead.chamber_name,
                            'chamber_url': lead.chamber_url,
                            'created_at': lead.created_at
                        })
                        
                console.print(f"✓ Exported {len(leads)} records to {output_file}", style="bold green")
                
        except Exception as e:
            console.print(f"X Export failed: {e}", style="bold red")
            raise typer.Exit(1)
    
    asyncio.run(export_data())

@app.command()
def stats():
    """Show database statistics and performance metrics."""
    
    async def show_stats():
        try:
            await init_db()
            
            session_factory = get_async_session_local()
            async with session_factory() as session:
                result = await session.execute(select(Lead))
                all_leads = result.scalars().all()
                
                if not all_leads:
                    console.print("No data found in database", style="yellow")
                    return
                    
                table = Table(title="Business Intelligence Database Statistics")
                table.add_column("Metric", style="cyan", no_wrap=True)
                table.add_column("Count", style="magenta")
                
                total_leads = len(all_leads)
                leads_with_emails = sum(1 for lead in all_leads if lead.emails)
                leads_with_phones = sum(1 for lead in all_leads if lead.phone_numbers)
                leads_with_addresses = sum(1 for lead in all_leads if lead.addresses)
                leads_with_social = sum(1 for lead in all_leads if lead.social_media_links)
                leads_with_industry = sum(1 for lead in all_leads if lead.industry_tags)
                chamber_leads = sum(1 for lead in all_leads if lead.chamber_name)
                
                table.add_row("Total Business Records", str(total_leads))
                table.add_row("Chamber Directory Records", f"{chamber_leads} ({chamber_leads/total_leads*100:.1f}%)")
                table.add_row("Records with Emails", f"{leads_with_emails} ({leads_with_emails/total_leads*100:.1f}%)")
                table.add_row("Records with Phone Numbers", f"{leads_with_phones} ({leads_with_phones/total_leads*100:.1f}%)")
                table.add_row("Records with Addresses", f"{leads_with_addresses} ({leads_with_addresses/total_leads*100:.1f}%)")
                table.add_row("Records with Social Media", f"{leads_with_social} ({leads_with_social/total_leads*100:.1f}%)")
                table.add_row("Records with Industry Tags", f"{leads_with_industry} ({leads_with_industry/total_leads*100:.1f}%)")
                
                console.print(table)
                
                # Show recent records
                recent_leads = sorted(all_leads, key=lambda x: x.created_at or '', reverse=True)[:5]
                
                if recent_leads:
                    console.print("\n📊 Recent Records:", style="bold")
                    recent_table = Table()
                    recent_table.add_column("Company", style="green")
                    recent_table.add_column("Website", style="blue")
                    recent_table.add_column("Source", style="cyan")
                    recent_table.add_column("Industry", style="yellow")
                    recent_table.add_column("Created", style="yellow")
                    
                    for lead in recent_leads:
                        source = "Chamber" if lead.chamber_name else "Website"
                        industry = ', '.join(lead.industry_tags or []) if lead.industry_tags else "N/A"
                        recent_table.add_row(
                            lead.company_name or "N/A",
                            lead.website or "N/A",
                            source,
                            industry[:20] + "..." if len(industry) > 20 else industry,
                            str(lead.created_at)[:19] if lead.created_at else "N/A"
                        )
                    
                    console.print(recent_table)
                
        except Exception as e:
            console.print(f"❌ Failed to get statistics: {e}", style="bold red")
            raise typer.Exit(1)
    
    asyncio.run(show_stats())

@app.command()
def init():
    """Initialize the database."""
    
    async def init_database():
        try:
            await init_db()
            console.print("✓ Database initialized successfully!", style="bold green")
        except Exception as e:
            console.print(f"X Database initialization failed: {e}", style="bold red")
            raise typer.Exit(1)
    
    asyncio.run(init_database())

@app.command()
def config():
    """Show current configuration."""
    
    console.print("Current Configuration:", style="bold")
    
    config_table = Table()
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="magenta")
    
    config_table.add_row("Project Name", settings.PROJECT_NAME)
    config_table.add_row("Input CSV", str(settings.INPUT_URLS_CSV))
    config_table.add_row("Database URL", settings.database.DATABASE_URL)
    config_table.add_row("Max Concurrency", str(settings.MAX_PIPELINE_CONCURRENCY))
    config_table.add_row("Log Level", settings.logging.LOG_LEVEL)
    config_table.add_row("Default Timeout", f"{settings.crawler.DEFAULT_TIMEOUT_SECONDS}s")
    config_table.add_row("Respect robots.txt", str(settings.crawler.RESPECT_ROBOTS_TXT))
    config_table.add_row("Use Playwright", str(settings.crawler.USE_PLAYWRIGHT_BY_DEFAULT))
    
    console.print(config_table)

@app.command("test")
def test_scraper(
    url: str = typer.Argument(..., help="URL to test data extraction on"),
    playwright: bool = typer.Option(False, "--playwright", "-p", help="Use Playwright instead of HTTPX")
):
    """Test data extraction on a single URL."""
    
    async def test_single_url():
        try:
            from lead_gen_pipeline.crawler import AsyncWebCrawler
            from lead_gen_pipeline.scraper import HTMLScraper
            
            console.print(f"Testing data extraction on: {url}")
            
            crawler = AsyncWebCrawler()
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Fetching page...", total=None)
                
                html_content, status_code, final_url = await crawler.fetch_page(url, use_playwright=playwright)
                
                if not html_content or status_code < 200 or status_code >= 300:
                    console.print(f"X Failed to fetch page. Status: {status_code}", style="bold red")
                    return
                    
                progress.update(task, description="Extracting data...")
                
                scraper = HTMLScraper(html_content, final_url)
                data = scraper.scrape()
                
                progress.update(task, description="Completed!")
            
            console.print(f"✓ Successfully extracted data from {final_url}", style="bold green")
            
            results_table = Table(title="Extracted Data")
            results_table.add_column("Field", style="cyan")
            results_table.add_column("Value", style="magenta")
            
            for key, value in data.items():
                if isinstance(value, (list, dict)):
                    display_value = str(value) if value else "None"
                else:
                    display_value = str(value) if value is not None else "None"
                    
                if len(display_value) > 100:
                    display_value = display_value[:100] + "..."
                    
                results_table.add_row(key.replace('_', ' ').title(), display_value)
            
            console.print(results_table)
            
            await crawler.close()
            
        except Exception as e:
            console.print(f"X Test failed: {e}", style="bold red")
            raise typer.Exit(1)
    
    asyncio.run(test_single_url())

def main():
    """Main entry point."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\nGoodbye!", style="bold yellow")
        sys.exit(0)
    except Exception as e:
        console.print(f"X Application error: {e}", style="bold red")
        sys.exit(1)

if __name__ == "__main__":
    main()
