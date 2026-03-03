from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel

from app.documents.vehicle_registration import VehicleRegistration


class Document(Protocol):
    Schema: type[BaseModel]
    REQUIRED_FIELDS: list[str]
    KNOWLEDGE_BASE_PATH: Path
    CLASSIFY_DESCRIPTION: str
    EXTRACT_ALL: str
    EXTRACT_MISSING: str
    VALIDATE: str
    LAYOUT_HINTS: dict[str, dict[str, Any]]


SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "image/tiff",
}

TYPES: dict[str, Document] = {
    "vehicle_registration": VehicleRegistration(),
}
