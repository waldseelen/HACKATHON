"""
Pydantic models shared across the AI Analysis service.
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
    """Output returned by Gemini AI analysis."""
    category: str = Field(
        ...,
        description="Error category: database|network|auth|crash|performance|security|config|other",
    )
    severity: str = Field(
        ...,
        description="Severity: critical|high|medium|low",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score 0.0-1.0",
    )
    summary: str = Field(
        ...,
        description="Short one-line summary of the issue",
    )
    root_cause: str = Field(
        ...,
        description="Explanation of WHY this error happened",
    )
    solution: str = Field(
        ...,
        description="Actionable fix: immediate + long-term recommendation",
    )
    action_required: bool = Field(
        default=True,
        description="Whether human intervention is needed",
    )
