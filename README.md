# Barcode Conveyor Reader

Базовый reference-проект для считывания нескольких штрихкодов на коробках на конвейере.

## Архитектура

1. Фотоэлектрический датчик фиксирует вход коробки в зону считывания.
2. Пять монохромных global-shutter камер снимают верхнюю и четыре вертикальные грани.
3. YOLO обнаруживает все области `barcode`.
4. Каждый crop увеличивается/нормализуется; при необходимости выполняется deskew/perspective correction.
5. Декодер barcode/2D-кодов пытается прочитать код.
6. Результаты агрегируются по `box_id` и дедуплицируются по значению + пространственной близости + времени.
7. Результат отправляется в PLC/WCS по выбранному промышленному протоколу.

## Структура

- `app/pipeline.py` — reference pipeline для изображений/камер.
- `app/decoder.py` — декодирование crop через pyzbar/ZBar.
- `app/capture.py` — заготовка для Basler/pypylon.
- `training/data.yaml` — конфигурация датасета.
- `training/train.sh` — запуск fine-tuning.
- `training/export.sh` — экспорт в TensorRT.
- `configs/system.yaml` — параметры системы.
- `docs/AGENT_PROMPT.md` — готовый prompt для coding/research агента.

## Быстрый запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install ultralytics opencv-python numpy pyzbar pyyaml
python -m app.pipeline --image path/to/frame.jpg --model weights/best.pt
```

Для Linux может потребоваться системная библиотека ZBar.

## Обучение

```bash
pip install ultralytics
bash training/train.sh
```

Датасет должен быть в YOLO-формате:

```text
dataset/
  images/train/
  images/val/
  labels/train/
  labels/val/
```

Единственный класс на первом этапе: `barcode`.

После обучения:

```bash
bash training/export.sh
```

Для промышленного внедрения модель нужно прогнать на отдельном production-like test set и измерить не только mAP, но и end-to-end barcode read rate per box.
