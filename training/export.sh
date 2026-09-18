#!/usr/bin/env bash
set -euo pipefail

MODEL="${MODEL:-runs/barcode_yolo/weights/best.pt}"

yolo export \
  model="$MODEL" \
  format=engine \
  imgsz=960 \
  half=True
