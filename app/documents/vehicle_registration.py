from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class FieldKey(str, Enum):
    KENNZEICHEN = "kennzeichen"
    FIN = "fin"
    HALTER_NAME = "halter_name"
    ERSTZULASSUNG = "erstzulassung"
    MARKE = "marke"
    TYP = "typ"
    HSN = "hsn"
    TSN = "tsn"
    HALTER_VORNAME = "halter_vorname"
    HALTER_ADRESSE = "halter_adresse"
    HUBRAUM = "hubraum"
    LEISTUNG_KW = "leistung_kw"
    KRAFTSTOFF = "kraftstoff"
    FARBE = "farbe"
    HU_BIS = "hu_bis"


class FieldAnchor(str, Enum):
    A = "A"
    E = "E"
    I = "I"
    D1 = "D.1"
    D2 = "D.2"
    C11 = "C.1.1"
    C12 = "C.1.2"
    C13 = "C.1.3"
    P1 = "P.1"
    P2 = "P.2"
    P3 = "P.3"
    R = "R"
    SP = "SP"
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
    neighbors: tuple[FieldKey, ...] = ()
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
    kennzeichen: str = Field(description="Amtliches Kennzeichen (Feld A)")
    fin: str = Field(description="Fahrzeug-Identifizierungsnummer, 17-stellig (Feld E)")
    halter_name: str = Field(description="Name des Fahrzeughalters (Feld C.1.1)")
    erstzulassung: str = Field(description="Datum der Erstzulassung TT.MM.JJJJ (Feld I)")
    marke: str = Field(description="Marke / Hersteller (Feld D.1)")
    typ: str = Field(description="Typ / Modell (Feld D.2)")
    hsn: str = Field(description="Herstellerschlüsselnummer, 4-stellig (Feld 2.1)")
    tsn: str = Field(description="Typschlüsselnummer, 3-stellig (Feld 2.2)")

    halter_vorname: str | None = Field(None, description="Vorname des Halters (Feld C.1.2)")
    halter_adresse: str | None = Field(None, description="Anschrift des Halters (Feld C.1.3)")
    hubraum: str | None = Field(None, description="Hubraum in ccm (Feld P.1)")
    leistung_kw: str | None = Field(None, description="Leistung in kW (Feld P.2)")
    kraftstoff: str | None = Field(None, description="Kraftstoff / Energiequelle (Feld P.3)")
    farbe: str | None = Field(None, description="Farbe des Fahrzeugs (Feld R)")
    hu_bis: str | None = Field(None, description="Nächste HU fällig MM/JJ (Feld SP)")


REQUIRED_FIELDS: list[str] = [
    FieldKey.KENNZEICHEN.value,
    FieldKey.FIN.value,
    FieldKey.HALTER_NAME.value,
    FieldKey.ERSTZULASSUNG.value,
    FieldKey.MARKE.value,
    FieldKey.TYP.value,
    FieldKey.HSN.value,
    FieldKey.TSN.value,
]

KNOWLEDGE_BASE_DIR = Path(__file__).resolve().parents[2] / "knowledge_base"

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
Return only real violations, no speculative warnings.

Hard checks:
- fin: exactly 17 chars, uppercase alphanumeric, no I/O/Q
- hsn: exactly 4 digits
- erstzulassung: valid DD.MM.YYYY date

Consistency checks:
- if both hsn and tsn exist, both must be non-empty and format-compatible
- if field label/value mapping is ambiguous, report as validation error
"""

FIELD_HINTS_BY_KEY: dict[FieldKey, str] = {
    FieldKey.KENNZEICHEN: (
        "Field A. German plate pattern like 'B AB 1234'. "
        "Prioritize top section and label proximity."
    ),
    FieldKey.FIN: (
        "Field E. VIN with exactly 17 uppercase alphanumeric chars, no I/O/Q. "
        "Often near upper-middle section."
    ),
    FieldKey.HALTER_NAME: (
        "Field C.1.1. Holder surname or company name. "
        "Usually in C.* holder block."
    ),
    FieldKey.ERSTZULASSUNG: (
        "Field I. First registration date in DD.MM.YYYY."
    ),
    FieldKey.MARKE: (
        "Field D.1. Manufacturer/brand (e.g. BMW, VOLKSWAGEN)."
    ),
    FieldKey.TYP: (
        "Field D.2. Type/model/variant."
    ),
    FieldKey.HSN: (
        "Field 2.1. Exactly 4 digits."
    ),
    FieldKey.TSN: (
        "Field 2.2. Usually 3 alphanumeric characters; near HSN."
    ),
}

LAYOUT_HINTS_BY_KEY: dict[FieldKey, LayoutHint] = {
    FieldKey.KENNZEICHEN: LayoutHint(
        near_labels=(FieldAnchor.A,),
        zone=LayoutZone.UPPER,
    ),
    FieldKey.FIN: LayoutHint(
        near_labels=(FieldAnchor.E,),
        zone=LayoutZone.UPPER_MIDDLE,
        regex=r"[A-HJ-NPR-Z0-9]{17}",
    ),
    FieldKey.HALTER_NAME: LayoutHint(
        near_labels=(FieldAnchor.C11,),
        zone=LayoutZone.MIDDLE_LEFT,
    ),
    FieldKey.ERSTZULASSUNG: LayoutHint(
        near_labels=(FieldAnchor.I,),
        zone=LayoutZone.MIDDLE,
        regex=r"\d{2}\.\d{2}\.\d{4}",
    ),
    FieldKey.MARKE: LayoutHint(
        near_labels=(FieldAnchor.D1,),
        zone=LayoutZone.MIDDLE_LEFT,
        neighbors=(FieldKey.TYP,),
    ),
    FieldKey.TYP: LayoutHint(
        near_labels=(FieldAnchor.D2,),
        zone=LayoutZone.MIDDLE_LEFT,
        neighbors=(FieldKey.MARKE,),
    ),
    FieldKey.HSN: LayoutHint(
        near_labels=(FieldAnchor.HSN,),
        zone=LayoutZone.LOWER_MIDDLE,
        regex=r"\d{4}",
        neighbors=(FieldKey.TSN,),
    ),
    FieldKey.TSN: LayoutHint(
        near_labels=(FieldAnchor.TSN,),
        zone=LayoutZone.LOWER_MIDDLE,
        neighbors=(FieldKey.HSN,),
    ),
}

FIELD_HINTS: dict[str, str] = {key.value: value for key, value in FIELD_HINTS_BY_KEY.items()}
LAYOUT_HINTS: dict[str, dict[str, Any]] = {
    key.value: hint.to_dict() for key, hint in LAYOUT_HINTS_BY_KEY.items()
}


class VehicleRegistration:
    Schema = Schema
    REQUIRED_FIELDS = REQUIRED_FIELDS
    KNOWLEDGE_BASE_DIR = KNOWLEDGE_BASE_DIR
    CLASSIFY_DESCRIPTION = CLASSIFY_DESCRIPTION
    EXTRACT_ALL = EXTRACT_ALL
    EXTRACT_MISSING = EXTRACT_MISSING
    VALIDATE = VALIDATE
    FIELD_HINTS = FIELD_HINTS
    LAYOUT_HINTS = LAYOUT_HINTS

