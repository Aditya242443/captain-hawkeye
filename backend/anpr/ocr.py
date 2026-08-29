import re
import logging
from typing import List, Tuple, Union, Optional
import cv2
import numpy as np

logger = logging.getLogger(__name__)


def preprocess_plate_image(image: np.ndarray) -> np.ndarray:
    """
    Applies image preprocessing to improve OCR accuracy on license plate crops:
    - Rescaling to optimal text recognition resolution
    - Contrast enhancement via CLAHE
    - Bilateral filtering to reduce sensor noise while preserving character edges
    """
    if image is None or image.size == 0:
        return image

    h, w = image.shape[:2]

    # Target height around 90-120 pixels for optimal OCR text recognition
    target_height = 96
    if h < target_height or h > 250:
        aspect_ratio = w / float(h)
        new_w = int(target_height * aspect_ratio)
        resized = cv2.resize(image, (new_w, target_height), interpolation=cv2.INTER_CUBIC)
    else:
        resized = image.copy()

    # Convert to grayscale if 3 channels
    if len(resized.shape) == 3:
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    else:
        gray = resized

    # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # Mild bilateral filter to remove noise while keeping edges sharp
    filtered = cv2.bilateralFilter(enhanced, d=5, sigmaColor=50, sigmaSpace=50)

    # Convert back to 3-channel BGR for PaddleOCR
    preprocessed_bgr = cv2.cvtColor(filtered, cv2.COLOR_GRAY2BGR)
    return preprocessed_bgr


def clean_ocr_text(raw_text: str) -> str:
    """
    Strips non-alphanumeric noise, symbols, spaces, and forces uppercase.
    """
    if not raw_text:
        return ""
    cleaned = re.sub(r"[^A-Za-z0-9]", "", raw_text)
    return cleaned.upper()


class PlateOCR:
    """
    PaddleOCR wrapper for recognizing license plate text from cropped plate images.
    """

    def __init__(
        self,
        use_angle_cls: bool = True,
        lang: str = "en",
        use_gpu: bool = False,
        lazy_load: bool = True,
    ):
        self.use_angle_cls = use_angle_cls
        self.lang = lang
        self.use_gpu = use_gpu
        self.ocr = None

        if not lazy_load:
            self._init_ocr()

    def _init_ocr(self):
        """Initializes PaddleOCR instance."""
        if self.ocr is None:
            try:
                from paddleocr import PaddleOCR
                logger.info("Initializing PaddleOCR (lang=%s, use_gpu=%s)...", self.lang, self.use_gpu)
                self.ocr = PaddleOCR(
                    use_angle_cls=self.use_angle_cls,
                    lang=self.lang,
                    device="gpu" if self.use_gpu else "cpu",
                    enable_mkldnn=False,
                )
            except Exception as e:
                logger.warning("PaddleOCR initialization warning / fallback: %s", e)
                self.ocr = None
                

    def recognize_single(
        self,
        image: np.ndarray,
        preprocess: bool = True,
    ) -> Tuple[str, float]:
        """
        Runs OCR on a single cropped plate image.

        Returns:
        - Tuple of (cleaned_text, confidence_score)
        """
        if image is None or image.size == 0:
            return "", 0.0

        self._init_ocr()
        if self.ocr is None:
            # Fallback if PaddleOCR is not installed/initialized
            return "", 0.0

        proc_img = preprocess_plate_image(image) if preprocess else image

        try:
            result = self.ocr.predict(proc_img)

            if not result:
                return "", 0.0

            page = result[0]
            rec_texts = page.get("rec_texts", [])
            rec_scores = page.get("rec_scores", [])

            if not rec_texts:
                return "", 0.0

            text_parts = []
            conf_parts = []

            for txt, conf in zip(rec_texts, rec_scores):
                cleaned = clean_ocr_text(txt)
                if cleaned:
                    text_parts.append(cleaned)
                    conf_parts.append(float(conf))

            if not text_parts:
                return "", 0.0

            full_text = "".join(text_parts)
            avg_conf = float(np.mean(conf_parts)) if conf_parts else 0.0
            return full_text, avg_conf

        except Exception as e:
            logger.error("Error during OCR inference: %s", e)
            return "", 0.0

    
    def recognize(
        self,
        images: Union[np.ndarray, List[np.ndarray]],
        preprocess: bool = True,
    ) -> List[Tuple[str, float]]:
        """
        Runs OCR on a single image or a list of candidate images.

        Returns:
        - List of (text, confidence) tuples
        """
        if isinstance(images, np.ndarray):
            return [self.recognize_single(images, preprocess=preprocess)]

        results = []
        for img in images:
            results.append(self.recognize_single(img, preprocess=preprocess))
        return results


# Global singleton OCR instance
_global_ocr: Optional[PlateOCR] = None


def get_ocr() -> PlateOCR:
    """Returns or lazily creates a singleton PlateOCR instance."""
    global _global_ocr
    if _global_ocr is None:
        _global_ocr = PlateOCR(lazy_load=True)
    return _global_ocr
