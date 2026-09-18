# Prompt for a coding/research agent

Ты senior computer-vision/embedded engineer. Нужно довести reference-проект
Barcode Conveyor Reader до воспроизводимого production-like прототипа.

## Исходные условия

- conveyor width: 650 mm
- box: 600 x 400 x 400 mm
- speed: 1 m/s
- spacing: ~2 s
- barcode may be on any visible vertical/top face
- multiple barcodes per box and multiple barcodes per face
- sorter is <= 3 m downstream
- target: read ALL visible barcodes and send the set to PLC/WCS.

## Целевая архитектура

5 cameras:
- top
- left
- right
- front
- rear

Use global-shutter monochrome GigE cameras, hardware trigger, short exposure and pulsed LED illumination.

Detector:
- fine-tune a small YOLO detector with one class `barcode`
- start with YOLO26n
- compare YOLO26n vs YOLO26s if recall is insufficient
- do NOT use Vision Transformer as the first production detector; benchmark only if it solves a demonstrated failure mode.

Decoder:
- crop every detection
- add margin
- preprocess multiple variants
- decode with ZBar/pyzbar or another maintained decoder
- if decoder supports the required symbologies, keep a second decoder as fallback
- never use OCR as a substitute for barcode decoding unless the barcode type is unsupported.

Tracking/aggregation:
- create box_id from photoeye trigger
- associate detections from all cameras and frames with the active box
- deduplicate identical decoded values
- retain camera, timestamp, confidence and crop coordinates
- require repeated confirmation where possible
- emit final result before the box reaches the sorter.

## Dataset

Build a production-like dataset, not a random web dataset.

Collect at least:
- 3,000-5,000 full frames for initial prototype
- 10,000+ frames for robust production training if failure cases are diverse
- 1,000+ hard-negative frames with no barcode or barcode-like graphics
- multiple boxes, tape, labels, logos, text, wrinkles and damaged packaging
- all five camera views
- several distances/orientations
- motion blur, glare, shadows, low contrast, dirty labels, partial occlusion

Split by PHYSICAL BOX / recording session, never by random frames from the same video:
- train 70%
- val 15%
- test 15%

Annotation:
- one bounding box per visible barcode
- one class only: `barcode`
- do not include decoded string in detector labels
- include difficult but readable examples
- optionally mark unreadable/occluded labels separately in metadata, not as a detector class.

## Augmentations

Use moderate, physically plausible augmentation:
- brightness/contrast
- blur/motion blur
- JPEG/compression noise
- small rotations
- perspective
- scale
- shadows/glare
- partial occlusion
- sensor noise

Do not overuse mosaic/crazy geometric transforms if they create unrealistic barcode geometry.

## Geometry

For every camera, calculate:
- mm/pixel at the smallest expected barcode
- FOV
- working distance
- exposure needed to keep motion blur below ~1-2 pixels

For a 1 m/s conveyor:
- 1 ms exposure = 1 mm motion
- 0.3 ms exposure = 0.3 mm motion

Use strobe illumination to obtain short effective exposure.

## Decoder stage

For each YOLO crop:
1. enlarge with margin
2. grayscale
3. contrast normalization
4. optional adaptive threshold
5. optional sharpening
6. optional 2x upscale
7. try 0/90/180/270 degree rotations if needed
8. decode
9. validate checksum/symbology where supported
10. store raw crop for diagnostics

If the barcode is heavily skewed:
- estimate the quadrilateral / orientation
- perspective rectify
- decode again.

## Metrics

Measure end-to-end, not only detector mAP:

1. barcode detection recall @ IoU 0.5
2. barcode detection precision
3. decode success per visible barcode
4. all-barcodes-per-box success rate
5. false decoded value rate
6. duplicate rate
7. median and p99 latency
8. missed-box rate
9. PLC message delivery success
10. performance by camera/view and by barcode size.

Most important acceptance metric:
`box_all_codes_success = boxes where every visible required barcode was correctly decoded / total boxes`.

## Engineering

Implement:
- async capture threads
- bounded queues
- inference worker
- decoder worker pool
- box state machine
- watchdog
- camera reconnect
- structured JSON logs
- saved failure crops
- health endpoint or local diagnostics
- deterministic camera serial-number mapping
- configuration in YAML
- unit tests for association/deduplication.

Export detector to TensorRT FP16 and benchmark.
Try INT8 only after establishing FP16 accuracy and building a representative calibration set.

## Output

Produce:
- reproducible training command
- validation report
- benchmark table
- architecture diagram
- deployment Dockerfile
- README
- sample JSON output
- PLC/WCS adapter interface
- failure-case gallery.

Do not claim production readiness without an end-to-end test set captured from the actual conveyor.
