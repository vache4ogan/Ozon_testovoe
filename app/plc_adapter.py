import logging
import requests
import json

logger = logging.getLogger(__name__)

class PLCAdapter:
    def __init__(self, endpoint_url: str):
        self.endpoint_url = endpoint_url

    def send(self, payload: dict):
        """Sends the final payload to the PLC/WCS."""
        try:
            logger.info(f"Sending payload to PLC: {json.dumps(payload)}")
            # In a real scenario, this could be Modbus TCP, PROFINET, or a REST API
            response = requests.post(self.endpoint_url, json=payload, timeout=0.5)
            if response.status_code == 200:
                logger.info("Successfully delivered to PLC.")
            else:
                logger.warning(f"PLC returned status {response.status_code}: {response.text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to communicate with PLC: {e}")
