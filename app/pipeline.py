import argparse
import json
from pathlib import Path

import cv2
from ultralytics import YOLO

from .decoder import decode_crop


def run(image_path, model_path, conf=0.35, imgsz=960):
    frame = cv2.imread(str(image_path))
    if frame is None:
        raise FileNotFoundError(image_path)

    model = YOLO(model_path)
    result = model.predict(frame, imgsz=imgsz, conf=conf, verbose=False)[0]

    detections = []
    if result.boxes is not None:
        for box in result.boxes.xyxy.cpu().numpy().astype(int):
            x1, y1, x2, y2 = box.tolist()
            pad_x = max(4, int((x2 - x1) * 0.08))
            pad_y = max(4, int((y2 - y1) * 0.15))
            x1 = max(0, x1 - pad_x)
            y1 = max(0, y1 - pad_y)
            x2 = min(frame.shape[1], x2 + pad_x)
            y2 = min(frame.shape[0], y2 + pad_y)

            crop = frame[y1:y2, x1:x2]
            decoded = decode_crop(crop)

            detections.append({
                "bbox": [x1, y1, x2, y2],
                "decoded": decoded,
            })

    return {"image": str(image_path), "detections": detections}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--conf", type=float, default=0.35)
    parser.add_argument("--imgsz", type=int, default=960)
    args = parser.parse_args()

    print(json.dumps(
        run(args.image, args.model, args.conf, args.imgsz),
        ensure_ascii=False,
        indent=2,
    ))
