import io

import numpy as np
from PIL import Image
from onnxtr.models import ocr_predictor

from app.models import OCRResult

_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/tiff"}
_MIN_CONFIDENCE = 0.4


class OnnxTR:
    def __init__(self) -> None:
        self._engine = ocr_predictor(
            det_arch="db_mobilenet_v3_large",
            reco_arch="crnn_mobilenet_v3_small",
            assume_straight_pages=True,
            preserve_aspect_ratio=True,
            symmetric_pad=True,
        )

        self._engine.det_predictor.model.postprocessor.box_thresh = 0.3

    async def extract(self, file_bytes: bytes, mime_type: str) -> OCRResult:
        """Extract OCR result from file bytes"""
        pages = self._pages(file_bytes, mime_type)
        result = self._engine(pages)

        parts: list[str] = []
        for page in result.export()["pages"]:
            for block in page["blocks"]:
                for line in block["lines"]:
                    words = [
                        word["value"]
                        for word in line["words"]
                        if word["confidence"] >= _MIN_CONFIDENCE
                    ]
                    if words:
                        parts.append(" ".join(words))

        return OCRResult(text="\n".join(parts), pages=len(pages))

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
