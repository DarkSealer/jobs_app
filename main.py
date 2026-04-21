#!/usr/bin/env python3
"""
Job Search Agent - Main entry point.

This application searches for jobs across multiple job boards and matches them
against your profile, skills, experience, and projects.
"""

import click
import yaml
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from src.models.profile import UserProfile
from src.matcher import JobMatcher
from src.scraper.indeed_scraper import IndeedScraper
from src.scraper.remotive_scraper import RemotiveScraper
from src.utils.output import display_results, save_results


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Job Search Agent - Find jobs matching your skills and experience."""
    pass


@cli.command()
@click.option(
    "--config", "-c",
    default="config.yaml",
    help="Path to configuration file"
)
@click.option(
    "--location", "-l",
    multiple=True,
    help="Location to search (can be specified multiple times)"
)
@click.option(
    "--remote/--no-remote",
    default=None,
    help="Include remote jobs"
)
@click.option(
    "--remote-only",
    is_flag=True,
    help="Search for remote jobs only"
)
@click.option(
    "--query", "-q",
    multiple=True,
    help="Job title/keywords to search for (can be specified multiple times)"
)
@click.option(
    "--limit",
    default=50,
    help="Maximum number of jobs per search"
)
@click.option(
    "--min-score",
    default=60,
    help="Minimum match score threshold (0-100)"
)
@click.option(
    "--output-dir", "-o",
    default="./results",
    help="Directory to save results"
)
@click.option(
    "--format", "output_format",
    type=click.Choice(["json", "csv", "both"]),
    default="json",
    help="Output format for saved results"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose output"
)
def search(
    config: str,
    location: tuple,
    remote: Optional[bool],
    remote_only: bool,
    query: tuple,
    limit: int,
    min_score: float,
    output_dir: str,
    output_format: str,
    verbose: bool
):
    """
    Search for jobs matching your profile.
    
    This command searches multiple job boards for positions that match your
    skills, experience, and project background.
    """
    # Load configuration
    config_path = Path(config)
    if not config_path.exists():
        click.echo(f"❌ Configuration file not found: {config}")
        click.echo("   Please create a config.yaml file with your profile information.")
        return
    
    with open(config_path, 'r') as f:
        config_data = yaml.safe_load(f)
    
    # Create user profile from config
    profile = UserProfile.from_config(config_data)
    
    if verbose:
        click.echo(f"\n👤 Searching jobs for: {profile.name}")
        click.echo(f"💼 Experience: {profile.experience_years} years")
        click.echo(f"🛠️  Skills: {', '.join(profile.get_skills_list()[:5])}...")
        click.echo()
    
    # Determine search parameters
    search_locations = list(location) if location else config_data.get("search", {}).get("locations", [])
    search_queries = list(query) if query else profile.get_preferred_titles()
    include_remote = remote_only or (remote if remote is not None else config_data.get("search", {}).get("include_remote", True))
    
    if remote_only:
        search_locations = ["Remote"]
    
    if verbose:
        click.echo(f"📍 Locations: {', '.join(search_locations)}")
        click.echo(f"🔍 Queries: {', '.join(search_queries[:3])}...")
        click.echo(f"🏠 Remote: {'Yes' if include_remote else 'No'}")
        click.echo()
    
    # Initialize matcher
    matcher = JobMatcher(profile, config_data)
    
    # Initialize scrapers
    all_jobs = []
    
    # Search Indeed
    click.echo("🔎 Searching Indeed...")
    indeed_scraper = IndeedScraper()
    
    for loc in search_locations:
        for job_query in search_queries:
            try:
                jobs = indeed_scraper.search(
                    query=job_query,
                    location=loc if loc.lower() != "remote" else None,
                    remote=include_remote and loc.lower() == "remote",
                    limit=limit // len(search_locations) // len(search_queries)
                )
                all_jobs.extend(jobs)
                if verbose:
                    click.echo(f"   ✓ Found {len(jobs)} jobs for '{job_query}' in '{loc}'")
            except Exception as e:
                click.echo(f"   ⚠️  Error searching Indeed: {e}")
    
    indeed_scraper.close()

    # Fallback source when direct scraping is blocked or returns empty
    if not all_jobs:
        click.echo("🔁 Indeed returned no results. Trying Remotive API fallback...")
        remotive_scraper = RemotiveScraper()

        for job_query in search_queries:
            try:
                jobs = remotive_scraper.search(
                    query=job_query,
                    remote=True,
                    limit=max(5, limit // max(1, len(search_queries))),
                )
                all_jobs.extend(jobs)
                if verbose:
                    click.echo(f"   ✓ Found {len(jobs)} fallback jobs for '{job_query}'")
            except Exception as e:
                click.echo(f"   ⚠️  Error searching Remotive: {e}")

        remotive_scraper.close()

    # Remove duplicates caused by overlapping queries across sources
    unique_jobs = {}
    for job in all_jobs:
        key = job.url or f"{job.source.value}:{job.title}:{job.company}:{job.location}"
        unique_jobs[key] = job
    all_jobs = list(unique_jobs.values())
    
    if not all_jobs:
        click.echo("\n⚠️  No jobs found. This could be due to:")
        click.echo("   • Rate limiting from job boards")
        click.echo("   • Network issues")
        click.echo("   • Need for authentication/API keys")
        click.echo("\n💡 Try:")
        click.echo("   • Using demo mode with sample data")
        click.echo("   • Configuring API keys in config.yaml")
        click.echo("   • Reducing search frequency")
        return
    
    click.echo(f"\n📦 Total jobs collected: {len(all_jobs)}")
    
    # Match jobs against profile
    click.echo("\n🎯 Matching jobs against your profile...")
    match_results = matcher.match_batch(all_jobs)
    
    # Filter by minimum score
    good_matches = matcher.filter_by_threshold(match_results, min_score)
    
    click.echo(f"✅ Good matches (>{min_score}%): {len(good_matches)}")
    
    if not good_matches:
        click.echo("\n⚠️  No good matches found. Try lowering the --min-score threshold.")
        return
    
    # Display results
    click.echo("\n" + "=" * 60)
    click.echo("🏆 TOP JOB MATCHES")
    click.echo("=" * 60 + "\n")
    
    display_results(good_matches[:20], verbose=verbose)
    
    # Save results
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_results(
        good_matches, 
        output_path / f"job_matches_{timestamp}",
        output_format=output_format
    )
    
    click.echo(f"\n💾 Results saved to: {output_path}")
    click.echo("\n✨ Done! Review the matches and apply to your favorites!")


@cli.command()
@click.option(
    "--config", "-c",
    default="config.yaml",
    help="Path to configuration file"
)
def show_profile(config: str):
    """Display your current profile configuration."""
    config_path = Path(config)
    if not config_path.exists():
        click.echo(f"❌ Configuration file not found: {config}")
        return
    
    with open(config_path, 'r') as f:
        config_data = yaml.safe_load(f)
    
    profile = UserProfile.from_config(config_data)
    
    click.echo(f"\n👤 {profile.name}")
    click.echo(f"📧 {profile.email}")
    click.echo(f"💼 {profile.experience_years} years of experience")
    click.echo(f"\n📝 Description:\n{profile.description}")
    
    click.echo(f"\n🛠️  Skills ({len(profile.skills)}):")
    for skill in profile.skills:
        click.echo(f"   • {skill}")
    
    click.echo(f"\n📁 Projects ({len(profile.projects)}):")
    for project in profile.projects:
        click.echo(f"   • {project.name}: {', '.join(project.technologies)}")
    
    click.echo(f"\n🎯 Preferred Job Titles:")
    for title in profile.get_preferred_titles():
        click.echo(f"   • {title}")


@cli.command()
def init():
    """Initialize a new configuration file."""
    config_path = Path("config.yaml")
    
    if config_path.exists():
        click.confirm("⚠️  config.yaml already exists. Overwrite?", abort=True)
    
    # Copy the example config
    example_config = Path(__file__).parent / "config.yaml"
    if example_config.exists():
        import shutil
        shutil.copy(example_config, config_path)
        click.echo("✅ Created config.yaml with example configuration.")
        click.echo("📝 Edit the file to add your profile information.")
    else:
        click.echo("❌ Could not find example configuration.")


if __name__ == "__main__":
    cli()
