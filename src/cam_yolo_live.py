#!/usr/bin/env python3
"""Live IMX708 + YOLOv8n inference on Jetson Orin Nano.

Streams MJPEG over HTTP on port 5000 with YOLO bounding boxes per frame.
Auto-selects CUDA if available, otherwise runs on CPU.

No fallback image: if the camera or model fails to open, the process exits
with a clear message.

Endpoints:
  /         landing page
  /stream   MJPEG stream
  /health   JSON status
"""
import os
import sys
import time

import cv2
import torch
from flask import Flask, Response, render_template_string
from ultralytics import YOLO


# ---------- device selection ----------
CUDA_OK = torch.cuda.is_available()
DEVICE = 0 if CUDA_OK else "cpu"
DEVICE_LABEL = f"cuda:0 ({torch.cuda.get_device_name(0)})" if CUDA_OK else "cpu"
print(f"[startup] torch {torch.__version__}", flush=True)
print(f"[startup] cuda available: {CUDA_OK}", flush=True)
print(f"[startup] inference device: {DEVICE_LABEL}", flush=True)


# ---------- camera ----------
GST_PIPELINE = (
    "nvarguscamerasrc sensor-id=0 sensor-mode=0 ! "
    "video/x-raw(memory:NVMM), width=4608, height=2592, framerate=14/1, format=NV12 ! "
    "nvvidconv flip-method=0 ! "
    "video/x-raw, width=960, height=540, format=BGRx ! "
    "videoconvert ! video/x-raw, format=BGR ! "
    "appsink drop=1 max-buffers=1"
)

def _open_camera_with_retry(max_attempts=6, delay=4):
    """nvargus often needs a few seconds to release after a previous app exits."""
    for attempt in range(1, max_attempts + 1):
        print(f"[startup] camera open attempt {attempt}/{max_attempts} ...", flush=True)
        cap = cv2.VideoCapture(GST_PIPELINE, cv2.CAP_GSTREAMER)
        if cap.isOpened():
            ok, frame = cap.read()
            if ok and frame is not None:
                print(f"[startup] camera opened on attempt {attempt}; frame {frame.shape}",
                      flush=True)
                return cap, frame
            cap.release()
        if attempt < max_attempts:
            print(f"[startup] attempt {attempt} failed, waiting {delay}s for nvargus to settle ...",
                  flush=True)
            time.sleep(delay)
    print("CAMERA OPEN FAILED after all retries.", file=sys.stderr, flush=True)
    sys.exit(2)


print("[startup] opening IMX708 via nvarguscamerasrc ...", flush=True)
CAMERA, frame = _open_camera_with_retry()


# ---------- model ----------
print("[startup] loading YOLOv8n ...", flush=True)
MODEL_PATH = os.getenv("WISP_MODEL_PATH", os.path.expanduser("~/yolov8n.engine"))
MODEL = YOLO(MODEL_PATH)  # TensorRT FP16 engine built for this Jetson
print("[startup] warming model ...", flush=True)
_warm = MODEL(frame, verbose=False, device=DEVICE, imgsz=640)
print(f"[startup] YOLO warm on {DEVICE_LABEL}. Flask starting on :5000 ...",
      flush=True)


# ---------- Flask ----------
app = Flask(__name__)


def gen_frames():
    last_t = time.monotonic()
    fps_ema = 0.0
    while True:
        ok, frame = CAMERA.read()
        if not ok or frame is None:
            continue

        t0 = time.monotonic()
        res = MODEL(frame, verbose=False, device=DEVICE, imgsz=640)
        infer_ms = (time.monotonic() - t0) * 1000.0
        annotated = res[0].plot()

        now = time.monotonic()
        dt = now - last_t
        if dt > 0:
            inst = 1.0 / dt
            fps_ema = inst if fps_ema == 0 else 0.85 * fps_ema + 0.15 * inst
        last_t = now

        h, w = annotated.shape[:2]
        cv2.rectangle(annotated, (0, 0), (w, 32), (0, 0, 0), -1)
        label = (f"IMX708 + YOLOv8n [{'cuda' if CUDA_OK else 'cpu'}]   "
                 f"{fps_ema:5.1f} FPS   {infer_ms:5.1f} ms/inf")
        cv2.putText(annotated, label, (10, 22), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (0, 255, 0), 2, cv2.LINE_AA)

        ok2, jpg = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ok2:
            continue
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
               + jpg.tobytes() + b"\r\n")


INDEX_HTML = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>IMX708 live + YOLOv8n</title>
<style>
  html, body { margin: 0; padding: 0; background: #0a0d12; color: #e0e6f0;
               font-family: -apple-system, BlinkMacSystemFont, system-ui, sans-serif; }
  .wrap { max-width: 1100px; margin: 0 auto; padding: 16px; text-align: center; }
  h1    { font-size: 18px; color: #88c0d0; margin: 6px 0 14px; font-weight: 500; }
  img   { max-width: 100%; height: auto; border: 1px solid #3b4252; border-radius: 8px; }
  .meta { color: #909aa9; font-size: 12px; margin-top: 10px; line-height: 1.5; }
  code  { background: #2e3440; padding: 1px 6px; border-radius: 4px; color: #d8dee9; }
</style>
</head>
<body>
<div class="wrap">
  <h1>Jetson Orin Nano Super &mdash; IMX708 live + YOLOv8n</h1>
  <img src="/stream" alt="live IMX708 + YOLO">
  <div class="meta">
    MJPEG stream with real-time YOLOv8n object detection.
    Reload the page if frames stall. Status: <code>/health</code>.
  </div>
</div>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(INDEX_HTML)


@app.route("/stream")
def stream():
    return Response(gen_frames(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/health")
def health():
    return {
        "camera": True,
        "model": "yolov8n",
        "device": "cuda:0" if CUDA_OK else "cpu",
        "imgsz": 640,
        "torch_version": torch.__version__,
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
