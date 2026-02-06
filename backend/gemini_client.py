"""
LogSense AI – Gemini AI Client
================================
Structured log analysis with Google Gemini 2.0 Flash.
"""

import json
import logging
import re
from typing import Optional

import google.generativeai as genai  # type: ignore[import-untyped]
from google.api_core import exceptions as google_exceptions  # type: ignore[import-untyped]
from tenacity import (  # type: ignore[import-untyped]
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    wait_fixed,
)

from models import AnalysisResult

logger = logging.getLogger("logsense.gemini")

ANALYSIS_PROMPT = """\
You are an expert Site Reliability Engineer (SRE) analyzing production container logs.

Analyze the following {count} error/warning log(s) and provide:

1. **category**: One of: database | network | auth | crash | performance | security | config | other
2. **severity**: One of: critical | high | medium | low
3. **confidence**: Float 0.0–1.0
4. **summary**: One-line summary (max 120 chars)
5. **root_cause**: WHY this error happened (2-3 sentences)
6. **solution**: Actionable fix — immediate workaround + long-term fix
7. **action_required**: Boolean — does a human need to intervene?

LOGS:
{logs}

Respond with ONLY valid JSON:
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


class GeminiClient:
    """Google Gemini AI wrapper for log analysis."""

    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        self._ready = False
        if not api_key:
            logger.warning("No Gemini API key — AI analysis disabled")
            return

        genai.configure(api_key=api_key)  # type: ignore[attr-defined]
        self._model = genai.GenerativeModel(model_name)  # type: ignore[attr-defined]
        self._ready = True
        logger.info(f"Gemini initialized: {model_name}")

    @property
    def is_ready(self) -> bool:
        return self._ready

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_fixed(30),  # Wait 30s for rate limit
        retry=retry_if_exception_type((Exception,)),
        before_sleep=lambda rs: logger.warning(
            f"Gemini retry #{rs.attempt_number} - waiting 30s for rate limit"
        ),
    )
    async def analyze(self, logs_text: str, count: int = 1) -> AnalysisResult:
        """Analyze log(s) with Gemini AI and return structured result."""
        if not self._ready:
            return self._fallback(logs_text)

        prompt = ANALYSIS_PROMPT.format(logs=logs_text, count=count)

        response = await self._model.generate_content_async(
            prompt,
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.1,
                "max_output_tokens": 512,
            },
        )

        raw = response.text.strip()
        logger.debug(f"Gemini response: {raw[:200]}")

        data = self._parse_json(raw)
        return AnalysisResult(**data)

    def _parse_json(self, text: str) -> dict:
        """Parse JSON from Gemini response, handling markdown wrapping."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                return json.loads(match.group())
            raise ValueError(f"Cannot parse Gemini response: {text[:200]}")

    def _fallback(self, logs_text: str) -> AnalysisResult:
        """Fallback analysis when Gemini is unavailable."""
        severity = "high"
        category = "other"

        text_lower = logs_text.lower()
        if any(w in text_lower for w in ("database", "sql", "postgres", "mysql", "connection pool")):
            category = "database"
        elif any(w in text_lower for w in ("timeout", "connection refused", "dns", "http 5")):
            category = "network"
        elif any(w in text_lower for w in ("auth", "jwt", "token", "login", "oauth")):
            category = "auth"
        elif any(w in text_lower for w in ("oom", "memory", "heap", "segfault", "killed")):
            category = "crash"
            severity = "critical"
        elif any(w in text_lower for w in ("cpu", "slow", "latency", "blocked")):
            category = "performance"
        elif any(w in text_lower for w in ("injection", "rate limit", "security")):
            category = "security"

        if any(w in text_lower for w in ("fatal", "critical", "killed", "oom")):
            severity = "critical"

        return AnalysisResult(
            category=category,
            severity=severity,
            confidence=0.3,
            summary=logs_text[:120].strip(),
            root_cause="Automated fallback — Gemini API unavailable.",
            solution="Check Gemini API key and quota. Review logs manually.",
            action_required=True,
        )
