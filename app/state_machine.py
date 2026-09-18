import time
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class BoxContext:
    def __init__(self, box_id: str, trigger_time: float):
        self.box_id = box_id
        self.trigger_time = trigger_time
        self.barcodes: Dict[str, Dict[str, Any]] = {}
        self.completed = False

    def add_barcode(self, value: str, code_type: str, camera: str, confidence: float = 1.0, quality: int = None):
        """Adds a barcode to the box, deduplicating by value."""
        # Simple deduplication by value. In a real scenario, we might also 
        # ensure it's not a spatially different barcode with the same value, 
        # but typically the value is unique per barcode instance on the box.
        if value in self.barcodes:
            # Update if confidence is higher or just increment consensus count
            existing = self.barcodes[value]
            existing["consensus"] += 1
            if confidence and existing.get("confidence", 0) < confidence:
                existing["confidence"] = confidence
                existing["camera"] = camera # The camera with the best shot
        else:
            self.barcodes[value] = {
                "value": value,
                "type": code_type,
                "camera": camera,
                "confidence": confidence,
                "quality": quality,
                "consensus": 1
            }

    def get_results(self) -> List[Dict[str, Any]]:
        return list(self.barcodes.values())

class BoxTracker:
    def __init__(self, plc_adapter=None, max_latency_s=2.5):
        self.active_boxes: Dict[str, BoxContext] = {}
        self.plc_adapter = plc_adapter
        self.max_latency_s = max_latency_s
        self.current_box_id = None

    def trigger_box(self) -> str:
        """Called by photoeye to start a new box."""
        box_id = f"box_{time.time_ns()}"
        self.active_boxes[box_id] = BoxContext(box_id, time.time())
        self.current_box_id = box_id
        logger.info(f"Triggered new box: {box_id}")
        return box_id

    def get_active_box(self) -> BoxContext:
        if self.current_box_id:
            return self.active_boxes.get(self.current_box_id)
        return None

    def process_frame_results(self, box_id: str, camera: str, detections: List[Dict[str, Any]]):
        box = self.active_boxes.get(box_id)
        if not box:
            logger.warning(f"Received results for unknown box {box_id}")
            return
        
        for det in detections:
            for decoded in det.get("decoded", []):
                box.add_barcode(
                    value=decoded["value"],
                    code_type=str(decoded["type"]),
                    camera=camera,
                    confidence=det.get("confidence", 1.0),
                    quality=decoded.get("quality", None)
                )

    def tick(self):
        """Called periodically to check for finalized boxes based on time."""
        now = time.time()
        to_remove = []
        for box_id, box in self.active_boxes.items():
            if now - box.trigger_time > self.max_latency_s:
                self._finalize_box(box)
                to_remove.append(box_id)
        
        for box_id in to_remove:
            del self.active_boxes[box_id]
            if self.current_box_id == box_id:
                self.current_box_id = None

    def _finalize_box(self, box: BoxContext):
        box.completed = True
        results = box.get_results()
        logger.info(f"Finalizing box {box.box_id} with {len(results)} unique barcodes.")
        payload = {
            "box_id": box.box_id,
            "codes": results,
            "complete": True,
            "latency_ms": int((time.time() - box.trigger_time) * 1000)
        }
        if self.plc_adapter:
            self.plc_adapter.send(payload)
        else:
            logger.info(f"No PLC Adapter. Payload: {payload}")
