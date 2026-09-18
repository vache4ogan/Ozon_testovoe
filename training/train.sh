#!/usr/bin/env bash
set -euo pipefail

MODEL="${MODEL:-yolo26n.pt}"
IMGSZ="${IMGSZ:-960}"
EPOCHS="${EPOCHS:-150}"
BATCH="${BATCH:-16}"

yolo detect train \
  model="$MODEL" \
  data=training/data.yaml \
  imgsz="$IMGSZ" \
  epochs="$EPOCHS" \
  batch="$BATCH" \
  patience=30 \
  device=0 \
  project=runs \
  name=barcode_yolo
