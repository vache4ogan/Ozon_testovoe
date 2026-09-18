import time
import logging
import threading
import queue
import cv2
import numpy as np

try:
    from pypylon import pylon
except ImportError:
    pylon = None

logger = logging.getLogger(__name__)

class CameraCaptureThread(threading.Thread):
    def __init__(self, camera_name: str, serial_number: str, out_queue: queue.Queue, mock_mode: bool = False):
        super().__init__(name=f"CaptureThread-{camera_name}")
        self.camera_name = camera_name
        self.serial_number = serial_number
        self.out_queue = out_queue
        self.mock_mode = mock_mode
        self.running = True
        self.camera = None

    def run(self):
        logger.info(f"Starting capture thread for {self.camera_name} (SN: {self.serial_number})")
        
        while self.running:
            if self.mock_mode:
                self._mock_capture_loop()
            else:
                try:
                    self._connect_and_grab()
                except Exception as e:
                    logger.error(f"Camera {self.camera_name} error: {e}. Reconnecting in 2s...")
                    time.sleep(2)
        
        if self.camera and not self.mock_mode:
            try:
                self.camera.Close()
            except Exception:
                pass

    def _connect_and_grab(self):
        if not pylon:
            raise RuntimeError("pypylon not installed, cannot use real cameras.")

        tl_factory = pylon.TlFactory.GetInstance()
        devices = tl_factory.EnumerateDevices()
        
        target_device = None
        for d in devices:
            if d.GetSerialNumber() == self.serial_number:
                target_device = d
                break
                
        if not target_device:
            raise RuntimeError(f"Camera {self.serial_number} not found.")

        self.camera = pylon.InstantCamera(tl_factory.CreateDevice(target_device))
        self.camera.Open()
        
        # Configure hardware trigger if needed (simplified for prototype)
        # self.camera.TriggerSelector.SetValue("FrameStart")
        # self.camera.TriggerMode.SetValue("On")
        # self.camera.TriggerSource.SetValue("Line1")
        
        self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

        while self.camera.IsGrabbing() and self.running:
            with self.camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException) as res:
                if res.GrabSucceeded():
                    img = res.Array
                    # Put into queue, drop oldest if full
                    if self.out_queue.full():
                        try:
                            self.out_queue.get_nowait()
                        except queue.Empty:
                            pass
                    self.out_queue.put({"camera": self.camera_name, "frame": img.copy(), "timestamp": time.time()})

    def _mock_capture_loop(self):
        # Generate dummy images for testing when no cameras are connected.
        # It's waiting for a 'trigger' via shared state, but we'll just produce a frame 
        # every 2 seconds for testing if no external trigger is provided.
        time.sleep(2)
        if not self.running: return
        img = np.zeros((2048, 2448), dtype=np.uint8)
        cv2.putText(img, f"MOCK {self.camera_name}", (500, 1000), cv2.FONT_HERSHEY_SIMPLEX, 10, 255, 10)
        
        if self.out_queue.full():
            try:
                self.out_queue.get_nowait()
            except queue.Empty:
                pass
        self.out_queue.put({"camera": self.camera_name, "frame": img, "timestamp": time.time()})

    def stop(self):
        self.running = False
        if self.camera and self.camera.IsGrabbing():
            self.camera.StopGrabbing()
