"""
data_cleaner.py
---------------
All data-cleaning logic lives here.  app.py never transforms data directly.

Design guarantees
-----------------
* Cleaning runs as a deterministic, sequential pipeline.
* Each step operates on the output of the previous step.
* A CleaningLog records exactly what was removed at each stage.
* An invariant assertion verifies that
      original - removals == len(cleaned_df)
  before the result is returned.  If the assertion fails, an explicit
  RuntimeError is raised instead of silently returning wrong counts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from utils import (
    is_meaningless,
    safe_parse_timestamp,
    validate_columns,
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class CleaningLog:
    """
    Immutable audit record produced by DataCleaner.clean().
    Every number displayed in the dashboard MUST come from here or from
    len(cleaned_df) — never from a separate count computed elsewhere.
    """

    original_count: int = 0
    removed_exact_duplicates: int = 0
    removed_empty: int = 0
    removed_meaningless: int = 0
    final_count: int = 0

    # Data Quality Warning Metrics
    missing_timestamps: int = 0
    invalid_timestamps: int = 0
    missing_ratings: int = 0
    missing_feedback_text: int = 0

    # Human-readable list of operations performed (for the audit trail UI)
    operations: list[str] = field(default_factory=list)

    @property
    def total_removed(self) -> int:
        return (
            self.removed_exact_duplicates
            + self.removed_empty
            + self.removed_meaningless
        )

    @property
    def retention_rate(self) -> float:
        """Percentage of original rows kept."""
        if self.original_count == 0:
            return 0.0
        return (self.final_count / self.original_count) * 100


@dataclass
class CleaningResult:
    """
    Everything the UI needs after cleaning.
    original_df  — raw upload, never mutated.
    cleaned_df   — single source of truth for all downstream steps.
    log          — audit trail; used for display only, not for recomputing counts.
    error        — non-None when cleaning failed before producing output.
    """

    original_df: Optional[pd.DataFrame] = None
    cleaned_df: Optional[pd.DataFrame] = None
    log: CleaningLog = field(default_factory=CleaningLog)
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None and self.cleaned_df is not None


# ---------------------------------------------------------------------------
# DataCleaner
# ---------------------------------------------------------------------------


class DataCleaner:
    """
    Stateless cleaner — instantiate once, call clean() as many times as needed.
    Each call returns a fresh CleaningResult.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def clean(self, raw_df: pd.DataFrame) -> CleaningResult:
        """
        Run the full cleaning pipeline and return a CleaningResult.

        Pipeline order
        --------------
        1. Schema validation
        2. Deep-copy (never mutate the caller's DataFrame)
        3. Strip whitespace on all string columns
        4. Standardise timestamps
        5. Remove exact duplicate rows
        6. Remove duplicate feedback_text
        7. Remove null / empty / whitespace-only feedback
        8. Remove meaningless feedback
        9. Reset index
        10. Invariant assertion
        """
        log = CleaningLog()

        # --- Schema validation -------------------------------------------
        is_valid, missing = validate_columns(raw_df)
        if not is_valid:
            return CleaningResult(
                error=f"Missing required columns: {', '.join(missing)}"
            )

        log.original_count = len(raw_df)
        log.operations.append(
            f"Loaded {log.original_count:,} rows with columns: "
            f"{', '.join(raw_df.columns.tolist())}"
        )

        # Work on a copy — never mutate the uploaded data
        df = raw_df.copy(deep=True)

        # Calculate Data Quality metrics on the raw input DataFrame
        ts_col = df["timestamp"]
        missing_ts_mask = ts_col.isna() | (ts_col.astype(str).str.strip() == "")
        log.missing_timestamps = int(missing_ts_mask.sum())

        def parse_and_check_invalid(x):
            if pd.isna(x) or str(x).strip() == "":
                return False  # Missing, not invalid
            return safe_parse_timestamp(x) is None

        log.invalid_timestamps = int(ts_col.apply(parse_and_check_invalid).sum())

        rating_col = df["rating"]
        log.missing_ratings = int((rating_col.isna() | (rating_col.astype(str).str.strip() == "")).sum())

        fb_col = df["feedback_text"]
        log.missing_feedback_text = int((fb_col.isna() | (fb_col.astype(str).str.strip() == "")).sum())

        # --- Step 1: Strip whitespace on all object columns ---------------
        df = self._strip_whitespace(df)
        log.operations.append("Stripped leading/trailing whitespace from all text fields.")

        # --- Step 2: Standardise timestamps --------------------------------
        df = self._standardise_timestamps(df)
        log.operations.append("Standardised timestamp column (ISO 8601 UTC format).")

        # --- Step 3: Remove exact duplicate rows ---------------------------
        before = len(df)
        df = df.drop_duplicates()
        log.removed_exact_duplicates = before - len(df)
        log.operations.append(
            f"Removed {log.removed_exact_duplicates:,} exact duplicate rows."
        )

        # --- Step 4: Remove null / empty / whitespace-only feedback --------
        before = len(df)
        df = self._remove_empty_feedback(df)
        log.removed_empty = before - len(df)
        log.operations.append(
            f"Removed {log.removed_empty:,} rows with null, empty, or "
            f"whitespace-only feedback_text."
        )

        # --- Step 5: Remove meaningless feedback ---------------------------
        before = len(df)
        df = self._remove_meaningless_feedback(df)
        log.removed_meaningless = before - len(df)
        log.operations.append(
            f"Removed {log.removed_meaningless:,} rows with meaningless feedback "
            f"(e.g. 'ok', 'test', '-', 'n/a')."
        )

        # --- Step 6: Reset index so iloc / positional access is consistent -
        df = df.reset_index(drop=True)

        log.final_count = len(df)
        log.operations.append(
            f"Final cleaned dataset: {log.final_count:,} rows "
            f"({log.retention_rate:.1f}% of original retained)."
        )

        # --- Invariant assertion -------------------------------------------
        expected = (
            log.original_count
            - log.removed_exact_duplicates
            - log.removed_empty
            - log.removed_meaningless
        )
        if log.final_count != expected:
            raise RuntimeError(
                f"Cleaning invariant violated: "
                f"expected {expected} rows after cleaning, got {log.final_count}. "
                f"This indicates overlapping removal steps — investigate pipeline."
            )

        return CleaningResult(
            original_df=raw_df,
            cleaned_df=df,
            log=log,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _strip_whitespace(df: pd.DataFrame) -> pd.DataFrame:
        """Strip leading/trailing whitespace from all string (object) columns."""
        for col in df.select_dtypes(include=["object"]).columns:
            df[col] = df[col].apply(
                lambda x: x.strip() if isinstance(x, str) else x
            )
        return df

    @staticmethod
    def _standardise_timestamps(df: pd.DataFrame) -> pd.DataFrame:
        """
        Coerce the timestamp column to ISO 8601 strings (UTC).
        Rows with unparseable timestamps are kept — only the format changes.
        NaT values are stored as empty strings so downstream display is clean.
        """
        parsed = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
        df["timestamp"] = parsed.apply(
            lambda ts: ts.isoformat() if not pd.isna(ts) else ""
        )
        return df

    @staticmethod
    def _remove_empty_feedback(df: pd.DataFrame) -> pd.DataFrame:
        """Remove rows where feedback_text is null, empty, or whitespace-only."""
        mask_null = df["feedback_text"].isna()
        mask_empty = df["feedback_text"].apply(
            lambda x: isinstance(x, str) and x.strip() == ""
        )
        return df[~(mask_null | mask_empty)].copy()

    @staticmethod
    def _remove_meaningless_feedback(df: pd.DataFrame) -> pd.DataFrame:
        """Remove rows whose feedback_text is in the MEANINGLESS_VALUES set."""
        mask = df["feedback_text"].apply(is_meaningless)
        return df[~mask].copy()
