"""Minimal Basler/pypylon acquisition skeleton.

Production version should add:
- camera serial-number mapping
- hardware trigger
- exposure/strobe synchronization
- packet size/GigE tuning
- watchdog/reconnect
- timestamp synchronization
- ring buffers
"""

from pypylon import pylon


def grab_one(serial_number=None):
    tl = pylon.TlFactory.GetInstance()
    devices = tl.EnumerateDevices()

    if not devices:
        raise RuntimeError("No Basler camera found")

    device = devices[0]
    if serial_number:
        for d in devices:
            if d.GetSerialNumber() == serial_number:
                device = d
                break

    camera = pylon.InstantCamera(tl.CreateDevice(device))
    camera.Open()
    camera.StartGrabbingMax(1)

    with camera.RetrieveResult(5000) as result:
        if not result.GrabSucceeded():
            raise RuntimeError(result.ErrorDescription)
        image = result.Array.copy()

    camera.Close()
    return image
