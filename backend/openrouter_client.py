"""
LogSense AI – OpenRouter AI Client
====================================
Structured log analysis with DeepSeek R1 via OpenRouter.
"""

import json
import logging
import re
from typing import Optional

from openai import AsyncOpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from models import AnalysisResult

logger = logging.getLogger("logsense.openrouter")

ANALYSIS_PROMPT = """\
You are an expert Site Reliability Engineer (SRE) analyzing production container logs.

Analyze the following {count} error/warning log(s) and provide a SINGLE, UNIFIED analysis that summarizes all logs together:

1. **category**: Primary category (database | network | auth | crash | performance | security | config | other)
2. **severity**: Overall severity (critical | high | medium | low)
3. **confidence**: Float 0.0–1.0
4. **summary**: One-line summary covering all logs (max 120 chars)
5. **root_cause**: Unified root cause analysis (2-3 sentences)
6. **solution**: Actionable fix — immediate workaround + long-term fix
7. **action_required**: Boolean — does a human need to intervene?

LOGS:
{logs}

IMPORTANT: Respond with ONLY a SINGLE JSON object (not an array), no markdown, no extra text:
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


class OpenRouterClient:
    """OpenRouter AI wrapper for log analysis with DeepSeek R1."""

    def __init__(self, api_key: str, model_name: str = "deepseek/deepseek-r1-0528:free"):
        self._ready = False
        if not api_key:
            logger.warning("No OpenRouter API key — AI analysis disabled")
            return

        self._client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        self._model = model_name
        self._ready = True
        logger.info(f"OpenRouter initialized: {model_name}")

    @property
    def is_ready(self) -> bool:
        return self._ready

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        before_sleep=lambda rs: logger.warning(
            f"OpenRouter retry #{rs.attempt_number}"
        ),
    )
    async def analyze(self, logs_text: str, count: int = 1) -> AnalysisResult:
        """Analyze log(s) with DeepSeek R1 and return structured result."""
        if not self._ready:
            return self._fallback(logs_text)

        prompt = ANALYSIS_PROMPT.format(logs=logs_text, count=count)

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert SRE. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=2048,
            )

            raw = response.choices[0].message.content.strip()
            logger.debug(f"OpenRouter raw response: {raw}")

            data = self._parse_json(raw)
            return AnalysisResult(**data)

        except Exception as e:
            logger.error(f"OpenRouter analysis failed: {e}", exc_info=True)
            raise

    def _parse_json(self, text: str) -> dict:
        """Parse JSON from response, handling markdown wrapping."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
            if match:
                return json.loads(match.group(1))

            # Try to find any JSON object
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                return json.loads(match.group())

            raise ValueError(f"Cannot parse OpenRouter response: {text[:200]}")

    def _fallback(self, logs_text: str) -> AnalysisResult:
        """Fallback analysis when AI is unavailable."""
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
            root_cause="Automated fallback — AI API unavailable.",
            solution="Check OpenRouter API key and network. Review logs manually.",
            action_required=True,
        )
