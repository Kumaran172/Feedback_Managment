"""
ai_analyzer.py
--------------
Gemini API enrichment layer.
"""

from __future__ import annotations

import time
import textwrap
from typing import Optional

import google.generativeai as genai

# Model name — change here if upgrading
GEMINI_MODEL: str = "gemini-2.5-flash"

# Maximum characters of feedback_text to send to Gemini (cost control)
MAX_FEEDBACK_CHARS: int = 800

EXPLAIN_PROMPT_TEMPLATE = textwrap.dedent(
    """
    You are a customer feedback analyst. Explain the customer feedback below.

    Feedback:
    \"\"\"{feedback}\"\"\"

    Provide the analysis under these exact headers:
    - Customer Intent: <explanation of customer intent>
    - Main Issue: <explanation of main issue>
    - Business Impact: <explanation of business impact>

    Keep the entire response clear, concise, and under 100 words.
    """
).strip()

RESOLVE_PROMPT_TEMPLATE = textwrap.dedent(
    """
    You are a customer feedback analyst. Suggest a resolution for the customer feedback below.

    Feedback:
    \"\"\"{feedback}\"\"\"

    Provide the resolution under these exact headers:
    - Root Cause: <explanation of likely root cause>
    - Suggested Fix: <explanation of suggested fix>
    - Prevention Strategy: <explanation of prevention strategy>

    Keep the entire response clear, concise, and under 120 words.
    """
).strip()


class AIAnalyzer:
    """
    On-demand AI analyzer for individual feedback rows.
    """

    def __init__(self, api_key: str) -> None:
        """
        Parameters
        ----------
        api_key : str
            Gemini API key.
        """
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(GEMINI_MODEL)

    def explain_feedback(self, feedback_text: str) -> str:
        """
        Call Gemini to explain a single feedback text.
        Response is under 100 words explaining Customer Intent, Main Issue, and Business Impact.
        """
        prompt = EXPLAIN_PROMPT_TEMPLATE.format(feedback=feedback_text[:MAX_FEEDBACK_CHARS])
        return self._call_gemini_row_safe(prompt, fallback="Unable to generate explanation.")

    def suggest_resolution(self, feedback_text: str) -> str:
        """
        Call Gemini to suggest a resolution for a single feedback text.
        Response is under 120 words explaining Root Cause, Suggested Fix, and Prevention Strategy.
        """
        prompt = RESOLVE_PROMPT_TEMPLATE.format(feedback=feedback_text[:MAX_FEEDBACK_CHARS])
        return self._call_gemini_row_safe(prompt, fallback="Unable to generate resolution suggestions.")

    def _call_gemini_row_safe(self, prompt: str, fallback: str) -> str:
        """
        Helper to call Gemini with a single prompt. Retry once on failure.
        """
        try:
            response = self._model.generate_content(prompt)
            return response.text.strip()
        except Exception as exc1:
            time.sleep(1.0)
            try:
                response = self._model.generate_content(prompt)
                return response.text.strip()
            except Exception as exc2:
                return f"{fallback}\n\n(Error: {exc2})"
