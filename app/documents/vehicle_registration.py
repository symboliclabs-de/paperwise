from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RequiredField(str, Enum):
    """Keys for required fields that have layout hints for targeted extraction."""

    KENNZEICHEN = "kennzeichen"
    FIN = "fin"
    HALTER_NAME = "halter_name"
    ERSTZULASSUNG = "erstzulassung"
    MARKE = "marke"
    TYP = "typ"
    HSN = "hsn"
    TSN = "tsn"


class FieldAnchor(str, Enum):
    """Document field labels as printed on the Zulassungsbescheinigung Teil I."""

    A = "A"
    E = "E"
    I = "I"
    D1 = "D.1"
    D2 = "D.2"
    C11 = "C.1.1"
    HSN = "2.1"
    TSN = "2.2"


class LayoutZone(str, Enum):
    UPPER = "upper"
    UPPER_MIDDLE = "upper_middle"
    MIDDLE = "middle"
    MIDDLE_LEFT = "middle_left"
    LOWER_MIDDLE = "lower_middle"


@dataclass(frozen=True, slots=True)
class LayoutHint:
    near_labels: tuple[FieldAnchor, ...]
    zone: LayoutZone
    neighbors: tuple[RequiredField, ...] = ()
    regex: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "near_labels": [label.value for label in self.near_labels],
            "zone": self.zone.value,
        }
        if self.neighbors:
            data["neighbors"] = [neighbor.value for neighbor in self.neighbors]
        if self.regex:
            data["regex"] = self.regex
        return data


class Schema(BaseModel):
    kennzeichen: str = Field(
        description="Official license plate (field A). Pattern: 1-3 letters, 1-2 letters, 1-4 digits, e.g. 'B AB 1234'.",
    )
    fin: str = Field(
        description="Vehicle identification number (field E). Exactly 17 chars, uppercase alphanumeric, no I/O/Q.",
    )
    halter_name: str = Field(
        description="Vehicle holder name (field C.1.1). Surname or company name.",
    )
    erstzulassung: str = Field(
        description="First registration date (field I). Format: DD.MM.YYYY.",
    )
    marke: str = Field(
        description="Manufacturer / brand (field D.1), e.g. BMW, VOLKSWAGEN.",
    )
    typ: str = Field(
        description="Type / model / variant (field D.2).",
    )
    hsn: str = Field(
        description="Herstellerschlüsselnummer (field 2.1). Exactly 4 digits.",
    )
    tsn: str = Field(
        description="Typschlüsselnummer (field 2.2). Usually 3 alphanumeric chars.",
    )

    halter_vorname: str | None = Field(None, description="Holder first name (field C.1.2).")
    halter_adresse: str | None = Field(None, description="Holder address (field C.1.3).")
    hubraum: str | None = Field(None, description="Engine displacement in ccm (field P.1).")
    leistung_kw: str | None = Field(None, description="Power in kW (field P.2).")
    kraftstoff: str | None = Field(None, description="Fuel / energy source (field P.3).")
    farbe: str | None = Field(None, description="Vehicle color (field R).")
    hu_bis: str | None = Field(None, description="Next inspection due (field SP). Format: MM/YY.")


REQUIRED_FIELDS: list[str] = [
    name for name, field in Schema.model_fields.items() if field.is_required()
]

KNOWLEDGE_BASE_PATH = Path(__file__).resolve().parents[2] / "knowledge_base"

CLASSIFY_DESCRIPTION = """\
Document type key: vehicle_registration
Name: German vehicle registration certificate (Zulassungsbescheinigung Teil I)
Document is highly standardized. Use structural anchors, not keyword guessing.

Primary anchors (strong):
- A + plausible German license plate
- E + plausible VIN (17 chars, no I/O/Q)
- I + date in DD.MM.YYYY
- D.1 and D.2
- 2.1 and 2.2
- C.1.1

Secondary anchors (supporting):
- P.1 / P.2 / P.3, R, SP
- Terms: "Zulassungsbescheinigung", "Teil I", "Fahrzeugschein"

Negative indicators:
- Invoice/payment/tax language (e.g. "Rechnung", "IBAN", "USt")
- Insurance policy wording without technical vehicle field blocks
- Generic letters/contracts without field-coded sections

Classification guidance:
- classify=vehicle_registration only if at least 3 primary anchors are present
- classify=uncertain if 1-2 weak/partial anchors or OCR quality is too poor
- classify=unknown if anchors are missing or contradictory
"""

EXTRACT_ALL = """\
Extract fields from a German vehicle registration certificate (Zulassungsbescheinigung Teil I).
Exploit document structure: field label + local value, not global guesswork.

Required fields:
- kennzeichen (A)
- fin (E, 17 chars, no I/O/Q)
- halter_name (C.1.1)
- erstzulassung (I, DD.MM.YYYY)
- marke (D.1)
- typ (D.2)
- hsn (2.1, 4 digits)
- tsn (2.2, usually 3 alphanumeric chars)

Optional fields:
- halter_vorname (C.1.2)
- halter_adresse (C.1.3)
- hubraum (P.1)
- leistung_kw (P.2)
- kraftstoff (P.3)
- farbe (R)
- hu_bis (SP)

Rules:
- Return only values with explicit evidence in OCR text.
- Prefer values near matching field labels (same line or neighboring line).
- Correct OCR confusions only when context is clear:
  - 0<->O, 1<->I<->l, 8<->B, 5<->S
- Do not infer missing values from world knowledge.
"""

EXTRACT_MISSING = """\
Search specifically for missing required fields in the provided OCR text.

For each missing field:
- prioritize the canonical field label neighborhood first (A, E, I, D.1, D.2, 2.1, 2.2, C.1.1)
- apply format constraints as hard filters
- cross-check against already extracted values to avoid contradictions

OCR-focused recovery:
- consider common confusions: 0<->O, 1<->I<->l, 8<->B, 5<->S
- for VIN, enforce no I/O/Q
- for HSN, enforce exactly 4 digits
- for date, enforce DD.MM.YYYY

Output:
- found: fields recovered with high confidence
- not_found: short, concrete reason per field (e.g. "label missing", "format conflict")
"""

VALIDATE = """\
Validate extracted vehicle registration values.
Format checks (FIN length, HSN digits, date format) are handled deterministically in code.
Focus only on semantic and consistency checks:

- if both hsn and tsn exist, both must be non-empty and format-compatible
- license plate should match a plausible German format (1-3 letters, 1-2 letters, 1-4 digits)
- if a value looks like it was extracted from the wrong field, report it

Return only real violations, no speculative warnings.
"""

_LAYOUT_HINTS: dict[RequiredField, LayoutHint] = {
    RequiredField.KENNZEICHEN: LayoutHint(
        near_labels=(FieldAnchor.A,),
        zone=LayoutZone.UPPER,
    ),
    RequiredField.FIN: LayoutHint(
        near_labels=(FieldAnchor.E,),
        zone=LayoutZone.UPPER_MIDDLE,
        regex=r"[A-HJ-NPR-Z0-9]{17}",
    ),
    RequiredField.HALTER_NAME: LayoutHint(
        near_labels=(FieldAnchor.C11,),
        zone=LayoutZone.MIDDLE_LEFT,
    ),
    RequiredField.ERSTZULASSUNG: LayoutHint(
        near_labels=(FieldAnchor.I,),
        zone=LayoutZone.MIDDLE,
        regex=r"\d{2}\.\d{2}\.\d{4}",
    ),
    RequiredField.MARKE: LayoutHint(
        near_labels=(FieldAnchor.D1,),
        zone=LayoutZone.MIDDLE_LEFT,
        neighbors=(RequiredField.TYP,),
    ),
    RequiredField.TYP: LayoutHint(
        near_labels=(FieldAnchor.D2,),
        zone=LayoutZone.MIDDLE_LEFT,
        neighbors=(RequiredField.MARKE,),
    ),
    RequiredField.HSN: LayoutHint(
        near_labels=(FieldAnchor.HSN,),
        zone=LayoutZone.LOWER_MIDDLE,
        regex=r"\d{4}",
        neighbors=(RequiredField.TSN,),
    ),
    RequiredField.TSN: LayoutHint(
        near_labels=(FieldAnchor.TSN,),
        zone=LayoutZone.LOWER_MIDDLE,
        neighbors=(RequiredField.HSN,),
    ),
}

LAYOUT_HINTS: dict[str, dict[str, Any]] = {
    key.value: hint.to_dict() for key, hint in _LAYOUT_HINTS.items()
}


class VehicleRegistration:
    Schema = Schema
    REQUIRED_FIELDS = REQUIRED_FIELDS
    KNOWLEDGE_BASE_PATH = KNOWLEDGE_BASE_PATH
    CLASSIFY_DESCRIPTION = CLASSIFY_DESCRIPTION
    EXTRACT_ALL = EXTRACT_ALL
    EXTRACT_MISSING = EXTRACT_MISSING
    VALIDATE = VALIDATE
    LAYOUT_HINTS = LAYOUT_HINTS
