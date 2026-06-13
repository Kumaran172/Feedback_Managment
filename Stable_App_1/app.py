"""
app.py
------
Streamlit UI layer — pure presentation.

Rules enforced in this file
---------------------------
* No data transformation or cleaning logic.
* All numbers come from session_state["enriched_df"] or session_state["cleaning_result"].
* Charts and metrics are derived from enriched_df at render time (groupby / len).
* session_state keys are defined once in _init_session_state() to avoid typos.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ai_analyzer import AIAnalyzer
from data_cleaner import DataCleaner, CleaningResult
from utils import (
    CATEGORY_COLOURS,
    format_number,
    format_percentage,
    truncate_text,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Customer Feedback Intelligence System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Session state keys
# ---------------------------------------------------------------------------

_SESSION_KEYS = {
    "cleaning_result": None,   # CleaningResult
    "api_key": "",             # str
    "file_name": "",           # str
    "explanation_cache": {},   # {feedback_text: explanation_string}
    "resolution_cache": {},    # {feedback_text: resolution_string}
}


def _init_session_state() -> None:
    for key, default in _SESSION_KEYS.items():
        if key not in st.session_state:
            st.session_state[key] = default


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------


def render_sidebar() -> str:
    """Render sidebar controls and return the current API key."""
    with st.sidebar:
        st.title("⚙️ Configuration")
        st.markdown("---")

        api_key = st.text_input(
            "Gemini API Key",
            value=st.session_state["api_key"],
            type="password",
            help="Required for AI enrichment and insights generation.",
        )
        st.session_state["api_key"] = api_key

        st.markdown("---")
        st.markdown("### Pipeline Status")

        cleaning_result: CleaningResult = st.session_state["cleaning_result"]

        def _status(done: bool, label: str) -> None:
            icon = "✅" if done else "⬜"
            st.markdown(f"{icon} {label}")

        _status(cleaning_result is not None and cleaning_result.success, "Data Cleaned")

        if cleaning_result and cleaning_result.success:
            st.markdown("---")
            st.markdown("### Audit Trail")
            for op in cleaning_result.log.operations:
                st.markdown(f"- {op}")

        st.markdown("---")
        st.caption("Customer Feedback Intelligence System v2.0")

    return api_key


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------


def render_upload_section() -> None:
    """Section 1 — Upload CSV."""
    st.header("📁 Upload Customer Feedback CSV")

    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type=["csv"],
        help="Expected columns: id, timestamp, source, rating, feedback_text",
    )

    if uploaded_file is None:
        st.info("Upload a CSV file to begin the analysis pipeline.")
        return

    # Only re-process if a new file is uploaded
    if uploaded_file.name != st.session_state["file_name"]:
        _reset_pipeline()
        st.session_state["file_name"] = uploaded_file.name

        with st.spinner("Reading file…"):
            try:
                raw_df = pd.read_csv(uploaded_file)
            except Exception as exc:
                st.error(f"Failed to read CSV: {exc}")
                return

        with st.spinner("Cleaning data…"):
            cleaner = DataCleaner()
            result = cleaner.clean(raw_df)

        if not result.success:
            st.error(f"Cleaning failed: {result.error}")
            return

        st.session_state["cleaning_result"] = result
        st.success(
            f"✅ File uploaded and cleaned. "
            f"{format_number(result.log.final_count)} records ready for exploration."
        )
        st.rerun()

    else:
        if st.session_state["cleaning_result"] and st.session_state["cleaning_result"].success:
            st.success(
                f"✅ '{uploaded_file.name}' loaded — "
                f"{format_number(st.session_state['cleaning_result'].log.final_count)} "
                f"clean records."
            )


def render_data_quality_section() -> None:
    """Section 2 — Data Quality Overview."""
    result: CleaningResult = st.session_state["cleaning_result"]
    if result is None or not result.success:
        return

    st.header("🔍 Data Quality Overview")
    log = result.log

    # Cleaning Previews (Before vs After)
    st.subheader("📊 Cleaning Preview")
    col_pre_a, col_pre_b = st.columns(2)
    with col_pre_a:
        st.markdown("**Before Cleaning (Issues Detected)**")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Original Rows", format_number(log.original_count))
        col2.metric("Duplicate Rows", format_number(log.removed_exact_duplicates))
        col3.metric("Empty Rows", format_number(log.removed_empty))
        col4.metric("Meaningless Rows", format_number(log.removed_meaningless))
    
    with col_pre_b:
        st.markdown("**After Cleaning**")
        col5, col6 = st.columns(2)
        col5.metric("Final Cleaned Rows", format_number(log.final_count))
        col6.metric("Retention Percentage", f"{log.retention_rate:.1f}%")

    st.markdown("---")

    # Data Quality Warnings Subsection
    st.subheader("⚠️ Data Quality Warnings")
    col_w1, col_w2, col_w3, col_w4 = st.columns(4)
    with col_w1:
        st.metric(
            "Missing Timestamps", 
            format_number(log.missing_timestamps), 
            delta="Warning" if log.missing_timestamps > 0 else None, 
            delta_color="inverse"
        )
    with col_w2:
        st.metric(
            "Invalid Timestamps", 
            format_number(log.invalid_timestamps), 
            delta="Warning" if log.invalid_timestamps > 0 else None, 
            delta_color="inverse"
        )
    with col_w3:
        st.metric(
            "Missing Ratings", 
            format_number(log.missing_ratings), 
            delta="Warning" if log.missing_ratings > 0 else None, 
            delta_color="inverse"
        )
    with col_w4:
        st.metric(
            "Missing Feedback Text", 
            format_number(log.missing_feedback_text), 
            delta="Warning" if log.missing_feedback_text > 0 else None, 
            delta_color="inverse"
        )

    st.markdown("---")

    col_a, col_b = st.columns(2)

    with col_a:
        # Donut chart — retained vs removed
        labels = ["Retained", "Removed"]
        values = [log.final_count, log.total_removed]
        fig = go.Figure(
            go.Pie(
                labels=labels,
                values=values,
                hole=0.5,
                marker_colors=["#2ecc71", "#e74c3c"],
            )
        )
        fig.update_layout(
            title="Records Retained vs Removed",
            showlegend=True,
            height=300,
            margin=dict(t=40, b=10, l=10, r=10),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        # Bar chart — breakdown of removal reasons
        reasons = {
            "Exact Duplicates": log.removed_exact_duplicates,
            "Empty/Null": log.removed_empty,
            "Meaningless": log.removed_meaningless,
        }
        fig2 = px.bar(
            x=list(reasons.keys()),
            y=list(reasons.values()),
            labels={"x": "Removal Reason", "y": "Count"},
            color=list(reasons.keys()),
            color_discrete_sequence=CATEGORY_COLOURS,
            title="Rows Removed by Reason",
        )
        fig2.update_layout(
            showlegend=False,
            height=300,
            margin=dict(t=40, b=10, l=10, r=10),
        )
        st.plotly_chart(fig2, use_container_width=True)


def render_cleaning_results_section() -> None:
    """Section 3 — Cleaning Results table."""
    result: CleaningResult = st.session_state["cleaning_result"]
    if result is None or not result.success:
        return

    st.header("🧹 Cleaning Results")
    log = result.log

    summary_data = {
        "Step": [
            "Original records",
            "After removing exact duplicates",
            "After removing empty/null feedback",
            "After removing meaningless feedback",
            "✅ Final cleaned records",
        ],
        "Row Count": [
            log.original_count,
            log.original_count - log.removed_exact_duplicates,
            log.original_count - log.removed_exact_duplicates - log.removed_empty,
            log.final_count,
            log.final_count,
        ],
        "Removed at This Step": [
            0,
            log.removed_exact_duplicates,
            log.removed_empty,
            log.removed_meaningless,
            0,
        ],
    }

    summary_df = pd.DataFrame(summary_data)
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

    st.markdown(
        f"**Retention rate:** {log.retention_rate:.1f}%  |  "
        f"**Total removed:** {format_number(log.total_removed)}"
    )


def render_cleaned_preview_section() -> None:
    """Section 4 — Cleaned Dataset Preview."""
    result: CleaningResult = st.session_state["cleaning_result"]
    if result is None or not result.success:
        return

    st.header("📋 Cleaned Dataset Preview")

    df = result.cleaned_df
    st.caption(
        f"Showing {min(100, len(df))} of {format_number(len(df))} records. "
        f"Download the full dataset in the Download Centre."
    )
    st.dataframe(df.head(100), use_container_width=True)


def render_cleaned_charts_section() -> None:
    """Section 4 — Charts and Analytics based on cleaned dataset."""
    result: CleaningResult = st.session_state["cleaning_result"]
    if result is None or not result.success:
        return

    st.header("📊 Dataset Charts & Analytics")
    df = result.cleaned_df

    col_a, col_b = st.columns(2)

    with col_a:
        # Rating distribution chart
        if "rating" in df.columns and not df["rating"].dropna().empty:
            rating_counts = df["rating"].value_counts().sort_index()
            fig = px.bar(
                x=rating_counts.index.astype(str),
                y=rating_counts.values,
                labels={"x": "Rating Value", "y": "Feedback Count"},
                title="Customer Ratings Distribution",
                color=rating_counts.index.astype(str),
                color_discrete_sequence=CATEGORY_COLOURS,
            )
            fig.update_layout(
                showlegend=False,
                height=350,
                margin=dict(t=40, b=10, l=10, r=10),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No rating data available for chart rendering.")

    with col_b:
        # Source distribution chart
        if "source" in df.columns and not df["source"].dropna().empty:
            source_counts = df["source"].value_counts()
            fig2 = px.pie(
                names=source_counts.index,
                values=source_counts.values,
                title="Feedback Sources Share",
                color_discrete_sequence=CATEGORY_COLOURS,
                hole=0.4
            )
            fig2.update_layout(
                height=350,
                margin=dict(t=40, b=10, l=10, r=10),
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No source data available for chart rendering.")


def render_feedback_explorer() -> None:
    """Section 5 — Feedback Explorer (On-demand row-level analysis)."""
    result: CleaningResult = st.session_state["cleaning_result"]
    if result is None or not result.success:
        return

    st.header("🔍 Feedback Explorer")
    st.markdown(
        "Explore individual feedback reviews and run on-demand AI analysis to "
        "explain details or suggest resolution strategies."
    )

    df = result.cleaned_df

    # Filter controls
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        unique_sources = sorted(list(df["source"].dropna().unique())) if "source" in df.columns else []
        source_filter = st.selectbox("Filter by Source", ["All"] + unique_sources)
    with col_f2:
        unique_ratings = sorted(list(df["rating"].dropna().unique())) if "rating" in df.columns else []
        rating_filter = st.selectbox("Filter by Rating", ["All"] + [str(r) for r in unique_ratings])

    # Filtering data
    filtered_df = df
    if "source" in df.columns and source_filter != "All":
        filtered_df = filtered_df[filtered_df["source"] == source_filter]
    if "rating" in df.columns and rating_filter != "All":
        filtered_df = filtered_df[filtered_df["rating"] == float(rating_filter)]

    total_filtered = len(filtered_df)
    st.caption(f"Showing {total_filtered} records matching filter criteria.")

    if total_filtered == 0:
        st.info("No feedback items match the selected filters.")
        return

    # Pagination controls
    rows_per_page = 10
    total_pages = max(1, (total_filtered - 1) // rows_per_page + 1)
    
    # Store page in session state
    if "explorer_page" not in st.session_state:
        st.session_state["explorer_page"] = 1
        
    # Reset page if out of bounds (due to filter change)
    if st.session_state["explorer_page"] > total_pages:
        st.session_state["explorer_page"] = 1

    col_p1, col_p2, col_p3 = st.columns([1, 4, 1])
    with col_p1:
        if st.button("⬅️ Previous", disabled=st.session_state["explorer_page"] <= 1):
            st.session_state["explorer_page"] -= 1
            st.rerun()
    with col_p2:
        st.markdown(
            f"<p style='text-align: center;'>Page <b>{st.session_state['explorer_page']}</b> of <b>{total_pages}</b></p>", 
            unsafe_allow_html=True
        )
    with col_p3:
        if st.button("Next ➡️", disabled=st.session_state["explorer_page"] >= total_pages):
            st.session_state["explorer_page"] += 1
            st.rerun()

    # Get page slice
    start_idx = (st.session_state["explorer_page"] - 1) * rows_per_page
    end_idx = min(start_idx + rows_per_page, total_filtered)
    page_df = filtered_df.iloc[start_idx:end_idx]

    # Ensure caches exist
    if "explanation_cache" not in st.session_state:
        st.session_state["explanation_cache"] = {}
    if "resolution_cache" not in st.session_state:
        st.session_state["resolution_cache"] = {}

    # Render each row in an expander
    for idx, row in page_df.iterrows():
        text = row["feedback_text"]
        source = row.get("source", "Unknown")
        rating = row.get("rating", "N/A")

        with st.expander(f"⭐ {rating} | [{source}] {truncate_text(text, 90)}"):
            st.markdown(f"**Feedback Text:**\n_{text}_")
            st.markdown(f"**Source:** {source}  |  **Rating:** {rating}")
            
            c_btn1, c_btn2 = st.columns(2)
            
            # Use unique keys based on row feedback text
            explain_key = text
            resolve_key = text
            
            with c_btn1:
                if st.button("🧠 Explain Feedback", key=f"btn_exp_{idx}"):
                    if explain_key not in st.session_state["explanation_cache"]:
                        with st.spinner("Analyzing feedback..."):
                            api_key = st.session_state["api_key"]
                            if api_key:
                                analyzer = AIAnalyzer(api_key=api_key)
                                result_text = analyzer.explain_feedback(text)
                                st.session_state["explanation_cache"][explain_key] = result_text
                            else:
                                st.error("Please configure Gemini API key in sidebar.")

            with c_btn2:
                if st.button("💡 Suggest Resolution", key=f"btn_res_{idx}"):
                    if resolve_key not in st.session_state["resolution_cache"]:
                        with st.spinner("Formulating resolution suggestion..."):
                            api_key = st.session_state["api_key"]
                            if api_key:
                                analyzer = AIAnalyzer(api_key=api_key)
                                result_text = analyzer.suggest_resolution(text)
                                st.session_state["resolution_cache"][resolve_key] = result_text
                            else:
                                st.error("Please configure Gemini API key in sidebar.")

            # Display explanation if it exists in cache
            if explain_key in st.session_state["explanation_cache"]:
                st.info(f"**Explanation:**\n\n{st.session_state['explanation_cache'][explain_key]}")
                
            # Display resolution if it exists in cache
            if resolve_key in st.session_state["resolution_cache"]:
                st.success(f"**Resolution Suggestion:**\n\n{st.session_state['resolution_cache'][resolve_key]}")


def render_download_center() -> None:
    """Section 6 — Download Centre."""
    result: CleaningResult = st.session_state["cleaning_result"]

    if result is None or not result.success:
        return

    st.header("⬇️ Download Centre")

    cleaned_csv = result.cleaned_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Cleaned Dataset (CSV)",
        data=cleaned_csv,
        file_name="cleaned_feedback.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.caption(f"{format_number(len(result.cleaned_df))} records")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reset_pipeline() -> None:
    """Clear all pipeline outputs when a new file is uploaded."""
    st.session_state["cleaning_result"] = None
    st.session_state["explanation_cache"] = {}
    st.session_state["resolution_cache"] = {}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    _init_session_state()

    st.title("📊 Customer Feedback Intelligence System")
    st.markdown(
        "A production-grade pipeline for cleaning, enriching, and analysing "
        "customer feedback data."
    )
    st.markdown("---")

    render_sidebar()

    # Render all sections in order — each checks its own prerequisites
    render_upload_section()
    render_data_quality_section()
    render_cleaning_results_section()
    render_cleaned_preview_section()
    render_cleaned_charts_section()
    render_feedback_explorer()
    render_download_center()


if __name__ == "__main__":
    main()
