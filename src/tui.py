"""
Interactive TUI (Text User Interface) for exploring papers.

This module provides a rich, interactive terminal interface for browsing
and exploring analyzed papers using the Textual framework.

Usage:
    python main.py --explore
"""

import json
from datetime import datetime
from pathlib import Path
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

from src.database import delete_paper, get_db_session, mark_paper_as_read
from src.models.paper import Paper, ReadingProgress


class PaperDetailScreen(Screen):
    """
    Screen showing detailed view of a single paper.

    Displays:
    - Paper metadata
    - Analysis from Reader Agent
    - Explanation from Explainer Agent
    """

    BINDINGS: ClassVar = [
        Binding("escape", "pop_screen", "Back"),
        Binding("q", "pop_screen", "Back"),
        Binding("e", "export_json", "Export JSON"),
        Binding("d", "delete_paper", "Delete"),
        Binding("r", "toggle_read", "Mark Read"),
    ]

    def __init__(self, paper: Paper, reading_status: str | None = None):
        super().__init__()
        self.paper = paper
        self.reading_status = reading_status or "unread"

    def compose(self) -> ComposeResult:
        """Build the UI layout."""
        yield Header()

        with VerticalScroll():
            # Status indicator
            status_text = self._get_status_text()
            yield Static(status_text, id="status")

            # Paper metadata
            metadata = self._format_metadata()
            yield Static(metadata, id="metadata")

            # Abstract
            yield Static("[bold cyan]ABSTRACT[/bold cyan]", classes="section-header")
            yield Static(self.paper.abstract or "No abstract available", id="abstract")

            # Analysis (if available)
            if self.paper.analyzed_at:
                yield Static(
                    "\n[bold green]ANALYSIS (Claude Haiku)[/bold green]", classes="section-header"
                )
                analysis = self._format_analysis()
                yield Static(analysis, id="analysis")

            # Explanation (if available)
            if self.paper.explained_at:
                yield Static(
                    "\n[bold magenta]EXPLANATION (Claude Sonnet)[/bold magenta]",
                    classes="section-header",
                )
                explanation = self._format_explanation()
                yield Static(explanation, id="explanation")

        yield Footer()

    def _get_status_text(self) -> str:
        """Get status indicator text with color."""
        status_icons = {
            "unread": "○",
            "reading": "◐",
            "finished": "●",
            "archived": "▣",
        }

        icon = status_icons.get(self.reading_status, "○")

        # Processing status
        process_status = []
        if self.paper.analyzed_at:
            process_status.append("✓ Analyzed")
        if self.paper.explained_at:
            process_status.append("✓ Explained")

        process_str = " | ".join(process_status) if process_status else "Not processed"

        return f"[bold]{icon} {self.reading_status.upper()}[/bold] | {process_str}"

    def _format_metadata(self) -> str:
        """Format paper metadata."""
        # Format scores
        bt_score = (
            f"{self.paper.breakthrough_score:.0%}" if self.paper.breakthrough_score else "N/A"
        )
        rel_score = f"{self.paper.relevance_score:.0%}" if self.paper.relevance_score else "N/A"
        fav_indicator = "★ FAVORITE" if self.paper.is_favorite else ""

        lines = [
            f"[bold white]{self.paper.title}[/bold white]",
            f"\n[bold yellow]Breakthrough: {bt_score}[/bold yellow] | [bold cyan]Relevance: {rel_score}[/bold cyan] {fav_indicator}",
            f"\n[dim]ArXiv ID:[/dim] {self.paper.arxiv_id}",
            f"[dim]Authors:[/dim] {', '.join(self.paper.authors[:3])}{'...' if len(self.paper.authors) > 3 else ''}",
            f"[dim]Published:[/dim] {self.paper.published_date.date()}",
            f"[dim]Categories:[/dim] {', '.join(self.paper.categories)}",
            f"[dim]PDF:[/dim] {self.paper.pdf_url}",
        ]
        return "\n".join(lines)

    def _format_analysis(self) -> str:
        """Format analysis section."""
        lines = [
            f"\n[yellow]Main Claim:[/yellow]\n{self.paper.main_claim}",
            f"\n[yellow]Methodology:[/yellow]\n{self.paper.methodology}",
            "\n[yellow]Key Results:[/yellow]",
        ]

        if isinstance(self.paper.key_results, list):
            for result in self.paper.key_results:
                lines.append(f"  • {result}")
        else:
            lines.append(f"{self.paper.key_results}")

        lines.extend(
            [
                f"\n[yellow]Novel Contributions:[/yellow]\n{self.paper.novel_contributions}",
                f"\n[yellow]Limitations:[/yellow]\n{self.paper.limitations}",
                f"\n[yellow]Concepts:[/yellow] {', '.join(self.paper.concepts) if isinstance(self.paper.concepts, list) else self.paper.concepts}",
            ]
        )

        return "\n".join(lines)

    def _format_explanation(self) -> str:
        """Format explanation section."""
        lines = [
            f"\n[cyan]ELI5 Summary:[/cyan]\n{self.paper.eli5_summary}",
            f"\n[cyan]Key Insight:[/cyan]\n{self.paper.key_insight}",
            "\n[cyan]Learning Questions:[/cyan]",
        ]

        if isinstance(self.paper.learning_questions, list):
            for i, question in enumerate(self.paper.learning_questions, 1):
                lines.append(f"  {i}. {question}")
        else:
            lines.append(f"{self.paper.learning_questions}")

        lines.extend(
            [
                "\n[cyan]Prerequisites:[/cyan]",
                f"{self._format_list(self.paper.prerequisites)}",
                "\n[cyan]Related Concepts:[/cyan]",
                f"{self._format_list(self.paper.related_concepts)}",
            ]
        )

        return "\n".join(lines)

    def _format_list(self, items) -> str:
        """Format a list of items."""
        if isinstance(items, list):
            return "\n".join(f"  • {item}" for item in items)
        return str(items)

    def action_pop_screen(self) -> None:
        """Go back to the main list."""
        self.app.pop_screen()

    def action_export_json(self) -> None:
        """Export current paper to JSON file."""
        # Create exports directory if it doesn't exist
        exports_dir = Path("exports")
        exports_dir.mkdir(exist_ok=True)

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = exports_dir / f"{self.paper.arxiv_id}_{timestamp}.json"

        # Prepare data
        paper_data = {
            "arxiv_id": self.paper.arxiv_id,
            "title": self.paper.title,
            "abstract": self.paper.abstract,
            "authors": self.paper.authors,
            "published_date": self.paper.published_date.isoformat(),
            "categories": self.paper.categories,
            "pdf_url": self.paper.pdf_url,
            "abstract_url": self.paper.abstract_url,
            "discovered_at": self.paper.discovered_at.isoformat(),
            "analysis": (
                {
                    "main_claim": self.paper.main_claim,
                    "methodology": self.paper.methodology,
                    "key_results": self.paper.key_results,
                    "novel_contributions": self.paper.novel_contributions,
                    "limitations": self.paper.limitations,
                    "concepts": self.paper.concepts,
                    "analyzed_at": (
                        self.paper.analyzed_at.isoformat() if self.paper.analyzed_at else None
                    ),
                }
                if self.paper.analyzed_at
                else None
            ),
            "explanation": (
                {
                    "eli5_summary": self.paper.eli5_summary,
                    "key_insight": self.paper.key_insight,
                    "learning_questions": self.paper.learning_questions,
                    "prerequisites": self.paper.prerequisites,
                    "related_concepts": self.paper.related_concepts,
                    "explained_at": (
                        self.paper.explained_at.isoformat() if self.paper.explained_at else None
                    ),
                }
                if self.paper.explained_at
                else None
            ),
            "reading_status": self.reading_status,
        }

        # Write to file
        with open(filename, "w") as f:
            json.dump(paper_data, f, indent=2)

        self.notify(f"Exported to {filename}", severity="information")

    def action_delete_paper(self) -> None:
        """Delete the current paper with confirmation."""
        # Show confirmation (we'll use a simple approach for now)
        if delete_paper(self.paper.arxiv_id):
            self.notify(f"Deleted {self.paper.arxiv_id}", severity="warning")
            self.app.pop_screen()
        else:
            self.notify("Failed to delete paper", severity="error")

    def action_toggle_read(self) -> None:
        """Toggle reading status."""
        # Cycle through statuses: unread -> reading -> finished -> unread
        status_cycle = {"unread": "reading", "reading": "finished", "finished": "unread"}

        new_status = status_cycle.get(self.reading_status, "reading")

        if mark_paper_as_read(self.paper.arxiv_id, new_status):
            self.reading_status = new_status
            # Update status display
            status_widget = self.query_one("#status", Static)
            status_widget.update(self._get_status_text())
            self.notify(f"Marked as {new_status}", severity="information")
        else:
            self.notify("Failed to update reading status", severity="error")


class PaperExplorerApp(App):
    """
    Main TUI application for exploring papers.

    Features:
    - Browse all papers in a table
    - View detailed analysis and explanations
    - Export papers to JSON
    - Delete papers
    - Mark papers as read
    """

    CSS = """
    Screen {
        background: $surface;
    }

    DataTable {
        height: 100%;
    }

    #metadata {
        padding: 1;
        background: $panel;
        border: solid $primary;
    }

    #status {
        padding: 1;
        background: $panel;
        margin-bottom: 1;
    }

    .section-header {
        margin-top: 1;
        margin-bottom: 1;
    }

    #abstract, #analysis, #explanation {
        padding: 1;
        background: $panel;
        margin-bottom: 1;
    }
    """

    BINDINGS: ClassVar = [
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.papers = []
        self.reading_statuses = {}

    def compose(self) -> ComposeResult:
        """Build the main UI."""
        yield Header()
        yield DataTable(id="papers-table")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the table when app starts."""
        table = self.query_one(DataTable)

        # Add columns with score columns
        table.add_columns("⭐", "Breakthrough", "Relevance", "Title", "Status", "Concepts")
        table.cursor_type = "row"

        # Load papers from database
        self._load_papers()

    def _load_papers(self) -> None:
        """Load papers from database and populate table."""
        table = self.query_one(DataTable)

        with get_db_session() as db:
            # Get all papers ordered by breakthrough score (best to worst)
            papers = (
                db.query(Paper)
                .order_by(
                    Paper.breakthrough_score.desc().nulls_last(),
                    Paper.relevance_score.desc().nulls_last(),
                )
                .all()
            )

            # Get reading statuses
            reading_progress = db.query(ReadingProgress).all()
            self.reading_statuses = {rp.paper_id: rp.status for rp in reading_progress}

            for paper in papers:
                # Favorite indicator
                fav = "★" if paper.is_favorite else ""

                # Breakthrough score
                bt_score = f"{paper.breakthrough_score:.0%}" if paper.breakthrough_score else "-"

                # Relevance score
                rel_score = f"{paper.relevance_score:.0%}" if paper.relevance_score else "-"

                # Determine status
                status_parts = []

                # Reading status
                reading_status = self.reading_statuses.get(paper.arxiv_id, "unread")
                status_icons = {
                    "unread": "○",
                    "reading": "◐",
                    "finished": "●",
                    "archived": "▣",
                }
                status_parts.append(status_icons.get(reading_status, "○"))

                # Processing status
                if paper.analyzed_at and paper.explained_at:
                    status_parts.append("✓✓")
                elif paper.analyzed_at:
                    status_parts.append("✓")
                else:
                    status_parts.append("-")

                status = " ".join(status_parts)

                # Get key concepts (limit to 2 for display)
                if paper.concepts and isinstance(paper.concepts, list):
                    concepts = ", ".join(paper.concepts[:2])
                    if len(paper.concepts) > 2:
                        concepts += "..."
                elif paper.concepts:
                    concepts = str(paper.concepts)[:30]
                else:
                    concepts = "-"

                # Truncate title if too long
                title = paper.title
                if len(title) > 45:
                    title = title[:42] + "..."

                # Add row to table
                table.add_row(fav, bt_score, rel_score, title, status, concepts, key=paper.arxiv_id)

            self.papers = papers

    def on_data_table_row_selected(self, event) -> None:
        """Handle row selection when Enter is pressed on a row."""
        # This is the proper Textual event for DataTable row selection
        # Get the selected row's key (which is the arxiv_id)
        arxiv_id = str(event.row_key.value)

        # Find paper by arxiv_id
        paper = next((p for p in self.papers if p.arxiv_id == arxiv_id), None)

        if paper:
            reading_status = self.reading_statuses.get(paper.arxiv_id, "unread")
            self.push_screen(PaperDetailScreen(paper, reading_status))
        else:
            self.notify(f"Paper not found: {arxiv_id}", severity="error")


def run_paper_explorer():
    """Run the paper explorer TUI."""
    app = PaperExplorerApp()
    app.run()
