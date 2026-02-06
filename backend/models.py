"""
LogSense AI – Pydantic Models
==============================
Request/response models for the API.
"""

from typing import Optional
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


# ── Response Models ───────────────────────────────────────

class IngestResponse(BaseModel):
    status: str
    log_id: Optional[str] = None
    stored: bool = False


class HealthResponse(BaseModel):
    status: str
    service: str
    firebase: bool
    ai: bool
    pending_logs: int = 0


# ── AI Analysis Result ───────────────────────────────────

class AnalysisResult(BaseModel):
    category: str = Field(
        ...,
        description="database|network|auth|crash|performance|security|config|other",
    )
    severity: str = Field(
        ...,
        description="critical|high|medium|low",
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0,
    )
    summary: str = Field(
        ...,
        description="One-line summary (max 120 chars)",
    )
    root_cause: str = Field(
        ...,
        description="Why this error happened",
    )
    solution: str = Field(
        ...,
        description="Actionable fix (immediate + long-term)",
    )
    action_required: bool = Field(
        default=True,
        description="Whether human intervention is needed",
    )
