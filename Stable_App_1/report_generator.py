"""
report_generator.py
-------------------
Derives all metrics, insights, and downloadable reports from the enriched DataFrame.

Key design rule
---------------
EVERY count, percentage, and chart value is computed via
    len(enriched_df)  or  enriched_df.groupby(...)
at the moment of generation — NEVER from stored integers that could drift.
This makes it impossible for dashboard numbers to diverge from the data.
"""

from __future__ import annotations

import io
import textwrap
from dataclasses import dataclass, field
from typing import Optional

import google.generativeai as genai
import pandas as pd

from utils import (
    VALID_SENTIMENTS,
    format_percentage,
    truncate_text,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GEMINI_MODEL: str = "gemini-1.5-flash"

# How many representative examples to pull per category
EXAMPLES_PER_CATEGORY: int = 3

# Maximum feedback length shown in examples
EXAMPLE_MAX_CHARS: int = 200

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class SentimentBreakdown:
    sentiment: str
    count: int
    percentage: str


@dataclass
class CategoryBreakdown:
    category: str
    count: int
    percentage: str
    examples: list[str] = field(default_factory=list)


@dataclass
class InsightsReport:
    total_records: int
    sentiment_breakdown: list[SentimentBreakdown]
    top_categories: list[CategoryBreakdown]
    executive_summary: str
    root_cause_analysis: str
    recommendations: str
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# ReportGenerator
# ---------------------------------------------------------------------------


class ReportGenerator:
    """
    Generates management insights from an enriched DataFrame.

    The enriched DataFrame is the SOLE source of truth.
    No counts are stored; all are derived fresh on every call.
    """

    def __init__(self, api_key: str) -> None:
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(GEMINI_MODEL)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, enriched_df: pd.DataFrame) -> InsightsReport:
        """
        Build the full InsightsReport from an enriched DataFrame.

        Parameters
        ----------
        enriched_df : pd.DataFrame
            Must contain columns: feedback_text, sentiment, category, summary.

        Returns
        -------
        InsightsReport
        """
        total = len(enriched_df)

        sentiment_breakdown = self._compute_sentiment_breakdown(enriched_df, total)
        top_categories = self._compute_category_breakdown(enriched_df, total)

        # Generate AI narrative sections
        exec_summary = self._generate_executive_summary(enriched_df)
        root_cause = self._generate_root_cause(enriched_df)
        recommendations = self._generate_recommendations(enriched_df)

        return InsightsReport(
            total_records=total,
            sentiment_breakdown=sentiment_breakdown,
            top_categories=top_categories,
            executive_summary=exec_summary,
            root_cause_analysis=root_cause,
            recommendations=recommendations,
        )

    # ------------------------------------------------------------------
    # CSV export helpers
    # ------------------------------------------------------------------

    @staticmethod
    def to_cleaned_csv(cleaned_df: pd.DataFrame) -> bytes:
        """Return cleaned_df as UTF-8 encoded CSV bytes."""
        return cleaned_df.to_csv(index=False).encode("utf-8")

    @staticmethod
    def to_enriched_csv(enriched_df: pd.DataFrame) -> bytes:
        """Return enriched_df as UTF-8 encoded CSV bytes."""
        return enriched_df.to_csv(index=False).encode("utf-8")

    @staticmethod
    def to_summary_csv(report: InsightsReport) -> bytes:
        """
        Build a human-readable summary CSV from the InsightsReport.
        Suitable for attaching to management emails.
        """
        rows = []

        # Executive summary section
        rows.append(["EXECUTIVE SUMMARY", "", ""])
        rows.append([report.executive_summary, "", ""])
        rows.append(["", "", ""])

        # Sentiment section
        rows.append(["SENTIMENT BREAKDOWN", "", ""])
        rows.append(["Sentiment", "Count", "Percentage"])
        for s in report.sentiment_breakdown:
            rows.append([s.sentiment, s.count, s.percentage])

        rows.append(["", "", ""])

        # Category section
        rows.append(["TOP COMPLAINT CATEGORIES", "", ""])
        rows.append(["Category", "Count", "Percentage"])
        for c in report.top_categories:
            rows.append([c.category, c.count, c.percentage])

        rows.append(["", "", ""])

        # Root cause
        rows.append(["ROOT CAUSE ANALYSIS", "", ""])
        rows.append([report.root_cause_analysis, "", ""])

        rows.append(["", "", ""])

        # Recommendations
        rows.append(["RECOMMENDATIONS", "", ""])
        rows.append([report.recommendations, "", ""])

        buf = io.StringIO()
        for row in rows:
            # Simple CSV serialisation (no pandas dependency for this small output)
            buf.write(",".join(f'"{str(cell)}"' for cell in row) + "\n")

        return buf.getvalue().encode("utf-8")

    # ------------------------------------------------------------------
    # Private: metric computation
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_sentiment_breakdown(
        df: pd.DataFrame, total: int
    ) -> list[SentimentBreakdown]:
        """Compute counts and percentages for each sentiment label."""
        breakdown = []
        counts = df["sentiment"].value_counts()

        for sentiment in sorted(VALID_SENTIMENTS):
            count = int(counts.get(sentiment, 0))
            breakdown.append(
                SentimentBreakdown(
                    sentiment=sentiment,
                    count=count,
                    percentage=format_percentage(count, total),
                )
            )

        return breakdown

    @staticmethod
    def _compute_category_breakdown(
        df: pd.DataFrame, total: int
    ) -> list[CategoryBreakdown]:
        """
        Compute top-5 categories with counts, percentages, and examples.
        Examples are pulled directly from the DataFrame — no hardcoding.
        """
        counts = df["category"].value_counts().head(5)
        breakdown = []

        for category, count in counts.items():
            subset = df[df["category"] == category]["feedback_text"]
            examples = [
                truncate_text(t, EXAMPLE_MAX_CHARS)
                for t in subset.dropna().head(EXAMPLES_PER_CATEGORY).tolist()
            ]
            breakdown.append(
                CategoryBreakdown(
                    category=str(category),
                    count=int(count),
                    percentage=format_percentage(count, total),
                    examples=examples,
                )
            )

        return breakdown

    # ------------------------------------------------------------------
    # Private: AI narrative generation
    # ------------------------------------------------------------------

    def _generate_executive_summary(self, df: pd.DataFrame) -> str:
        """
        Ask Gemini to generate a short management/executive summary of the feedback.
        """
        total = len(df)
        negative_count = int((df["sentiment"] == "Negative").sum())
        negative_pct = format_percentage(negative_count, total)

        category_counts = df["category"].value_counts().head(3).to_dict()
        top_cat = df["category"].mode().iloc[0] if not df["category"].empty else "None"

        # Get some sample negative feedback to ground it
        negative_samples = (
            df[df["sentiment"] == "Negative"]["feedback_text"]
            .dropna()
            .head(10)
            .tolist()
        )
        sample_text = "\n".join(f"- {t[:120]}" for t in negative_samples)

        prompt = textwrap.dedent(
            f"""
            You are a senior operations analyst. Write a concise executive summary (around 2-3 sentences) for management based on the following customer feedback metrics:

            - Total feedback: {total}
            - Negative feedback: {negative_count} ({negative_pct})
            - Top categories: {category_counts}
            - Primary category of concern: {top_cat}

            Sample negative customer comments:
            {sample_text}

            Write a professional summary.
            Example style: "Most customer complaints are related to Delivery issues. Negative sentiment represents 62% of feedback. The primary concerns involve delayed deliveries and poor support responsiveness."

            Do not include formatting, markdown headers, or bullet points. Just return 2-3 sentences of clean text.
            """
        ).strip()

        return self._call_gemini_safe(prompt, fallback="Executive summary unavailable.")

    def _generate_root_cause(self, df: pd.DataFrame) -> str:
        """
        Ask Gemini to identify major complaint themes and their potential causes.
        Returns a formatted string; falls back gracefully on errors.
        """
        # Build a compact summary of the top issues to feed into the prompt
        category_counts = df["category"].value_counts().head(5).to_dict()
        negative_samples = (
            df[df["sentiment"] == "Negative"]["feedback_text"]
            .dropna()
            .head(15)
            .tolist()
        )
        sample_text = "\n".join(f"- {t[:150]}" for t in negative_samples)

        prompt = textwrap.dedent(
            f"""
            You are a senior operations analyst reviewing customer feedback.

            Category distribution (top 5):
            {category_counts}

            Sample negative feedback:
            {sample_text}

            Provide a Root Cause Analysis with:
            1. The 3-4 major complaint themes
            2. The most likely underlying cause for each theme

            Be concise. Use bullet points. Maximum 250 words.
            """
        ).strip()

        return self._call_gemini_safe(prompt, fallback="Root cause analysis unavailable.")

    def _generate_recommendations(self, df: pd.DataFrame) -> str:
        """
        Ask Gemini for actionable recommendations based on the complaint data.
        Returns a formatted string; falls back gracefully on errors.
        """
        category_counts = df["category"].value_counts().head(5).to_dict()
        negative_count = int((df["sentiment"] == "Negative").sum())
        total = len(df)

        prompt = textwrap.dedent(
            f"""
            You are a senior operations analyst.

            Dataset summary:
            - Total feedback: {total}
            - Negative feedback: {negative_count} ({format_percentage(negative_count, total)})
            - Top categories: {category_counts}

            Provide 4-5 actionable recommendations to reduce customer complaints.
            For each recommendation:
            - State the issue it addresses
            - Give a specific, implementable action
            - Mention the expected outcome

            Be concise. Use numbered points. Maximum 300 words.
            """
        ).strip()

        return self._call_gemini_safe(prompt, fallback="Recommendations unavailable.")

    def _call_gemini_safe(self, prompt: str, fallback: str) -> str:
        """
        Call Gemini and return the text response.
        Returns fallback string on any exception — never crashes the app.
        """
        try:
            response = self._model.generate_content(prompt)
            return response.text.strip()
        except Exception as exc:  # noqa: BLE001
            return f"{fallback}\n\n(Error: {exc})"
