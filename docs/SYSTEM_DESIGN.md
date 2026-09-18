# System design summary

## Recommended topology

The baseline is a five-camera ring around the conveyor:

        [TOP CAMERA]
             |
 [LEFT] -- BOX -- [RIGHT]
             |
      [FRONT] [REAR]

All five cameras look at the corresponding visible face. The cameras are placed
in a short inspection tunnel approximately 0.8-1.5 m long. The exact geometry
is set after measuring the smallest barcode and the available mounting envelope.

A photoelectric trigger is placed upstream of the camera trigger plane. The
trigger starts an inspection window. Each camera may acquire several frames
while the box crosses the zone; frames are associated with the same box_id.

## Important mechanical limitation

A barcode on the physical bottom face cannot be observed by cameras mounted
above/around a solid conveyor. If "any face" literally includes the bottom,
the conveyor must provide an optical gap / underside camera or the box must be
lifted/turned. This must be resolved before final acceptance testing.

## Recommended compute

NVIDIA Jetson Orin NX 16 GB is a practical edge target. It provides enough
GPU headroom for a small detector plus image processing while keeping the
system local and deterministic. Training should be done on a workstation/cloud
GPU; only inference runs on the edge device.

## Why local inference

The sorter is safety/operations adjacent and has a hard latency constraint.
Sending raw frames to a cloud introduces network dependency, variable latency,
privacy/security concerns and an unnecessary bandwidth load. The edge device
should therefore perform detection, decoding, aggregation and output locally.

## Detector vs decoder

The neural network is not responsible for reading the numeric/string payload.
Its job is to find every barcode rectangle. A specialized barcode decoder is
then used on the crop. This separation makes the system easier to validate and
lets the decoder exploit barcode geometry/checksum rules.

## Camera sizing

For the example Basler 5 MP camera (2448 x 2048), a 650-700 mm horizontal FOV
gives roughly 3.5-3.8 pixels/mm. A 50 mm-wide barcode therefore occupies
~175-190 pixels horizontally before perspective effects. This is a starting
point; the actual minimum barcode dimensions must be inserted into the optical
calculation.

## Timing

At 1 m/s:
- 1 ms exposure => ~1 mm physical movement during exposure
- 0.3 ms => ~0.3 mm movement

Use short exposure and high-intensity pulsed LED lighting rather than increasing
exposure time.

The 2 s box spacing is generous relative to a ~0.6 s box transit time for a
600 mm dimension at 1 m/s. The pipeline should nevertheless use a state machine
rather than assuming exactly 2 s spacing.

## Data flow

Photoeye
 -> trigger/timestamp
 -> 5 camera captures
 -> YOLO barcode detection
 -> crop + preprocessing
 -> barcode decoder
 -> multi-frame/camera aggregation
 -> deduplication
 -> validation
 -> PLC/WCS message
 -> audit log

## Output example

```json
{
  "box_id": "2026-09-18T18:42:31.418Z_000184",
  "codes": [
    {"value": "ABC123456", "type": "CODE128", "camera": "left", "confidence": 0.94},
    {"value": "99887766", "type": "CODE128", "camera": "top", "confidence": 0.89}
  ],
  "complete": true,
  "latency_ms": 147
}
```
