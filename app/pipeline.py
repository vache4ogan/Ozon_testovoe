import argparse
import time
import logging
import queue
import yaml
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

from .capture import CameraCaptureThread
from .plc_adapter import PLCAdapter
from .state_machine import BoxTracker
from .workers import DecoderPool, InferenceWorker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("pipeline")

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status": "ok"}')

def run_pipeline(config_path: str):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # 1. Init PLC Adapter & State Machine
    plc_endpoint = config.get("output", {}).get("plc_endpoint", "http://localhost:8080/api/plc")
    max_latency = config.get("output", {}).get("max_latency_ms_target", 2500) / 1000.0
    plc_adapter = PLCAdapter(endpoint_url=plc_endpoint)
    box_tracker = BoxTracker(plc_adapter=plc_adapter, max_latency_s=max_latency)

    # 2. Init Decoder Pool
    pool_size = config.get("decoder", {}).get("worker_pool_size", 4)
    decoder_pool = DecoderPool(workers=pool_size)

    # 3. Init Queues and Capture Threads
    mock_mode = config.get("vision", {}).get("mock_mode", False)
    cameras_cfg = config.get("vision", {}).get("cameras", {})
    in_queues = {}
    capture_threads = []

    for cam_name, serial in cameras_cfg.items():
        q = queue.Queue(maxsize=10) # bounded queue to avoid memory leak if processing is slow
        in_queues[cam_name] = q
        t = CameraCaptureThread(camera_name=cam_name, serial_number=serial, out_queue=q, mock_mode=mock_mode)
        capture_threads.append(t)

    # 4. Init Inference Worker
    model_path = config.get("detector", {}).get("model", "yolov8n.pt")
    imgsz = config.get("detector", {}).get("imgsz", 960)
    conf = config.get("detector", {}).get("conf", 0.35)
    
    inference_worker = InferenceWorker(
        model_path=model_path,
        in_queues=in_queues,
        box_tracker=box_tracker,
        decoder_pool=decoder_pool,
        imgsz=imgsz,
        conf=conf
    )

    # 5. Start everything
    for t in capture_threads:
        t.start()
    inference_worker.start()

    # Diagnostics HTTP server
    server = HTTPServer(('0.0.0.0', 8000), HealthHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    logger.info("Diagnostics server started on port 8000")

    try:
        # Main loop acting as BoxTracker tick and mock trigger generator
        last_trigger = time.time()
        while True:
            # If in mock mode, trigger a new box every 2 seconds
            if mock_mode and time.time() - last_trigger > 2.0:
                box_tracker.trigger_box()
                last_trigger = time.time()
                
            box_tracker.tick()
            time.sleep(0.05)
    except KeyboardInterrupt:
        logger.info("Shutting down pipeline...")
    finally:
        # Cleanup
        for t in capture_threads:
            t.stop()
        inference_worker.stop()
        
        for t in capture_threads:
            t.join()
        inference_worker.join()
        decoder_pool.shutdown()
        server.shutdown()
        logger.info("Shutdown complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/system.yaml")
    args = parser.parse_args()
    
    run_pipeline(args.config)
