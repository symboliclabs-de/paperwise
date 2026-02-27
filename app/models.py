import uuid
from datetime import datetime, UTC
from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


@dataclass
class OCRResult:
    text: str
    pages: int = 1


class DocumentStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    FLAGGED = "flagged"


class DocumentType(str, Enum):
    VEHICLE_REGISTRATION = "vehicle_registration"
    UNKNOWN = "unknown"
    UNCERTAIN = "uncertain"


class Result(BaseModel):
    document_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: DocumentStatus
    classification: DocumentType
    confidence: float
    extracted: dict[str, Any] | None = None
    failed_fields: dict[str, str] = Field(default_factory=dict)
    validation_errors: list[str] = Field(default_factory=list)
    flagged_reason: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
