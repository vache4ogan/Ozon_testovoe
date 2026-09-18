import cv2
import numpy as np

try:
    from pyzbar.pyzbar import decode as zbar_decode
except ImportError:
    zbar_decode = None


def _variants(crop):
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
    yield gray

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    yield clahe

    blur = cv2.GaussianBlur(clahe, (3, 3), 0)
    yield cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 7
    )

    yield cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    sharp = cv2.addWeighted(clahe, 1.7, cv2.GaussianBlur(clahe, (0, 0), 1.0), -0.7, 0)
    yield sharp


def decode_crop(crop):
    if zbar_decode is None:
        raise RuntimeError("Install pyzbar and the system ZBar library")

    found = []
    for image in _variants(crop):
        for item in zbar_decode(image):
            value = item.data.decode("utf-8", errors="replace")
            found.append({
                "value": value,
                "type": item.type,
                "quality": getattr(item, "quality", None),
                "rect": [
                    item.rect.left, item.rect.top,
                    item.rect.width, item.rect.height
                ],
            })

    # Deduplicate decoder outputs from multiple preprocessing variants.
    unique = {}
    for item in found:
        unique[(item["type"], item["value"])] = item
    return list(unique.values())
