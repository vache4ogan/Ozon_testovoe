import logging
import queue
import threading
from concurrent.futures import ProcessPoolExecutor
from ultralytics import YOLO

from .decoder import decode_crop
from .state_machine import BoxTracker

logger = logging.getLogger(__name__)

class DecoderPool:
    def __init__(self, workers=4):
        self.executor = ProcessPoolExecutor(max_workers=workers)
    
    def submit(self, crop):
        return self.executor.submit(decode_crop, crop)
    
    def shutdown(self):
        self.executor.shutdown(wait=True)

class InferenceWorker(threading.Thread):
    def __init__(self, model_path: str, in_queues: dict, box_tracker: BoxTracker, decoder_pool: DecoderPool, imgsz: int = 960, conf: float = 0.35):
        super().__init__(name="InferenceWorker")
        self.in_queues = in_queues  # dict of camera_name -> queue
        self.box_tracker = box_tracker
        self.decoder_pool = decoder_pool
        self.model_path = model_path
        self.imgsz = imgsz
        self.conf = conf
        self.running = True
        self.model = None

    def run(self):
        logger.info(f"Loading YOLO model from {self.model_path}")
        self.model = YOLO(self.model_path)
        
        while self.running:
            # Poll queues for frames
            for cam_name, q in self.in_queues.items():
                if not self.running:
                    break
                try:
                    frame_data = q.get_nowait()
                    self._process_frame(frame_data)
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Error processing frame from {cam_name}: {e}")

    def _process_frame(self, frame_data):
        box_ctx = self.box_tracker.get_active_box()
        if not box_ctx:
            return  # No active box, ignore frame
            
        cam_name = frame_data["camera"]
        frame = frame_data["frame"]
        
        # Inference
        result = self.model.predict(frame, imgsz=self.imgsz, conf=self.conf, verbose=False)[0]
        
        if result.boxes is None or len(result.boxes) == 0:
            return

        futures = []
        bboxes = []
        confidences = []

        # Crop and submit to decoder
        for box, conf in zip(result.boxes.xyxy.cpu().numpy().astype(int), result.boxes.conf.cpu().numpy()):
            x1, y1, x2, y2 = box.tolist()
            pad_x = max(4, int((x2 - x1) * 0.08))
            pad_y = max(4, int((y2 - y1) * 0.15))
            x1 = max(0, x1 - pad_x)
            y1 = max(0, y1 - pad_y)
            x2 = min(frame.shape[1], x2 + pad_x)
            y2 = min(frame.shape[0], y2 + pad_y)

            crop = frame[y1:y2, x1:x2]
            future = self.decoder_pool.submit(crop)
            futures.append(future)
            bboxes.append([x1, y1, x2, y2])
            confidences.append(float(conf))

        # Wait for decodes (simple blocking per frame for now)
        detections = []
        for future, bbox, conf in zip(futures, bboxes, confidences):
            decoded = future.result()  # blocking
            if decoded:
                detections.append({
                    "bbox": bbox,
                    "confidence": conf,
                    "decoded": decoded
                })

        if detections:
            self.box_tracker.process_frame_results(box_ctx.box_id, cam_name, detections)

    def stop(self):
        self.running = False
