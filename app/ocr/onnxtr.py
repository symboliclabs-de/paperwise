import io
import re
from typing import Iterable

import numpy as np
from PIL import Image
from onnxtr.models import ocr_predictor

from app.models import OCRResult

_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/tiff"}
_MIN_CONFIDENCE = 0.4
_LABEL_PATTERN = re.compile(r"^[A-Z0-9]{1,3}(?:\.[A-Z0-9]{1,3}){0,2}$")


class OnnxTR:
    def __init__(self) -> None:
        """Initialize OnnxTR OCR engine with CPU-friendly defaults."""
        self._engine = ocr_predictor(
            det_arch="db_mobilenet_v3_large",
            reco_arch="crnn_mobilenet_v3_small",
            assume_straight_pages=True,
            preserve_aspect_ratio=True,
            symmetric_pad=True,
        )

        self._engine.det_predictor.model.postprocessor.box_thresh = 0.3

    async def extract(
        self,
        file_bytes: bytes,
        mime_type: str,
        anchors: Iterable[str] | None = None,
    ) -> OCRResult:
        """Extract OCR result from file bytes"""
        pages = self._pages(file_bytes, mime_type)
        result = self._engine(pages)
        normalized_anchors = self._normalize_anchors(anchors or ())

        parts: list[str] = []
        layout_lines: list[dict[str, object]] = []
        for page_idx, page in enumerate(result.export()["pages"], start=1):
            for block in page["blocks"]:
                for line in block["lines"]:
                    line_words = line.get("words", [])
                    words = [
                        word["value"]
                        for word in line_words
                        if word["confidence"] >= _MIN_CONFIDENCE
                        or self._is_anchor_or_label(word["value"], normalized_anchors)
                    ]
                    if words:
                        parts.append(" ".join(words))

                    line_text = " ".join(
                        word.get("value", "") for word in line_words if word.get("value")
                    )
                    if line_text:
                        layout_lines.append(
                            {
                                "page": page_idx,
                                "text": line_text,
                                "confidence": self._avg_confidence(line_words),
                                "bbox": line.get("geometry"),
                            }
                        )

        return OCRResult(text="\n".join(parts), pages=len(pages), layout_lines=layout_lines)

    @staticmethod
    def _pages(file_bytes: bytes, mime_type: str) -> list[np.ndarray]:
        """Get document pages from file bytes"""
        if mime_type == "application/pdf":
            from pdf2image import convert_from_bytes

            images = convert_from_bytes(file_bytes, dpi=300)
        elif mime_type in _IMAGE_TYPES:
            images = [Image.open(io.BytesIO(file_bytes))]
        else:
            raise ValueError(f"Unsupported mime type: {mime_type}")
        return [np.array(image.convert("RGB")) for image in images]

    @staticmethod
    def _is_anchor_or_label(anchor: str, normalized_anchors: set[str]) -> bool:
        """Return true for configured anchors or field-like label tokens."""
        normalized = OnnxTR._normalize_anchor(anchor)
        if not normalized:
            return False
        if normalized in normalized_anchors:
            return True
        if not _LABEL_PATTERN.match(normalized):
            return False
        return (
            "." in normalized or any(char.isdigit() for char in normalized) or len(normalized) == 1
        )

    @staticmethod
    def _normalize_anchor(anchor: str) -> str:
        """Normalize OCR token for robust anchor matching."""
        normalized = anchor.strip().upper().replace(" ", "")
        if normalized.endswith((".", ":")):
            normalized = normalized[:-1]
        normalized = normalized.replace("L", "1").replace("I", "1").replace("O", "0")
        return normalized

    @staticmethod
    def _normalize_anchors(anchors: Iterable[str]) -> set[str]:
        """Normalize and deduplicate configured anchors."""
        return {normalized for token in anchors if (normalized := OnnxTR._normalize_anchor(token))}

    @staticmethod
    def _avg_confidence(words: list[dict]) -> float:
        """Compute average confidence for one OCR line."""
        if not words:
            return 0.0
        return sum(float(word.get("confidence", 0.0)) for word in words) / len(words)
