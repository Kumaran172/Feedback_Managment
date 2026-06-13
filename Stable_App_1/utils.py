"""
utils.py
--------
Shared constants, validators, and helper functions.
No business logic lives here — only reusable primitives.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Columns that MUST exist in the uploaded CSV
REQUIRED_COLUMNS: list[str] = ["id", "timestamp", "source", "rating", "feedback_text"]

# Feedback texts that are considered meaningless (lowercased for comparison)
MEANINGLESS_VALUES: frozenset[str] = frozenset(
    [
        ".",
        "..",
        "...",
        "....",
        ".....",
        "-",
        "--",
        "---",
        "ok",
        "okay",
        "good",
        "nice",
        "test",
        "testing",
        "na",
        "n/a",
        "n\\a",
        "none",
        "nothing",
        "null",
        "no",
        "yes",
        "fine",
        "great",
        "meh",
        "whatever",
        "idk",
        "hmm",
        "hm",
        "lol",
        "haha",
        "nope",
        "yep",
        "yup",
        "nah",
    ]
)

# Regex pattern: matches strings that contain NO real words —
# only punctuation, symbols, digits, whitespace, or emoji.
# Used as a secondary meaningless-detection pass after the set check.
_SYMBOL_ONLY_PATTERN = re.compile(
    r"^[\s\d\W\U0001F000-\U0001FFFF]*$", flags=re.UNICODE
)

# Allowed AI sentiment values
VALID_SENTIMENTS: frozenset[str] = frozenset(["Positive", "Negative", "Neutral"])

# Allowed AI categories — never add new ones
VALID_CATEGORIES: frozenset[str] = frozenset(
    ["Billing", "App Bug", "Delivery", "Staff/Support", "Other"]
)

# Fallback values when AI output is invalid or missing
DEFAULT_SENTIMENT: str = "Neutral"
DEFAULT_CATEGORY: str = "Other"
DEFAULT_SUMMARY: str = "No summary available"

# Colour palette for charts (consistent across all visuals)
SENTIMENT_COLOURS: dict[str, str] = {
    "Positive": "#2ecc71",
    "Negative": "#e74c3c",
    "Neutral": "#95a5a6",
}

CATEGORY_COLOURS: list[str] = [
    "#3498db",
    "#9b59b6",
    "#e67e22",
    "#1abc9c",
    "#e74c3c",
]

# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


def validate_columns(df: pd.DataFrame) -> tuple[bool, list[str]]:
    """
    Check that all required columns are present in the DataFrame.

    Returns
    -------
    (is_valid, missing_columns)
    """
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    return len(missing) == 0, missing


def validate_sentiment(value: str) -> str:
    """Return value if valid, otherwise DEFAULT_SENTIMENT."""
    if isinstance(value, str) and value.strip() in VALID_SENTIMENTS:
        return value.strip()
    return DEFAULT_SENTIMENT


def validate_category(value: str) -> str:
    """Return value if valid, otherwise DEFAULT_CATEGORY."""
    if isinstance(value, str) and value.strip() in VALID_CATEGORIES:
        return value.strip()
    return DEFAULT_CATEGORY


def validate_summary(value: str) -> str:
    """Return value if non-empty string, otherwise DEFAULT_SUMMARY."""
    if isinstance(value, str) and value.strip():
        return value.strip()
    return DEFAULT_SUMMARY


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


def format_number(n: int) -> str:
    """Format an integer with comma separators for display."""
    return f"{n:,}"


def format_percentage(count: int, total: int) -> str:
    """Return a formatted percentage string, safe against zero-division."""
    if total == 0:
        return "0.0%"
    return f"{(count / total) * 100:.1f}%"


def safe_parse_timestamp(ts: str) -> Optional[datetime]:
    """
    Try to parse a timestamp string using common formats.
    Returns None if all attempts fail (never raises).
    """
    if pd.isna(ts) or str(ts).strip() == "":
        return None
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
    ]
    ts_str = str(ts).strip()
    for fmt in formats:
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            continue
    return None


def is_meaningless(text: str) -> bool:
    """
    Return True if the feedback text carries no analytical value.

    Catches:
    - Exact matches against MEANINGLESS_VALUES (case-insensitive)
    - Strings made up entirely of punctuation, symbols, digits, or emoji
      e.g. '....', '?????', '😡😡😡', '👍', '!!!!'
    """
    if not isinstance(text, str):
        return False
    stripped = text.strip()
    if not stripped:
        return False  # Empty is handled separately
    # Set-based check (fast path)
    if stripped.lower() in MEANINGLESS_VALUES:
        return True
    # Regex check: no real word characters at all
    if _SYMBOL_ONLY_PATTERN.fullmatch(stripped):
        return True
    return False


def truncate_text(text: str, max_len: int = 120) -> str:
    """Truncate a string for display purposes."""
    if not isinstance(text, str):
        return ""
    return text if len(text) <= max_len else text[:max_len] + "…"
