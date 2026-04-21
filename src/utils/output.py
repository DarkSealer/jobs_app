"""Output utilities for displaying and saving results."""

import json
import csv
from typing import List, Optional
from pathlib import Path

from ..models.match_result import MatchResult


def display_results(results: List[MatchResult], verbose: bool = False, limit: int = 20):
    """
    Display match results in the terminal.
    
    Args:
        results: List of match results to display
        verbose: Show detailed information
        limit: Maximum number of results to show
    """
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    
    console = Console()
    
    # Create summary table
    table = Table(title="🎯 Top Job Matches", show_header=True, header_style="bold magenta")
    table.add_column("Rank", style="dim", width=4)
    table.add_column("Position", style="cyan")
    table.add_column("Company", style="green")
    table.add_column("Location", style="yellow")
    table.add_column("Score", justify="right", style="bold")
    table.add_column("Grade", justify="center")
    table.add_column("Remote", justify="center")
    
    for i, result in enumerate(results[:limit], 1):
        remote_icon = "🏠" if result.job.remote else "📍"
        table.add_row(
            str(i),
            result.job.title[:40] + "..." if len(result.job.title) > 40 else result.job.title,
            result.job.company[:25] + "..." if len(result.job.company) > 25 else result.job.company,
            result.job.location[:20] + "..." if len(result.job.location) > 20 else result.job.location,
            f"{result.score.overall_score:.1f}%",
            result.score.get_grade(),
            remote_icon if result.job.remote else "",
        )
    
    console.print(table)
    
    if verbose:
        console.print("\n")
        
        # Show detailed view of top matches
        for i, result in enumerate(results[:5], 1):
            panel_text = Text()
            panel_text.append(f"🏢 {result.job.title}\n", style="bold cyan")
            panel_text.append(f"📋 Company: {result.job.company}\n", style="green")
            panel_text.append(f"📍 Location: {result.job.location}\n")
            panel_text.append(f"🔗 URL: {result.job.url}\n\n")
            
            panel_text.append(f"📊 Match Score: {result.score.overall_score:.1f}% ({result.score.get_grade()})\n\n", style="bold")
            
            if result.score.matched_skills:
                panel_text.append("✅ Matched Skills:\n", style="bold green")
                for skill in result.score.matched_skills[:8]:
                    panel_text.append(f"   • {skill}\n")
                panel_text.append("\n")
            
            if result.score.missing_skills:
                panel_text.append("❌ Missing Skills:\n", style="bold red")
                for skill in result.score.missing_skills[:5]:
                    panel_text.append(f"   • {skill}\n")
                panel_text.append("\n")
            
            panel_text.append(f"💡 {result.recommendation}\n", style="italic yellow")
            
            console.print(Panel(panel_text, title=f"#{i} Match Details", border_style="blue"))
            console.print()


def save_results(
    results: List[MatchResult], 
    filepath: Path, 
    output_format: str = "json"
):
    """
    Save match results to file.
    
    Args:
        results: List of match results to save
        filepath: Path to save results (without extension)
        output_format: Output format ("json", "csv", or "both")
    """
    if output_format in ["json", "both"]:
        _save_json(results, filepath.with_suffix(".json"))
    
    if output_format in ["csv", "both"]:
        _save_csv(results, filepath.with_suffix(".csv"))


def _save_json(results: List[MatchResult], filepath: Path):
    """Save results as JSON."""
    data = {
        "total_matches": len(results),
        "generated_at": results[0].matched_at.isoformat() if results else None,
        "jobs": [result.get_summary() for result in results]
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"   📄 Saved JSON: {filepath}")


def _save_csv(results: List[MatchResult], filepath: Path):
    """Save results as CSV."""
    if not results:
        return
    
    fieldnames = [
        "rank", "job_title", "company", "location", "remote",
        "overall_score", "grade", "skills_match", "experience_match",
        "matched_skills", "missing_skills", "recommendation", "url"
    ]
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for i, result in enumerate(results, 1):
            writer.writerow({
                "rank": i,
                "job_title": result.job.title,
                "company": result.job.company,
                "location": result.job.location,
                "remote": result.job.remote,
                "overall_score": f"{result.score.overall_score:.1f}",
                "grade": result.score.get_grade(),
                "skills_match": f"{result.score.skills_match:.1f}",
                "experience_match": f"{result.score.experience_match:.1f}",
                "matched_skills": "; ".join(result.score.matched_skills),
                "missing_skills": "; ".join(result.score.missing_skills),
                "recommendation": result.recommendation,
                "url": result.job.url,
            })
    
    print(f"   📊 Saved CSV: {filepath}")
