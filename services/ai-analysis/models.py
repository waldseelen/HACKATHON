"""
Pydantic models shared across the AI Analysis service (v2).
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class ParsedLog(BaseModel):
    """A single parsed log received from the ingestion service via RabbitMQ."""
    log_id: int
    timestamp: str
    severity: str
    service: str
    container: str
    raw_log: str
    fingerprint: Optional[str] = None
    ingested_at: Optional[str] = None


class AnalysisResult(BaseModel):
    """Output returned by AI analysis (v2 schema)."""
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
        description="Confidence score 0.0-1.0",
    )
    summary: str = Field(
        default="",
        description="Short summary of the issue (max 180 chars)",
    )
    root_cause: str = Field(
        default="",
        description="Explanation of WHY this error happened",
    )
    solution: str = Field(
        default="",
        description="Actionable fix: newline-separated action items",
    )
    action_required: bool = Field(
        default=True,
        description="Whether human intervention is needed",
    )
    # v2 fields
    title: str = Field(default="", description="Alert title (<= 80 chars)")
    dedupe_key: str = Field(default="", description="Deduplication key")
    impact: str = Field(default="", description="Impact description (<= 240 chars)")
    verification_steps: List[str] = Field(default_factory=list)
    follow_up_questions: List[str] = Field(default_factory=list)
    context_for_chat: str = Field(default="")
    code_level_hints: List[str] = Field(default_factory=list)
    detected_signals: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
