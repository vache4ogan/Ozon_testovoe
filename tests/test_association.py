import time
from app.state_machine import BoxTracker

class MockPLC:
    def __init__(self):
        self.payloads = []
    
    def send(self, payload):
        self.payloads.append(payload)

def test_box_association_and_deduplication():
    plc = MockPLC()
    tracker = BoxTracker(plc_adapter=plc, max_latency_s=0.5)

    # 1. Trigger box
    box_id = tracker.trigger_box()
    
    # 2. Receive first frame with a barcode from top camera
    tracker.process_frame_results(box_id, "top", [
        {"confidence": 0.8, "decoded": [{"value": "12345", "type": "CODE128"}]}
    ])
    
    # 3. Receive another frame with the SAME barcode from left camera (higher conf)
    tracker.process_frame_results(box_id, "left", [
        {"confidence": 0.95, "decoded": [{"value": "12345", "type": "CODE128"}]}
    ])

    # 4. Receive a different barcode from front camera
    tracker.process_frame_results(box_id, "front", [
        {"confidence": 0.9, "decoded": [{"value": "67890", "type": "EAN13"}]}
    ])

    box = tracker.get_active_box()
    assert len(box.barcodes) == 2
    
    b12345 = box.barcodes["12345"]
    assert b12345["consensus"] == 2
    assert b12345["confidence"] == 0.95
    assert b12345["camera"] == "left"
    
    # 5. Wait for max_latency to pass and tick
    time.sleep(0.6)
    tracker.tick()
    
    assert len(plc.payloads) == 1
    payload = plc.payloads[0]
    assert payload["box_id"] == box_id
    assert len(payload["codes"]) == 2
    assert payload["complete"] is True
