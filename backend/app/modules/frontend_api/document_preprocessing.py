from __future__ import annotations

import io
import logging
import math
from pathlib import Path
from typing import Any

logger = logging.getLogger("translatrix.preprocessing")

try:
    import cv2
    import numpy as np
    from PIL import Image
except ImportError:
    cv2 = None
    np = None
    Image = None


class ImagePreprocessor:
    """Clean and enhance document images before OCR processing.

    Applies deskew, denoise, CLAHE contrast enhancement, adaptive thresholding,
    border removal, and rotation correction to maximise OCR accuracy.
    """

    MIN_DESKEW_ANGLE = 0.5
    TARGET_DPI = 350

    @staticmethod
    def is_available() -> bool:
        return cv2 is not None and np is not None

    def preprocess_pdf_page(
        self, image: Image.Image, dpi: int | None = None
    ) -> Image.Image:
        if not self.is_available():
            return image
        target_dpi = dpi or self.TARGET_DPI
        dpi_info = image.info.get("dpi")
        if isinstance(dpi_info, (tuple, list)):
            current_dpi = dpi_info[0]
        elif isinstance(dpi_info, (int, float)):
            current_dpi = dpi_info
        else:
            current_dpi = target_dpi
        if abs(current_dpi - target_dpi) > 50:
            scale = target_dpi / max(current_dpi, 72)
            new_size = (int(image.width * scale), int(image.height * scale))
            image = image.resize(new_size, Image.LANCZOS)
        return self._pipeline(image)

    def preprocess_image(self, image: Image.Image) -> Image.Image:
        if not self.is_available():
            return image
        return self._pipeline(image)

    def _pipeline(self, pil_image: Image.Image) -> Image.Image:
        img = self._pil_to_cv2(pil_image)
        img = self._remove_borders(img)
        img = self._deskew(img)
        img = self._denoise(img)
        img = self._clahe_enhance(img)
        img = self._adaptive_threshold(img)
        return self._cv2_to_pil(img)

    def get_processing_metadata(self, pil_image: Image.Image) -> dict[str, Any]:
        meta: dict[str, Any] = {
            "preprocessor_available": self.is_available(),
            "original_size": {"width": pil_image.width, "height": pil_image.height},
        }
        if not self.is_available():
            return meta
        img = self._pil_to_cv2(pil_image)
        angle = self._compute_skew_angle(img)
        meta["detected_skew_angle"] = round(angle, 2)
        meta["steps_applied"] = [
            "border_removal",
            "deskew",
            "denoise",
            "clahe",
            "adaptive_threshold",
        ]
        return meta

    def _pil_to_cv2(self, pil: Image.Image) -> Any:
        arr = np.array(pil.convert("RGB"))
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

    def _cv2_to_pil(self, cv_img: Any) -> Image.Image:
        rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)

    def _deskew(self, img: Any) -> Any:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.bitwise_not(gray)
        coords = np.column_stack(np.where(gray > 0))
        if coords.shape[0] < 10:
            return img
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = 90 + angle
        if abs(angle) < self.MIN_DESKEW_ANGLE:
            return img
        h, w = img.shape[:2]
        center = (w // 2, h // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(
            img, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )

    def _compute_skew_angle(self, img: Any) -> float:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.bitwise_not(gray)
        coords = np.column_stack(np.where(gray > 0))
        if coords.shape[0] < 10:
            return 0.0
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = 90 + angle
        return angle

    def _denoise(self, img: Any) -> Any:
        return cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)

    def _clahe_enhance(self, img: Any) -> Any:
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        lab = cv2.merge([l, a, b])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    def _adaptive_threshold(self, img: Any) -> Any:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2
        )
        return cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)

    def _remove_borders(self, img: Any) -> Any:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)[1]
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return img
        h, w = img.shape[:2]
        margin = int(min(h, w) * 0.02)
        x, y, cw, ch = cv2.boundingRect(max(contours, key=cv2.contourArea))
        x = max(0, x - margin)
        y = max(0, y - margin)
        cw = min(w - x, cw + 2 * margin)
        ch = min(h - y, ch + 2 * margin)
        if cw < w * 0.3 or ch < h * 0.3:
            return img
        return img[y : y + ch, x : x + cw]

    def correct_rotation(self, img: Any) -> Any:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.bitwise_not(gray)
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        coords = np.column_stack(np.where(thresh > 0))
        if coords.shape[0] < 100:
            return img
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = 90 + angle
        if abs(angle) < 0.5:
            return img
        h, w = img.shape[:2]
        center = (w // 2, h // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(
            img, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )
