"""
LogSense AI – Pydantic Models (v2)
====================================
Request/response models for the API.
Includes new enriched AnalysisResult with chat and diagnostics payloads.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


# ── Request Models ────────────────────────────────────────

class LogEntry(BaseModel):
    log: str
    source: str = "api"
    container: str = "unknown"
    timestamp: Optional[str] = None


class LogBatchRequest(BaseModel):
    logs: list[LogEntry]


class TokenRegistration(BaseModel):
    token: str
    device_name: str = "unknown"
    platform: str = "expo"


class ChatRequest(BaseModel):
    """Mobil chat isteği."""
    alert_id: str = Field(..., description="Sohbet bağlamı olan alert ID")
    message: str = Field(..., description="Kullanıcı mesajı")
    history: Optional[list[dict]] = Field(
        default=None,
        description="Önceki sohbet geçmişi [{role, content}, ...]"
    )
    system_prompt: Optional[str] = Field(
        default=None,
        description="Kullanıcı tanımlı system prompt"
    )


class LoginRequest(BaseModel):
    """Basit kullanıcı giriş isteği."""
    username: str
    password: str


# ── Response Models ───────────────────────────────────────

class IngestResponse(BaseModel):
    status: str
    log_id: Optional[str] = None
    stored: bool = False


class HealthResponse(BaseModel):
    status: str
    service: str
    storage: bool
    ai: bool
    pending_logs: int = 0
    ai_gateway: Optional[dict] = None


class ChatResponse(BaseModel):
    """Chat yanıtı."""
    reply: str
    alert_id: str


class LoginResponse(BaseModel):
    """Login yanıtı."""
    status: str
    token: str = ""
    username: str = ""
    message: str = ""


# ── AI Analysis Result (v2 – enriched) ───────────────────

class AnalysisResult(BaseModel):
    # Temel alanlar (v1 uyumluluğu)
    category: str = Field(
        default="unknown",
        description="Database|Network|Auth|Performance|API|Infra|Build|Mobile|Unknown",
    )
    severity: str = Field(
        default="medium",
        description="critical|high|medium|low",
    )
    confidence: float = Field(
        default=0.5, ge=0.0, le=1.0,
    )
    summary: str = Field(
        default="",
        description="One-sentence summary (max 180 chars)",
    )
    root_cause: str = Field(
        default="",
        description="Likely root cause (max 300 chars)",
    )
    solution: str = Field(
        default="",
        description="Recommended actions (newline-separated)",
    )
    action_required: bool = Field(
        default=True,
        description="Whether human intervention is needed",
    )

    # Yeni alanlar (v2)
    title: str = Field(
        default="",
        description="Alert title (<= 80 chars)",
    )
    dedupe_key: str = Field(
        default="",
        description="Deduplication key for grouping same issues",
    )
    impact: str = Field(
        default="",
        description="Impact description (<= 240 chars)",
    )
    verification_steps: List[str] = Field(
        default_factory=list,
        description="Steps to verify the fix (1-3 items)",
    )
    follow_up_questions: List[str] = Field(
        default_factory=list,
        description="Suggested follow-up questions for chat (max 5)",
    )
    context_for_chat: str = Field(
        default="",
        description="Context summary for chat assistant",
    )
    code_level_hints: List[str] = Field(
        default_factory=list,
        description="File/layer/component level hints",
    )
    detected_signals: List[str] = Field(
        default_factory=list,
        description="Detected signals (e.g., rate_limit, db_timeout)",
    )
    assumptions: List[str] = Field(
        default_factory=list,
        description="Assumptions made during analysis",
    )
    # Cascade / Runbook fields (v3)
    is_cascade: bool = Field(
        default=False,
        description="Whether this alert is part of a cascade failure",
    )
    cascade_type: Optional[str] = Field(
        default=None,
        description="Type of cascade failure detected",
    )
    runbook_id: Optional[str] = Field(
        default=None,
        description="Associated recovery runbook ID",
    )
    recommended_actions: List[str] = Field(
        default_factory=list,
        description="Ordered recovery actions (from runbook or AI)",
    )
