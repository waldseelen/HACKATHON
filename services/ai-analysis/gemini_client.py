"""
Gemini AI Client – log analysis with structured JSON output.
"""

import json
import logging
from typing import Dict, Any

import google.generativeai as genai
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from models import AnalysisResult

logger = logging.getLogger("ai-analysis.gemini")

# ── Prompt template ───────────────────────────────────────

ANALYSIS_PROMPT = """\
You are an expert Site Reliability Engineer (SRE) analyzing production container logs.

Analyze the following {count} error/warning log(s) from service(s) and provide:

1. **category**: One of: database | network | auth | crash | performance | security | config | other
2. **severity**: One of: critical | high | medium | low
3. **confidence**: Float 0.0–1.0 indicating how certain you are
4. **summary**: One-line summary (max 120 chars)
5. **root_cause**: Clear explanation of WHY this error happened (2-3 sentences)
6. **solution**: Actionable fix — include BOTH an immediate workaround and a long-term fix
7. **action_required**: Boolean — does a human need to intervene?

LOGS:
{logs}

Respond with ONLY valid JSON matching this schema exactly:
{{
  "category": "...",
  "severity": "...",
  "confidence": 0.85,
  "summary": "...",
  "root_cause": "...",
  "solution": "...",
  "action_required": true
}}
"""


class GeminiAnalyzer:
    """Wrapper around Google Gemini 2.0 Flash for log analysis."""

    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        genai.configure(api_key=api_key)
        self.model_name = model_name
        self._model = genai.GenerativeModel(model_name)
        self.system_instruction = (
            "You are a senior SRE and DevOps expert. "
            "Analyze container logs concisely. "
            "Always respond with valid JSON only — no markdown, no explanation."
        )
        logger.info(f"Gemini model initialized: {model_name}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        retry=retry_if_exception_type((Exception,)),
        before_sleep=lambda rs: logger.warning(
            f"Gemini retry #{rs.attempt_number} after error: {rs.outcome.exception()}"
        ),
    )
    async def analyze(self, logs_text: str, count: int) -> AnalysisResult:
        """Send logs to Gemini and return structured analysis."""
        prompt = ANALYSIS_PROMPT.format(logs=logs_text, count=count)

        response = await self._model.generate_content_async(
            prompt,
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.1,
                "max_output_tokens": 512,
            },
        )

        raw_text = response.text.strip()
        logger.debug(f"Gemini raw response: {raw_text[:300]}")

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code block
            import re
            match = re.search(r"\{[\s\S]*\}", raw_text)
            if match:
                data = json.loads(match.group())
            else:
                raise ValueError(f"Gemini returned non-JSON: {raw_text[:200]}")

        return AnalysisResult(**data)

    def fallback_analysis(self, logs_text: str) -> AnalysisResult:
        """Simple rule-based fallback when Gemini is unavailable."""
        lower = logs_text.lower()

        if any(w in lower for w in ("database", "sql", "deadlock", "postgres", "mysql")):
            cat = "database"
        elif any(w in lower for w in ("timeout", "connection", "refused", "dns")):
            cat = "network"
        elif any(w in lower for w in ("memory", "oom", "heap")):
            cat = "crash"
        elif any(w in lower for w in ("auth", "token", "forbidden", "unauthorized")):
            cat = "auth"
        elif any(w in lower for w in ("slow", "latency", "cpu")):
            cat = "performance"
        else:
            cat = "other"

        return AnalysisResult(
            category=cat,
            severity="high",
            confidence=0.3,
            summary="Fallback analysis (AI unavailable)",
            root_cause="Automated analysis could not be performed — review logs manually.",
            solution="Check the raw log entries and investigate the affected service.",
            action_required=True,
        )
