"""
LogSense AI – OpenRouter AI Client (v2)
=========================================
Structured log analysis with incident categorization, root-cause
hypotheses, deduplication key generation, and chat-ready payloads.

Key improvements over v1:
  • Retry: 5 attempts with 5-60 s exponential back-off (rate-limit safe).
  • Empty/null choices detection + explicit rate_limit signal tracking.
  • New output schema: mobile_alert + chat_assistant_payload + diagnostics.
  • Fallback still tries best-effort heuristic analysis.
"""

import json
import logging
import re
import hashlib
from typing import Optional, List

from openai import AsyncOpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from models import AnalysisResult

logger = logging.getLogger("logsense.openrouter")


# ── System Prompt ─────────────────────────────────────────

SYSTEM_PROMPT = """\
Sen, geliştiriciler için incident/log analizi yapan bir AI asistansın.
Görevin: gelen log özetini doğru kategorize etmek, kök neden hipotezleri üretmek,
etkisini ve aciliyetini (severity) belirlemek, kısa ve uygulanabilir aksiyonlar önermek,
tekilleştirme için bir dedupe_key üretmek ve kullanıcı mobil sohbetinde sorulabilecek
takip sorularını hazırlamaktır.

Yanıtın her zaman kısa, teknik, uygulanabilir ve mobil ekranda okunabilir olmalı.
Gereksiz uzun açıklamalardan kaçın.  PII (email, telefon, token, parola) görürsen maskele.
Yanıtı yalnızca JSON olarak döndür — ek açıklama metni YAZMA.
"""

ANALYSIS_PROMPT = """\
Aşağıdaki {count} adet ERROR/WARN/FATAL log kaydını analiz et.

## Kurallar
1. Hızlı sınıflandır: category ∈ {{Database,Network,Auth,Performance,API,Infra,Build,Mobile,Unknown}}.
2. severity belirle: P0 (kritik, prod down/veri kaybı), P1 (yüksek), P2 (orta), P3 (düşük).
3. Root-cause: 1 ana hipotez + en fazla 2 alternatif; her hipoteze log kanıtı ekle.
4. Aksiyonları sıralı ver: 1) hızlı mitigasyon 2) kalıcı düzeltme 3) doğrulama adımı.
5. dedupe_key üret: category + hata_tipi + ana_endpoint + mesaj_özeti (kısa).
6. Mobil sohbet için max 5 takip sorusu öner.
7. Max 2200 karakter toplam çıktı.

## AI Gateway Durumu
provider: openrouter | model: {model} | son_durum: {gateway_status}

## Loglar
{logs}

## Beklenen JSON (TEK obje, markdown yok)
{{
  "mobile_alert": {{
    "title": "<= 80 karakter",
    "category": "Database|Network|Auth|Performance|API|Infra|Build|Mobile|Unknown",
    "severity": "P0|P1|P2|P3",
    "confidence": 0.85,
    "dedupe_key": "string",
    "one_sentence_summary": "<= 180 karakter",
    "impact": "<= 240 karakter",
    "likely_root_cause": "<= 300 karakter",
    "recommended_actions": ["adım 1", "adım 2", "adım 3"],
    "verification_steps": ["doğrulama 1"],
    "needs_human_review": true
  }},
  "chat_assistant_payload": {{
    "context_for_chat": "kısa teknik özet",
    "follow_up_questions": ["soru 1", "soru 2"],
    "code_level_hints": ["dosya/katman ipucu"]
  }},
  "diagnostics": {{
    "detected_signals": ["db_timeout", "rate_limit"],
    "assumptions": ["Varsayım: ..."],
    "what_would_change_my_mind": ["ek veri gelirse ..."]
  }}
}}
"""

CHAT_SYSTEM_PROMPT = """\
Sen LogSense AI chatbot'usun. Kullanıcı bir alert bağlamında soru soruyor.
Kısa, teknik, uygulanabilir yanıtlar ver.  Mobil ekranda okunacak — paragrafları kısa tut.
Kod bloğu veya komut önerisi gerekiyorsa ekle. PII maskelemeye dikkat et.
"""


# ── Özel exception sınıfları ─────────────────────────────

class EmptyChoicesError(Exception):
    """OpenRouter boş choices döndüğünde fırlatılır."""
    pass


class RateLimitError(Exception):
    """429 veya rate-limit benzeri sinyal alındığında."""
    pass


# ── Client ────────────────────────────────────────────────

class OpenRouterClient:
    """OpenRouter AI wrapper — geliştirilmiş retry ve yeni output schema."""

    def __init__(self, api_key: str, model_name: str = "deepseek/deepseek-r1-0528:free"):
        self._ready = False
        self._last_status = "init"
        self._retry_count_used = 0
        self._rate_limit_signals: List[str] = []

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

    @property
    def gateway_health(self) -> dict:
        return {
            "provider": "openrouter",
            "model": self._model if self._ready else "none",
            "last_call_status": self._last_status,
            "retry_count_used": self._retry_count_used,
            "rate_limit_signals": list(self._rate_limit_signals[-10:]),
        }

    # ── Ana analiz ────────────────────────────────────────

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=5, max=60),
        retry=retry_if_exception_type((EmptyChoicesError, RateLimitError, ConnectionError, TimeoutError)),
        before_sleep=lambda rs: logger.warning(
            f"OpenRouter retry #{rs.attempt_number} — bekliyor…"
        ),
    )
    async def analyze(self, logs_text: str, count: int = 1) -> AnalysisResult:
        """Analyze log(s) and return the new structured AnalysisResult."""
        if not self._ready:
            return self._fallback(logs_text)

        prompt = ANALYSIS_PROMPT.format(
            logs=logs_text,
            count=count,
            model=self._model,
            gateway_status=self._last_status,
        )

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=2200,
            )

            # ── Boş choices koruması ─────────────────────
            if not response.choices:
                self._last_status = "empty_response"
                self._rate_limit_signals.append("empty_choices")
                raise EmptyChoicesError("response.choices is empty/null")

            content = response.choices[0].message.content
            if not content or not content.strip():
                self._last_status = "empty_response"
                self._rate_limit_signals.append("empty_content")
                raise EmptyChoicesError("response content is empty")

            raw = content.strip()
            logger.debug(f"OpenRouter raw ({len(raw)} chars)")

            data = self._parse_json(raw)
            self._last_status = "success"
            self._retry_count_used = 0

            return self._map_to_result(data, logs_text)

        except (EmptyChoicesError, RateLimitError):
            self._retry_count_used += 1
            raise
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "rate" in err_str:
                self._last_status = "rate_limited"
                self._rate_limit_signals.append("429")
                self._retry_count_used += 1
                raise RateLimitError(str(e))
            self._last_status = "fail"
            logger.error(f"OpenRouter analysis failed: {e}", exc_info=True)
            raise

    # ── Chat ──────────────────────────────────────────────

    async def chat(self, alert_context: str, user_message: str, history: list[dict] | None = None, system_prompt: str | None = None) -> str:
        """
        Kullanıcının bir alert hakkında sohbet etmesini sağlar.
        Kısa, teknik, uygulanabilir yanıtlar döndürür.
        """
        if not self._ready:
            return "AI servisi şu anda kullanılamıyor. Lütfen daha sonra tekrar deneyin."

        # Kullanıcı özel system prompt verdiyse onu kullan, yoksa varsayılan
        effective_prompt = system_prompt if system_prompt else CHAT_SYSTEM_PROMPT
        messages = [
            {"role": "system", "content": effective_prompt},
            {"role": "user", "content": f"[Alert Bağlamı]\n{alert_context}"},
        ]

        if history:
            for msg in history[-10:]:  # Son 10 mesaj
                messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

        messages.append({"role": "user", "content": user_message})

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0.3,
                max_tokens=1024,
            )

            if not response.choices or not response.choices[0].message.content:
                return "AI yanıt üretemedi. Rate limit olabilir — biraz sonra tekrar deneyin."

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Chat failed: {e}")
            return f"Chat hatası: Lütfen tekrar deneyin."

    # ── Yardımcılar ───────────────────────────────────────

    def _map_to_result(self, data: dict, logs_text: str) -> AnalysisResult:
        """Yeni JSON formatını AnalysisResult'a eşle."""
        ma = data.get("mobile_alert", data)
        chat_pl = data.get("chat_assistant_payload", {})
        diag = data.get("diagnostics", {})

        # Severity mapping: P0→critical, P1→high, P2→medium, P3→low
        sev_map = {"P0": "critical", "P1": "high", "P2": "medium", "P3": "low"}
        raw_sev = ma.get("severity", "P2")
        severity = sev_map.get(raw_sev, raw_sev)

        # Category mapping (büyük harfle gelebilir)
        category = (ma.get("category", "Unknown") or "Unknown").lower()

        return AnalysisResult(
            category=category,
            severity=severity,
            confidence=float(ma.get("confidence", 0.5)),
            summary=ma.get("one_sentence_summary", ma.get("title", logs_text[:120]))[:180],
            root_cause=ma.get("likely_root_cause", "")[:500],
            solution="\n".join(ma.get("recommended_actions", [])),
            action_required=ma.get("needs_human_review", True),
            # Yeni alanlar
            title=ma.get("title", "")[:80],
            dedupe_key=ma.get("dedupe_key", ""),
            impact=ma.get("impact", "")[:240],
            verification_steps=ma.get("verification_steps", []),
            follow_up_questions=chat_pl.get("follow_up_questions", []),
            context_for_chat=chat_pl.get("context_for_chat", ""),
            code_level_hints=chat_pl.get("code_level_hints", []),
            detected_signals=diag.get("detected_signals", []),
            assumptions=diag.get("assumptions", []),
        )

    def _parse_json(self, text: str) -> dict:
        """Parse JSON from response, handling markdown wrapping and think blocks."""
        # DeepSeek R1 bazen <think>...</think> bloğu döndürür — çıkar
        text = re.sub(r"<think>[\s\S]*?</think>", "", text).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Markdown code block içinden çıkar
            match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
            if match:
                return json.loads(match.group(1))

            # Herhangi bir JSON objesi bul
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                return json.loads(match.group())

            raise ValueError(f"Cannot parse OpenRouter response: {text[:200]}")

    def _fallback(self, logs_text: str) -> AnalysisResult:
        """Fallback analysis when AI is unavailable."""
        severity = "high"
        category = "unknown"

        text_lower = logs_text.lower()
        if any(w in text_lower for w in ("database", "sql", "postgres", "mysql", "connection pool", "db")):
            category = "database"
        elif any(w in text_lower for w in ("timeout", "connection refused", "dns", "http 5", "socket")):
            category = "network"
        elif any(w in text_lower for w in ("auth", "jwt", "token", "login", "oauth", "401", "403")):
            category = "auth"
        elif any(w in text_lower for w in ("oom", "memory", "heap", "segfault", "killed")):
            category = "infra"
            severity = "critical"
        elif any(w in text_lower for w in ("cpu", "slow", "latency", "blocked", "p99")):
            category = "performance"
        elif any(w in text_lower for w in ("api", "endpoint", "request", "response", "http")):
            category = "api"
        elif any(w in text_lower for w in ("build", "compile", "deploy", "ci", "cd")):
            category = "build"

        if any(w in text_lower for w in ("fatal", "critical", "killed", "oom", "down")):
            severity = "critical"

        # Basit dedupe key
        fp = hashlib.sha256(logs_text[:200].encode()).hexdigest()[:8]
        dedupe_key = f"{category}:{fp}"

        return AnalysisResult(
            category=category,
            severity=severity,
            confidence=0.25,
            summary=logs_text[:180].strip(),
            root_cause="AI API erişilemedi — otomatik fallback analizi.",
            solution="1. OpenRouter API key ve bağlantıyı kontrol et.\n2. Logları manuel incele.\n3. Rate limit geçince tekrar analiz et.",
            action_required=True,
            title=f"[Fallback] {category.upper()} hatası",
            dedupe_key=dedupe_key,
            impact="AI analizi üretilemedi; manuel inceleme gerekebilir.",
            verification_steps=["API key doğrula", "Bağlantıyı test et"],
            follow_up_questions=[
                "Son deploy ne zaman yapıldı?",
                "Hangi servis/endpoint etkileniyor?",
                "Bu hata daha önce görüldü mü?",
            ],
            context_for_chat=f"Fallback analiz: {category} kategorisinde {severity} seviyeli hata tespit edildi.",
            code_level_hints=[],
            detected_signals=["ai_fallback", self._last_status],
            assumptions=["Varsayım: AI API rate limit veya bağlantı sorunu."],
        )
