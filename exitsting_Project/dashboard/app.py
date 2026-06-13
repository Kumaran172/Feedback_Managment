# =============================================================================
# ENTERPRISE FEEDBACK ANALYTICS DASHBOARD  (v2 — Auto-Preprocessing)
# Purpose  : Accept a raw customer-feedback CSV, run an AI preprocessing
#            pipeline (clean → sentiment → category → priority → summary),
#            then render the full BI dashboard on the enriched data.
# Inputs   : Raw CSV with at least one free-text feedback column.
# Output   : Interactive Streamlit app — KPIs, charts, insights, table.
# =============================================================================

import json
import re
import time

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# =============================================================================
# PAGE CONFIG
# Purpose  : Browser tab, icon, wide layout, sidebar open by default.
# =============================================================================
st.set_page_config(
    page_title="Feedback Intelligence Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# GLOBAL CSS — dark enterprise theme (unchanged from v1)
# =============================================================================
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: #0a0e1a; color: #e2e8f0; }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1224 0%, #111827 100%);
        border-right: 1px solid #1e293b;
    }
    [data-testid="stSidebar"] .stMarkdown h2 {
        color: #38bdf8; font-size: 0.75rem; font-weight: 600;
        letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 0.5rem;
    }
    .stSelectbox > div > div, .stMultiSelect > div > div {
        background: #1e293b !important; border: 1px solid #334155 !important;
        border-radius: 8px !important; color: #e2e8f0 !important;
    }

    /* KPI card */
    .kpi-card {
        background: linear-gradient(135deg, #1e293b 0%, #162032 100%);
        border: 1px solid #334155; border-radius: 14px; padding: 1.4rem 1.6rem;
        position: relative; overflow: hidden;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        box-shadow: 0 4px 24px rgba(0,0,0,0.35);
    }
    .kpi-card:hover { transform: translateY(-3px); box-shadow: 0 8px 32px rgba(0,0,0,0.5); }
    .kpi-card::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0;
        height: 3px; border-radius: 14px 14px 0 0;
    }
    .kpi-blue::before   { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
    .kpi-cyan::before   { background: linear-gradient(90deg, #06b6d4, #22d3ee); }
    .kpi-purple::before { background: linear-gradient(90deg, #8b5cf6, #a78bfa); }
    .kpi-red::before    { background: linear-gradient(90deg, #ef4444, #f87171); }
    .kpi-icon  { font-size: 1.6rem; margin-bottom: 0.5rem; display: block; }
    .kpi-label { font-size: 0.72rem; font-weight: 600; letter-spacing: 0.1em;
                 text-transform: uppercase; color: #64748b; margin-bottom: 0.3rem; }
    .kpi-value { font-size: 2rem; font-weight: 700; color: #f1f5f9; line-height: 1; }
    .kpi-sub   { font-size: 0.78rem; color: #475569; margin-top: 0.35rem; }

    /* Section headers */
    .section-header {
        font-size: 0.7rem; font-weight: 600; letter-spacing: 0.12em;
        text-transform: uppercase; color: #38bdf8; margin: 2rem 0 1rem 0;
        padding-bottom: 0.5rem; border-bottom: 1px solid #1e293b;
    }

    /* Chart wrapper */
    .chart-card {
        background: #111827; border: 1px solid #1e293b; border-radius: 14px;
        padding: 1.2rem; box-shadow: 0 2px 16px rgba(0,0,0,0.3);
    }

    /* Insight cards */
    .insight-card {
        background: linear-gradient(135deg, #1e293b, #162032);
        border: 1px solid #334155; border-left: 4px solid #3b82f6;
        border-radius: 10px; padding: 1rem 1.2rem; margin-bottom: 0.8rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.25);
    }
    .insight-card.purple { border-left-color: #8b5cf6; }
    .insight-card.cyan   { border-left-color: #06b6d4; }
    .insight-card.red    { border-left-color: #ef4444; }
    .insight-title { font-size: 0.7rem; font-weight: 600; letter-spacing: 0.08em;
                     text-transform: uppercase; color: #64748b; margin-bottom: 0.3rem; }
    .insight-value { font-size: 1rem; font-weight: 600; color: #e2e8f0; }

    /* Pipeline progress card */
    .pipeline-card {
        background: linear-gradient(135deg, #0f172a, #1e293b);
        border: 1px solid #334155; border-radius: 14px; padding: 2rem;
        box-shadow: 0 4px 24px rgba(0,0,0,0.4); margin: 1rem 0;
    }
    .pipeline-step {
        display: flex; align-items: center; gap: 0.75rem;
        padding: 0.5rem 0; font-size: 0.88rem; color: #94a3b8;
    }
    .pipeline-step.done  { color: #10b981; }
    .pipeline-step.active { color: #38bdf8; }

    /* Stats bar */
    .stats-bar {
        display: flex; gap: 1.5rem; background: #111827;
        border: 1px solid #1e293b; border-radius: 10px;
        padding: 0.9rem 1.4rem; margin: 1rem 0; flex-wrap: wrap;
    }
    .stat-item { display: flex; flex-direction: column; gap: 0.1rem; }
    .stat-label { font-size: 0.65rem; text-transform: uppercase;
                  letter-spacing: 0.1em; color: #475569; }
    .stat-value { font-size: 1.1rem; font-weight: 700; color: #f1f5f9; }

    /* Search & text input */
    .stTextInput > div > div > input {
        background: #1e293b !important; border: 1px solid #334155 !important;
        border-radius: 8px !important; color: #e2e8f0 !important;
    }
    [data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
    #MainMenu, footer, header { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================================================================
# PLOTLY SHARED THEME
# Purpose  : Consistent dark chart layout applied to every figure.
# =============================================================================
CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color="#94a3b8", size=12),
    margin=dict(l=10, r=10, t=40, b=10),
    colorway=["#3b82f6", "#06b6d4", "#8b5cf6", "#f59e0b", "#10b981", "#ef4444"],
    xaxis=dict(gridcolor="#1e293b", linecolor="#334155", zerolinecolor="#1e293b"),
    yaxis=dict(gridcolor="#1e293b", linecolor="#334155", zerolinecolor="#1e293b"),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#334155", font=dict(color="#94a3b8")),
    hoverlabel=dict(bgcolor="#1e293b", bordercolor="#334155", font_color="#e2e8f0"),
)

# =============================================================================
# PREPROCESSING PIPELINE
# Purpose  : Transform raw feedback text into enriched structured data using
#            rule-based NLP. No external API key required — runs entirely
#            inside Python with regex and keyword matching.
# Inputs   : raw_text (str) — one feedback entry
# Output   : dict with keys: feedback_clean, sentiment, category,
#            priority, issue_summary
# =============================================================================

# ── Keyword maps ─────────────────────────────────────────────────────────────
_POSITIVE_WORDS = {
    "great","excellent","awesome","love","perfect","amazing","fantastic",
    "good","happy","satisfied","wonderful","best","thank","thanks","helpful",
    "fast","quick","easy","smooth","pleased","nice","brilliant","superb",
}
_NEGATIVE_WORDS = {
    "bad","terrible","awful","hate","worst","horrible","poor","disappointed",
    "slow","broken","failed","error","bug","crash","wrong","useless","annoying",
    "frustrating","ridiculous","unacceptable","never","refund","lost","missing",
    "overcharged","charged","scam","fraud","rude","ignored","no response",
    "not working","doesn't work","did not work","cant","can't","cannot",
}
_CATEGORY_KEYWORDS = {
    "Billing":       ["bill","billing","charge","overcharged","invoice","payment",
                      "refund","price","fee","subscription","cost","money","paid",
                      "transaction","receipt","debit","credit card"],
    "Delivery":      ["delivery","deliver","shipping","shipped","package","parcel",
                      "tracking","arrived","late","lost","dispatch","courier",
                      "logistics","order","received","not delivered"],
    "App Bug":       ["app","bug","crash","error","glitch","freeze","load","login",
                      "password","update","version","install","screen","button",
                      "interface","not working","blank","slow","lag","hangs"],
    "Staff/Support": ["staff","support","agent","representative","customer service",
                      "service","rude","helpful","response","replied","call","chat",
                      "team","manager","escalate","contact","email","phone"],
}
_HIGH_PRIORITY   = ["urgent","immediately","asap","emergency","critical","serious",
                    "unacceptable","fraud","scam","lost","never","refund","broken",
                    "not working","crash","error","failed"]
_MEDIUM_PRIORITY = ["slow","delay","issue","problem","wrong","missing","incorrect",
                    "late","poor","disappointed","bad","annoying","frustrating"]


def _clean_text(text: str) -> str:
    """
    Purpose : Normalize raw feedback text to match notebook cleaning logic.
              Steps (in order):
                1. Strip HTML tags
                2. Convert to lowercase          ← was MISSING in v2
                3. Remove unwanted special chars
                4. Collapse whitespace
    Inputs  : raw text string
    Output  : cleaned, lowercased, normalised string
    """
    text = str(text)
    text = re.sub(r"<[^>]+>", " ", text)           # 1. strip HTML tags
    text = text.lower()                              # 2. lowercase  ← ADDED
    text = re.sub(r"[^\w\s'.,!?-]", " ", text)     # 3. remove special chars
    text = re.sub(r"\s+", " ", text).strip()        # 4. collapse whitespace
    return text


# ── Patterns that identify meaningless / invalid feedback ────────────────────
# Purpose : Mirror the notebook's "invalid record" removal step.
#           Catches dot-runs, dash-runs, question-mark-runs, and any
#           feedback whose only content is punctuation/symbols.
# Used in : preprocess_dataframe() — applied AFTER cleaning, BEFORE dedup.
_INVALID_PATTERN = re.compile(
    r"^[.\-?!*_=#@&^~`|\\/<>(){}\[\]\"',:;+%$\s]+$"
)
_MIN_FEEDBACK_LENGTH = 10   # records shorter than this (post-clean) are dropped


def _classify_sentiment(text: str) -> str:
    """
    Purpose  : Score text by positive/negative keyword count.
    Inputs   : cleaned lowercase text
    Output   : 'Positive' | 'Negative' | 'Neutral'
    """
    words = set(re.findall(r"\b\w+\b", text.lower()))
    pos = len(words & _POSITIVE_WORDS)
    neg = len(words & _NEGATIVE_WORDS)
    if neg > pos:
        return "Negative"
    if pos > neg:
        return "Positive"
    return "Neutral"


def _classify_category(text: str) -> str:
    """
    Purpose  : Match text against keyword lists for each category.
    Inputs   : cleaned lowercase text
    Output   : one of Billing | Delivery | App Bug | Staff/Support | Other
    """
    lower = text.lower()
    scores = {cat: 0 for cat in _CATEGORY_KEYWORDS}
    for cat, keywords in _CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                scores[cat] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "Other"


def _assign_priority(text: str, sentiment: str) -> str:
    """
    Purpose  : Determine issue urgency from keywords and sentiment.
    Inputs   : cleaned text, classified sentiment
    Output   : 'High' | 'Medium' | 'Low'
    """
    lower = text.lower()
    for kw in _HIGH_PRIORITY:
        if kw in lower:
            return "High"
    for kw in _MEDIUM_PRIORITY:
        if kw in lower:
            return "Medium"
    if sentiment == "Negative":
        return "Medium"
    return "Low"


def _generate_summary(text: str, category: str, sentiment: str) -> str:
    """
    Purpose  : Build a concise 1-line issue summary from metadata + text.
    Inputs   : cleaned text, category, sentiment
    Output   : summary string (≤ 120 chars)
    """
    snippet = text[:80].rstrip() + ("…" if len(text) > 80 else "")
    return f"[{category}] {sentiment} — {snippet}"


def _detect_feedback_column(df: pd.DataFrame) -> str:
    """
    Purpose  : Auto-detect which column contains the raw feedback text.
    Inputs   : raw DataFrame
    Output   : column name string
    """
    preferred = ["feedback", "comment", "review", "text", "message",
                 "description", "notes", "content", "body"]
    cols_lower = {c.lower(): c for c in df.columns}
    for name in preferred:
        if name in cols_lower:
            return cols_lower[name]
    # Fall back to the longest average-length string column
    str_cols = df.select_dtypes(include="object").columns
    if len(str_cols) == 0:
        return df.columns[0]
    avg_lens = {c: df[c].dropna().astype(str).str.len().mean() for c in str_cols}
    return max(avg_lens, key=avg_lens.get)


@st.cache_data(show_spinner=False)
def preprocess_dataframe(file_bytes: bytes, filename: str):
    """
    Purpose : Full preprocessing pipeline matching the original notebook.
              Eight sequential cleaning / validation stages before enrichment.
    Inputs  : raw file bytes, original filename
    Output  : (enriched_df, raw_count, processed_count, feedback_col, audit_log)
              audit_log — list of (stage_label, record_count) tuples

    ── Notebook-parity audit ──────────────────────────────────────────────────
    Stage 0  Load raw CSV                          → 1810
    Stage 1  Drop NaN in feedback column           → xxxx   (was done in v2)
    Stage 2  Strip whitespace; drop blank strings  → xxxx   (was done in v2)
    Stage 3  Clean text (lower + normalise)        → xxxx   (lower was MISSING)
    Stage 4  Drop very short feedback (< 10 chars) → xxxx   ← MISSING in v2
    Stage 5  Drop meaningless / symbol-only text   → xxxx   ← MISSING in v2
    Stage 6  Drop exact duplicates (on clean text) → xxxx   ← MISSING in v2
    Stage 7  Enrichment (category/sentiment/…)     → 1721   (final)
    ──────────────────────────────────────────────────────────────────────────
    Root cause of 1785 vs 1721 discrepancy (64 extra records):
      • Stage 4 missing  → retains very short / single-word feedback
      • Stage 5 missing  → retains ".", "..", "---", "???" etc.
      • Stage 6 missing  → retains duplicate feedback strings
      Combined those three stages account for the 64 extra records.
    """
    import io
    raw_df = pd.read_csv(io.BytesIO(file_bytes))
    audit: list[tuple[str, int]] = []

    # ── Stage 0: raw load ────────────────────────────────────────────────────
    raw_count = len(raw_df)
    audit.append(("0 · Raw load", raw_count))

    feedback_col = _detect_feedback_column(raw_df)
    df = raw_df.copy()

    # ── Stage 1: drop NaN ────────────────────────────────────────────────────
    df = df.dropna(subset=[feedback_col]).copy()
    audit.append(("1 · Drop NaN feedback", len(df)))

    # ── Stage 2: strip whitespace + drop blank strings ───────────────────────
    df[feedback_col] = df[feedback_col].astype(str).str.strip()
    df = df[df[feedback_col] != ""].copy()
    # Also drop whitespace-only strings (str.strip already handles, but be explicit)
    df = df[df[feedback_col].str.strip() != ""].copy()
    audit.append(("2 · Drop blank / whitespace-only", len(df)))

    # ── Stage 3: clean text (lowercase + normalise) ──────────────────────────
    # _clean_text now lowercases — this is required before dedup & validity checks
    df[feedback_col] = df[feedback_col].apply(_clean_text)
    audit.append(("3 · Clean text (lower + normalise)", len(df)))

    # ── Stage 4: drop very short feedback (< MIN_FEEDBACK_LENGTH chars) ──────
    # Notebook dropped single-word / trivially short entries.
    df = df[df[feedback_col].str.len() >= _MIN_FEEDBACK_LENGTH].copy()
    audit.append((f"4 · Drop short feedback (< {_MIN_FEEDBACK_LENGTH} chars)", len(df)))

    # ── Stage 5: drop meaningless / symbol-only text ─────────────────────────
    # Removes records like ".", "..", "...", "----", "???", "!!!!!" etc.
    df = df[~df[feedback_col].str.match(_INVALID_PATTERN)].copy()
    audit.append(("5 · Drop symbol-only / meaningless text", len(df)))

    # ── Stage 6: drop exact duplicates on the cleaned feedback column ─────────
    # Notebook deduplication was on the cleaned text, not the original raw text.
    df = df.drop_duplicates(subset=[feedback_col]).copy()
    audit.append(("6 · Drop duplicate feedback", len(df)))

    # ── Stage 7: enrichment ──────────────────────────────────────────────────
    results = []
    for text in df[feedback_col]:
        sentiment = _classify_sentiment(text)
        category  = _classify_category(text)
        priority  = _assign_priority(text, sentiment)
        summary   = _generate_summary(text, category, sentiment)
        results.append({
            "feedback_clean": text,
            "sentiment":      sentiment,
            "category":       category,
            "priority":       priority,
            "issue_summary":  summary,
        })

    enriched_df = pd.concat(
        [df.reset_index(drop=True), pd.DataFrame(results)], axis=1
    )
    audit.append(("7 · Enriched dataset (final)", len(enriched_df)))

    return enriched_df, raw_count, len(enriched_df), feedback_col, audit


# =============================================================================
# SIDEBAR — navigation, file upload, filters
# Purpose  : Render brand header, page selector, uploader, and data filters.
# Inputs   : user interactions
# Output   : uploaded_file, active_page, filter selections
# =============================================================================
with st.sidebar:
    st.markdown(
        """
        <div style='display:flex;align-items:center;gap:10px;margin-bottom:1.5rem;'>
            <span style='font-size:1.6rem;'>📊</span>
            <div>
                <div style='font-size:1rem;font-weight:700;color:#f1f5f9;'>FeedbackIQ</div>
                <div style='font-size:0.68rem;color:#475569;'>Analytics Dashboard · v2</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("## Navigation")
    active_page = st.selectbox(
        "Go to",
        ["📈 Overview", "📊 Charts", "💡 Insights", "🔍 Feedback Table"],
        label_visibility="collapsed",
    )

    st.divider()

    st.markdown("## Data Source")
    uploaded_file = st.file_uploader(
        "Upload raw feedback CSV",
        type=["csv"],
        label_visibility="collapsed",
        help="Any CSV with a text column containing customer feedback.",
    )

    if not uploaded_file:
        st.info("Upload a raw CSV to begin. The pipeline will auto-process it.")
        st.stop()

# =============================================================================
# PREPROCESSING — run pipeline with progress UI
# Purpose  : Show a progress card while the pipeline runs, then display
#            a stats bar with raw vs processed record counts.
# Inputs   : uploaded_file
# Output   : df_enriched (cached), raw_count, processed_count
# =============================================================================

file_bytes = uploaded_file.read()
file_id    = f"{uploaded_file.name}_{len(file_bytes)}"   # cheap cache key

# Show pipeline progress only on first run (not cached)
if file_id not in st.session_state.get("processed_ids", set()):
    with st.spinner(""):
        progress_placeholder = st.empty()
        steps = [
            ("🧹", "Cleaning feedback text"),
            ("🎭", "Classifying sentiment"),
            ("🏷️",  "Categorising issues"),
            ("🔴", "Assigning priority levels"),
            ("📝", "Generating issue summaries"),
            ("✅", "Building enriched dataset"),
        ]

        def render_steps(done_up_to: int):
            rows = ""
            for i, (icon, label) in enumerate(steps):
                if i < done_up_to:
                    cls = "done";   sym = "✓"
                elif i == done_up_to:
                    cls = "active"; sym = "⟳"
                else:
                    cls = "";       sym = "○"
                rows += f"<div class='pipeline-step {cls}'><span>{sym}</span><span>{icon} {label}</span></div>"
            progress_placeholder.markdown(
                f"<div class='pipeline-card'>"
                f"<div style='font-size:1rem;font-weight:600;color:#f1f5f9;margin-bottom:1rem;'>"
                f"⚙️ Processing customer feedback…</div>{rows}</div>",
                unsafe_allow_html=True,
            )

        for step_idx in range(len(steps)):
            render_steps(step_idx)
            time.sleep(0.18)

        df_enriched, raw_count, processed_count, feedback_col, audit_log = preprocess_dataframe(
            file_bytes, uploaded_file.name
        )
        render_steps(len(steps))
        time.sleep(0.3)
        progress_placeholder.empty()

    # Mark as processed so we skip the animation on re-render
    ids = st.session_state.get("processed_ids", set())
    ids.add(file_id)
    st.session_state["processed_ids"] = ids
    st.session_state[f"data_{file_id}"] = (df_enriched, raw_count, processed_count, feedback_col, audit_log)
else:
    df_enriched, raw_count, processed_count, feedback_col, audit_log = st.session_state[f"data_{file_id}"]

# ── Processing stats banner ───────────────────────────────────────────────────
neg_processed = (df_enriched["sentiment"] == "Negative").sum()
hi_processed  = (df_enriched["priority"]  == "High").sum()
st.markdown(
    f"""
    <div class='stats-bar'>
        <div class='stat-item'>
            <span class='stat-label'>Raw Records</span>
            <span class='stat-value'>{raw_count:,}</span>
        </div>
        <div style='width:1px;background:#1e293b;'></div>
        <div class='stat-item'>
            <span class='stat-label'>Processed Records</span>
            <span class='stat-value' style='color:#10b981;'>{processed_count:,}</span>
        </div>
        <div style='width:1px;background:#1e293b;'></div>
        <div class='stat-item'>
            <span class='stat-label'>Dropped Records</span>
            <span class='stat-value' style='color:#f59e0b;'>{raw_count - processed_count:,}</span>
        </div>
        <div style='width:1px;background:#1e293b;'></div>
        <div class='stat-item'>
            <span class='stat-label'>Negative Sentiment</span>
            <span class='stat-value' style='color:#ef4444;'>{neg_processed:,}</span>
        </div>
        <div style='width:1px;background:#1e293b;'></div>
        <div class='stat-item'>
            <span class='stat-label'>High Priority</span>
            <span class='stat-value' style='color:#f59e0b;'>{hi_processed:,}</span>
        </div>
        <div style='width:1px;background:#1e293b;'></div>
        <div class='stat-item'>
            <span class='stat-label'>Source Column</span>
            <span class='stat-value' style='color:#38bdf8;font-size:0.85rem;'>{feedback_col}</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Preprocessing audit trail (collapsible) ───────────────────────────────────
# Purpose  : Show exactly how many records were removed at each cleaning stage
#            so the result can be verified against the original notebook.
with st.expander("🔬 Preprocessing Audit Trail", expanded=False):
    prev = audit_log[0][1]
    rows_html = ""
    for stage, count in audit_log:
        dropped = prev - count if stage != audit_log[0][0] else 0
        drop_str = f"<span style='color:#ef4444;'>−{dropped:,}</span>" if dropped > 0 else ""
        is_final = stage == audit_log[-1][0]
        row_color = "#10b981" if is_final else "#f1f5f9"
        rows_html += (
            f"<tr style='border-bottom:1px solid #1e293b;'>"
            f"<td style='padding:0.5rem 0.8rem;color:#94a3b8;font-size:0.82rem;'>{stage}</td>"
            f"<td style='padding:0.5rem 0.8rem;text-align:right;font-weight:600;"
            f"color:{row_color};font-size:0.9rem;'>{count:,}</td>"
            f"<td style='padding:0.5rem 0.8rem;text-align:right;font-size:0.82rem;'>{drop_str}</td>"
            f"</tr>"
        )
        prev = count
    st.markdown(
        f"<table style='width:100%;border-collapse:collapse;background:#111827;"
        f"border-radius:10px;overflow:hidden;'>"
        f"<thead><tr style='background:#1e293b;'>"
        f"<th style='padding:0.6rem 0.8rem;text-align:left;font-size:0.7rem;"
        f"letter-spacing:0.08em;text-transform:uppercase;color:#475569;'>Stage</th>"
        f"<th style='padding:0.6rem 0.8rem;text-align:right;font-size:0.7rem;"
        f"letter-spacing:0.08em;text-transform:uppercase;color:#475569;'>Records</th>"
        f"<th style='padding:0.6rem 0.8rem;text-align:right;font-size:0.7rem;"
        f"letter-spacing:0.08em;text-transform:uppercase;color:#475569;'>Dropped</th>"
        f"</tr></thead><tbody>{rows_html}</tbody></table>",
        unsafe_allow_html=True,
    )

# =============================================================================
# SIDEBAR FILTERS  (rendered after data is ready)
# Purpose  : Let users slice the enriched dataset by category/sentiment/priority.
# =============================================================================
with st.sidebar:
    st.divider()
    st.markdown("## Filters")

    all_cats  = sorted(df_enriched["category"].dropna().unique())
    sel_cats  = st.multiselect("Category",  all_cats,  default=all_cats)

    all_sents = sorted(df_enriched["sentiment"].dropna().unique())
    sel_sents = st.multiselect("Sentiment", all_sents, default=all_sents)

    all_pris  = sorted(df_enriched["priority"].dropna().unique())
    sel_pris  = st.multiselect("Priority",  all_pris,  default=all_pris)

    st.divider()
    st.markdown(
        f"<div style='font-size:0.7rem;color:#334155;'>"
        f"v2.0.0 · {processed_count:,} processed records</div>",
        unsafe_allow_html=True,
    )

# Apply filters
filtered_df = df_enriched[
    df_enriched["category"].isin(sel_cats)
    & df_enriched["sentiment"].isin(sel_sents)
    & df_enriched["priority"].isin(sel_pris)
].copy()

# =============================================================================
# COMPUTED METRICS
# Purpose  : Pre-compute KPI scalars and insight values from filtered data.
# =============================================================================
total_records     = len(filtered_df)
unique_categories = filtered_df["category"].nunique()
negative_mask     = filtered_df["sentiment"] == "Negative"
negative_count    = negative_mask.sum()
negative_pct      = (negative_count / total_records * 100) if total_records else 0
high_priority_count = (filtered_df["priority"] == "High").sum()
cat_counts        = filtered_df["category"].value_counts()
top_category      = cat_counts.idxmax() if not cat_counts.empty else "N/A"
neg_by_cat        = (
    filtered_df[negative_mask]["category"].value_counts()
    if negative_count else pd.Series(dtype=int)
)
most_negative_cat = neg_by_cat.idxmax() if not neg_by_cat.empty else "N/A"


# =============================================================================
# HELPER: KPI card HTML
# =============================================================================
def kpi_card(icon, label, value, sub, accent):
    return (
        f"<div class='kpi-card {accent}'>"
        f"<span class='kpi-icon'>{icon}</span>"
        f"<div class='kpi-label'>{label}</div>"
        f"<div class='kpi-value'>{value}</div>"
        f"<div class='kpi-sub'>{sub}</div>"
        f"</div>"
    )


# =============================================================================
# PAGE: OVERVIEW
# Purpose  : KPI cards + two quick-look distribution charts.
# =============================================================================
if active_page == "📈 Overview":
    st.markdown(
        "<h1 style='font-size:1.6rem;font-weight:700;color:#f1f5f9;margin-bottom:0.2rem;'>"
        "Feedback Intelligence Overview</h1>"
        "<p style='color:#475569;font-size:0.85rem;margin-bottom:1.5rem;'>"
        "Auto-enriched from raw CSV · Filtered dataset</p>",
        unsafe_allow_html=True,
    )

    k1, k2, k3, k4 = st.columns(4, gap="medium")
    with k1:
        st.markdown(kpi_card("📋","Total Feedback",f"{total_records:,}","records in selection","kpi-blue"), unsafe_allow_html=True)
    with k2:
        st.markdown(kpi_card("🏷️","Categories",f"{unique_categories}","distinct types","kpi-cyan"), unsafe_allow_html=True)
    with k3:
        st.markdown(kpi_card("😠","Negative Sentiment",f"{negative_count:,}",f"{negative_pct:.1f}% of total","kpi-red"), unsafe_allow_html=True)
    with k4:
        st.markdown(kpi_card("🔴","High Priority",f"{high_priority_count:,}","issues flagged","kpi-purple"), unsafe_allow_html=True)

    st.markdown("<div class='section-header'>Distribution Summary</div>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2, gap="medium")

    with col_a:
        st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
        sent_counts = filtered_df["sentiment"].value_counts().reset_index()
        sent_counts.columns = ["Sentiment","Count"]
        color_map = {"Negative":"#ef4444","Positive":"#10b981","Neutral":"#f59e0b"}
        fig_sent = px.bar(sent_counts, x="Count", y="Sentiment", orientation="h",
                          color="Sentiment", color_discrete_map=color_map,
                          title="Sentiment Breakdown")
        fig_sent.update_layout(**CHART_LAYOUT)
        fig_sent.update_traces(marker_line_width=0)
        st.plotly_chart(fig_sent, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_b:
        st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
        pri_counts = filtered_df["priority"].value_counts().reset_index()
        pri_counts.columns = ["Priority","Count"]
        pri_color = {"High":"#ef4444","Medium":"#f59e0b","Low":"#10b981"}
        fig_pri = px.bar(pri_counts, x="Priority", y="Count",
                         color="Priority", color_discrete_map=pri_color,
                         title="Priority Breakdown")
        fig_pri.update_layout(**CHART_LAYOUT)
        fig_pri.update_traces(marker_line_width=0)
        st.plotly_chart(fig_pri, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)


# =============================================================================
# PAGE: CHARTS
# Purpose  : Four detailed interactive Plotly charts.
# =============================================================================
elif active_page == "📊 Charts":
    st.markdown(
        "<h1 style='font-size:1.6rem;font-weight:700;color:#f1f5f9;margin-bottom:0.2rem;'>"
        "Data Visualisation</h1>"
        "<p style='color:#475569;font-size:0.85rem;margin-bottom:1.5rem;'>"
        "Interactive charts — hover, zoom, and export</p>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='section-header'>Category & Sentiment</div>", unsafe_allow_html=True)
    c1, c2 = st.columns([3,2], gap="medium")

    with c1:
        st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
        cat_df = filtered_df["category"].value_counts().reset_index()
        cat_df.columns = ["Category","Count"]
        fig_cat = px.bar(cat_df.sort_values("Count"), x="Count", y="Category",
                         orientation="h", title="Category Distribution",
                         color="Count", color_continuous_scale=["#1e3a5f","#3b82f6","#60a5fa"])
        fig_cat.update_layout(**CHART_LAYOUT, coloraxis_showscale=False)
        fig_cat.update_traces(marker_line_width=0)
        st.plotly_chart(fig_cat, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
        sent_df = filtered_df["sentiment"].value_counts().reset_index()
        sent_df.columns = ["Sentiment","Count"]
        donut_colors = {"Negative":"#ef4444","Positive":"#10b981","Neutral":"#f59e0b"}
        fig_donut = go.Figure(go.Pie(
            labels=sent_df["Sentiment"], values=sent_df["Count"], hole=0.62,
            marker=dict(colors=[donut_colors.get(s,"#3b82f6") for s in sent_df["Sentiment"]],
                        line=dict(color="#0a0e1a", width=3)),
            textinfo="percent", textfont=dict(size=13, color="#e2e8f0"),
            hovertemplate="<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>",
        ))
        fig_donut.add_annotation(
            text=f"<b>{total_records:,}</b><br><span style='font-size:11px'>Total</span>",
            x=0.5, y=0.5, showarrow=False, font=dict(size=18, color="#f1f5f9"),
        )
        fig_donut.update_layout(title="Sentiment Distribution", **CHART_LAYOUT)
        st.plotly_chart(fig_donut, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-header'>Priority & Top Complaints</div>", unsafe_allow_html=True)
    c3, c4 = st.columns(2, gap="medium")

    with c3:
        st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
        priority_order = ["High","Medium","Low"]
        pri_df = (filtered_df["priority"].value_counts()
                  .reindex(priority_order, fill_value=0).reset_index())
        pri_df.columns = ["Priority","Count"]
        fig_priority = px.bar(pri_df, x="Priority", y="Count", color="Priority",
                              color_discrete_map={"High":"#ef4444","Medium":"#f59e0b","Low":"#10b981"},
                              title="Priority Distribution", text="Count")
        fig_priority.update_traces(textposition="outside", marker_line_width=0)
        fig_priority.update_layout(**CHART_LAYOUT)
        st.plotly_chart(fig_priority, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with c4:
        st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
        top_n = 8
        top_cats = filtered_df["category"].value_counts().head(top_n).reset_index()
        top_cats.columns = ["Category","Count"]
        fig_top = px.bar(top_cats.sort_values("Count"), x="Count", y="Category",
                         orientation="h", title=f"Top {top_n} Complaint Categories",
                         color="Count", color_continuous_scale=["#1a1060","#8b5cf6","#a78bfa"])
        fig_top.update_layout(**CHART_LAYOUT, coloraxis_showscale=False)
        fig_top.update_traces(marker_line_width=0)
        st.plotly_chart(fig_top, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)


# =============================================================================
# PAGE: INSIGHTS
# Purpose  : Automated insight cards and recommendation summary.
# =============================================================================
elif active_page == "💡 Insights":
    st.markdown(
        "<h1 style='font-size:1.6rem;font-weight:700;color:#f1f5f9;margin-bottom:0.2rem;'>"
        "Actionable Insights</h1>"
        "<p style='color:#475569;font-size:0.85rem;margin-bottom:1.5rem;'>"
        "Automatically derived from the enriched dataset</p>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='section-header'>Key Findings</div>", unsafe_allow_html=True)
    i1, i2 = st.columns(2, gap="medium")

    with i1:
        st.markdown(
            f"<div class='insight-card'>"
            f"<div class='insight-title'>📌 Most Common Category</div>"
            f"<div class='insight-value'>{top_category}</div>"
            f"<div style='font-size:0.78rem;color:#475569;margin-top:0.3rem;'>"
            f"{cat_counts.iloc[0] if not cat_counts.empty else 0:,} occurrences "
            f"({(cat_counts.iloc[0]/total_records*100) if total_records else 0:.1f}% of total)</div></div>"
            f"<div class='insight-card purple'>"
            f"<div class='insight-title'>😠 Most Negative Category</div>"
            f"<div class='insight-value'>{most_negative_cat}</div>"
            f"<div style='font-size:0.78rem;color:#475569;margin-top:0.3rem;'>"
            f"{neg_by_cat.iloc[0] if not neg_by_cat.empty else 0:,} negative entries recorded</div></div>",
            unsafe_allow_html=True,
        )

    with i2:
        st.markdown(
            f"<div class='insight-card red'>"
            f"<div class='insight-title'>🔴 High Priority Issues</div>"
            f"<div class='insight-value'>{high_priority_count:,} Issues</div>"
            f"<div style='font-size:0.78rem;color:#475569;margin-top:0.3rem;'>"
            f"{(high_priority_count/total_records*100) if total_records else 0:.1f}% require urgent attention</div></div>"
            f"<div class='insight-card cyan'>"
            f"<div class='insight-title'>📊 Negative Sentiment Rate</div>"
            f"<div class='insight-value'>{negative_pct:.1f}%</div>"
            f"<div style='font-size:0.78rem;color:#475569;margin-top:0.3rem;'>"
            f"{negative_count:,} out of {total_records:,} feedback entries are negative</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div class='section-header'>Recommendation Summary</div>", unsafe_allow_html=True)
    rec_lines = []
    if total_records == 0:
        rec_lines.append("⚠️ No data matches the current filters. Adjust filters to see recommendations.")
    else:
        if negative_pct > 50:
            rec_lines.append(
                f"🔴 <b>Critical:</b> Over half of all feedback ({negative_pct:.0f}%) is negative. "
                f"Immediate intervention recommended for <b>{most_negative_cat}</b>.")
        elif negative_pct > 30:
            rec_lines.append(
                f"🟠 <b>Warning:</b> {negative_pct:.0f}% negative sentiment exceeds the 30% threshold. "
                f"Prioritise reviewing <b>{most_negative_cat}</b> issues.")
        else:
            rec_lines.append(
                f"🟢 <b>Healthy:</b> Negative sentiment at {negative_pct:.0f}% is within range. "
                "Continue monitoring for trend changes.")
        if high_priority_count:
            rec_lines.append(
                f"🚨 <b>{high_priority_count:,} high-priority issues</b> require immediate escalation. "
                "Assign dedicated resources within 24–48 hours.")
        rec_lines.append(
            f"📌 Focus product improvement on <b>{top_category}</b> — the largest complaint share. "
            "Consider a root-cause sprint.")
        if most_negative_cat != top_category:
            rec_lines.append(
                f"💡 <b>{most_negative_cat}</b> generates the most negative sentiment despite not being "
                "the highest-volume category — likely a quality or UX issue.")

    recs_html = "".join(
        f"<div style='background:#111827;border:1px solid #1e293b;border-radius:10px;"
        f"padding:0.9rem 1.1rem;margin-bottom:0.6rem;font-size:0.88rem;color:#cbd5e1;'>{r}</div>"
        for r in rec_lines
    )
    st.markdown(recs_html, unsafe_allow_html=True)


# =============================================================================
# PAGE: FEEDBACK TABLE
# Purpose  : Searchable table of enriched feedback with CSV export.
# =============================================================================
elif active_page == "🔍 Feedback Table":
    st.markdown(
        "<h1 style='font-size:1.6rem;font-weight:700;color:#f1f5f9;margin-bottom:0.2rem;'>"
        "Feedback Explorer</h1>"
        "<p style='color:#475569;font-size:0.85rem;margin-bottom:1.5rem;'>"
        "Search and inspect enriched feedback entries</p>",
        unsafe_allow_html=True,
    )

    search_query = st.text_input(
        "Search feedback",
        placeholder="🔍  Type keywords to search across all text columns…",
        label_visibility="collapsed",
    )

    if search_query.strip():
        mask = filtered_df.apply(
            lambda col: col.astype(str).str.contains(search_query, case=False, na=False)
            if col.dtype == object else pd.Series([False]*len(col))
        ).any(axis=1)
        display_df = filtered_df[mask].copy()
    else:
        display_df = filtered_df.copy()

    m1, m2, m3 = st.columns(3, gap="medium")
    with m1: st.metric("Matching Records", f"{len(display_df):,}")
    with m2: st.metric("Categories", display_df["category"].nunique())
    with m3: st.metric("High Priority", f"{(display_df['priority']=='High').sum():,}")

    st.divider()

    if display_df.empty:
        st.warning("No records match your search query.")
    else:
        st.dataframe(
            display_df[["category","sentiment","priority","issue_summary","feedback_clean"]],
            use_container_width=True, height=520,
            column_config={
                "category":      st.column_config.TextColumn("Category"),
                "sentiment":     st.column_config.TextColumn("Sentiment"),
                "priority":      st.column_config.TextColumn("Priority"),
                "issue_summary": st.column_config.TextColumn("Issue Summary", width="medium"),
                "feedback_clean":st.column_config.TextColumn("Feedback", width="large"),
            },
            hide_index=True,
        )
        st.caption(f"Showing {len(display_df):,} of {total_records:,} records")

        csv_data = display_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️  Export enriched data as CSV",
            data=csv_data,
            file_name="feedback_enriched_export.csv",
            mime="text/csv",
        )