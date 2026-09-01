#!/usr/bin/env python3
"""WISP perception service (Jetson).

The "Eyes" of the WISP runtime. Opens the IMX708 camera, runs YOLOv8n-pose on
the GPU, and turns body keypoints into a live stream of:

  - head position  (x, y in normalized -1..1, z as an approximate distance)
  - hand positions  (left/right wrist, normalized, with presence)

It serves three HTTP endpoints (plain Flask — no extra deps, works offline):

  GET /            small status page
  GET /state       Server-Sent Events stream of perception JSON (for the renderer)
  GET /camera      MJPEG debug feed with the pose skeleton + head/hand markers
  GET /health      JSON status

Run on the Jetson:
  LD_LIBRARY_PATH=$HOME/libcusparselt/lib:$LD_LIBRARY_PATH python3 ~/wisp_perception.py

NOTE: depth (z) is approximate. It is derived from the pixel distance between the
eyes vs a known ~63 mm interpupillary distance. Real accuracy needs camera
intrinsic calibration (a future step). x/y are reliable; z is a usable estimate.
"""
import json
import os
import sys
import threading
import time

import cv2
import numpy as np
from flask import Flask, Response, render_template_string
from ultralytics import YOLO

# ---------- config ----------
MODEL_PATH = os.getenv("WISP_MODEL_PATH", os.path.expanduser("~/yolov8n-pose.pt"))
FRAME_W, FRAME_H = 960, 540
MIRROR = True              # camera faces the viewer -> mirror x for natural feel
KP_CONF = 0.35             # min keypoint confidence to trust
EMA = 0.45                 # smoothing factor for head (0=frozen, 1=raw/jittery)

# depth calibration (approximate; tune later with real calibration)
EYE_PX_NEAR = 130.0        # eyes this far apart in px  -> close
EYE_PX_FAR  = 26.0         # eyes this far apart in px  -> far
EYE_Z_NEAR  = 3.2          # renderer eye-z when close
EYE_Z_FAR   = 9.0          # renderer eye-z when far

# COCO pose keypoint indices
NOSE, L_EYE, R_EYE, L_EAR, R_EAR = 0, 1, 2, 3, 4
L_WRIST, R_WRIST = 9, 10

GST = (
    "nvarguscamerasrc sensor-id=0 sensor-mode=0 ! "
    "video/x-raw(memory:NVMM), width=4608, height=2592, framerate=14/1, format=NV12 ! "
    "nvvidconv flip-method=0 ! "
    f"video/x-raw, width={FRAME_W}, height={FRAME_H}, format=BGRx ! "
    "videoconvert ! video/x-raw, format=BGR ! appsink drop=1 max-buffers=1"
)


def open_camera(max_attempts=6, delay=4):
    for attempt in range(1, max_attempts + 1):
        print(f"[startup] camera open attempt {attempt}/{max_attempts}", flush=True)
        cap = cv2.VideoCapture(GST, cv2.CAP_GSTREAMER)
        if cap.isOpened():
            ok, frame = cap.read()
            if ok and frame is not None:
                print(f"[startup] camera live {frame.shape}", flush=True)
                return cap
            cap.release()
        if attempt < max_attempts:
            time.sleep(delay)
    print("CAMERA OPEN FAILED", file=sys.stderr, flush=True)
    sys.exit(2)


def lerp_clamp(v, in0, in1, out0, out1):
    if in1 == in0:
        return out0
    t = (v - in0) / (in1 - in0)
    t = max(0.0, min(1.0, t))
    return out0 + t * (out1 - out0)


# ---------- shared state ----------
STATE = {
    "head": {"x": 0.0, "y": 0.0, "z": 5.0, "present": False},
    "hands": {
        "left":  {"x": 0.0, "y": 0.0, "present": False},
        "right": {"x": 0.0, "y": 0.0, "present": False},
    },
    "people": 0,
    "fps": 0.0,
    "ts": 0,
}
LOCK = threading.Lock()
LATEST_JPEG = [None]
_ema = {"x": 0.0, "y": 0.0, "z": 5.0, "init": False}


def norm_xy(px, py):
    """pixel -> normalized -1..1, x mirrored if configured, y up-positive."""
    nx = (px / FRAME_W) * 2.0 - 1.0
    ny = (py / FRAME_H) * 2.0 - 1.0
    if MIRROR:
        nx = -nx
    return nx, -ny  # flip y so up is positive (renderer convention)


def pick_person(kps_xy, kps_conf):
    """Choose the most prominent person: largest eye/nose spread with good conf."""
    best, best_score = -1, -1.0
    for i in range(kps_xy.shape[0]):
        conf = kps_conf[i]
        # head visible?
        if conf[L_EYE] < KP_CONF and conf[R_EYE] < KP_CONF and conf[NOSE] < KP_CONF:
            continue
        # score by shoulder/eye span (closer person = bigger) + mean conf
        span = 0.0
        if conf[L_EYE] >= KP_CONF and conf[R_EYE] >= KP_CONF:
            span = float(np.linalg.norm(kps_xy[i][L_EYE] - kps_xy[i][R_EYE]))
        score = span + 40.0 * float(conf.mean())
        if score > best_score:
            best_score, best = score, i
    return best


def worker():
    cap = open_camera()
    print("[startup] loading YOLOv8n-pose on GPU ...", flush=True)
    model = YOLO(MODEL_PATH)
    # warm
    ok, frame = cap.read()
    if ok and frame is not None:
        model(frame, verbose=False, device=0, imgsz=640)
    print("[startup] pose model warm. perception loop running.", flush=True)

    last_t = time.monotonic()
    fps = 0.0
    while True:
        ok, frame = cap.read()
        if not ok or frame is None:
            time.sleep(0.01)
            continue

        res = model(frame, verbose=False, device=0, imgsz=640)
        r = res[0]
        annotated = r.plot()

        head = {"x": 0.0, "y": 0.0, "z": _ema["z"], "present": False}
        hands = {"left": {"x": 0.0, "y": 0.0, "present": False},
                 "right": {"x": 0.0, "y": 0.0, "present": False}}
        n_people = 0

        if r.keypoints is not None and r.keypoints.xy is not None and len(r.keypoints.xy) > 0:
            kps_xy = r.keypoints.xy.cpu().numpy()          # [n,17,2]
            kps_conf = (r.keypoints.conf.cpu().numpy()
                        if r.keypoints.conf is not None
                        else np.ones((kps_xy.shape[0], 17)))
            n_people = kps_xy.shape[0]
            idx = pick_person(kps_xy, kps_conf)
            if idx >= 0:
                xy, cf = kps_xy[idx], kps_conf[idx]

                # head center: midpoint of eyes, else nose
                if cf[L_EYE] >= KP_CONF and cf[R_EYE] >= KP_CONF:
                    cx = (xy[L_EYE][0] + xy[R_EYE][0]) / 2.0
                    cy = (xy[L_EYE][1] + xy[R_EYE][1]) / 2.0
                    eye_px = float(np.linalg.norm(xy[L_EYE] - xy[R_EYE]))
                    z = lerp_clamp(eye_px, EYE_PX_FAR, EYE_PX_NEAR, EYE_Z_FAR, EYE_Z_NEAR)
                elif cf[NOSE] >= KP_CONF:
                    cx, cy = float(xy[NOSE][0]), float(xy[NOSE][1])
                    z = _ema["z"]
                else:
                    cx = cy = None
                    z = _ema["z"]

                if cx is not None:
                    nx, ny = norm_xy(cx, cy)
                    if not _ema["init"]:
                        _ema.update(x=nx, y=ny, z=z, init=True)
                    else:
                        _ema["x"] += EMA * (nx - _ema["x"])
                        _ema["y"] += EMA * (ny - _ema["y"])
                        _ema["z"] += EMA * (z - _ema["z"])
                    head = {"x": round(_ema["x"], 4), "y": round(_ema["y"], 4),
                            "z": round(_ema["z"], 4), "present": True}

                # hands (wrists)
                for side, k in (("left", L_WRIST), ("right", R_WRIST)):
                    if cf[k] >= KP_CONF:
                        hx, hy = norm_xy(float(xy[k][0]), float(xy[k][1]))
                        hands[side] = {"x": round(hx, 4), "y": round(hy, 4), "present": True}

        # fps
        now = time.monotonic()
        dt = now - last_t
        if dt > 0:
            fps = 0.85 * fps + 0.15 * (1.0 / dt)
        last_t = now

        # overlay head/hand readout
        cv2.rectangle(annotated, (0, 0), (annotated.shape[1], 30), (0, 0, 0), -1)
        cv2.putText(annotated,
                    f"WISP perception  {fps:4.1f} FPS  people:{n_people}  "
                    f"head:{'Y' if head['present'] else '-'} "
                    f"({head['x']:+.2f},{head['y']:+.2f},z{head['z']:.1f})",
                    (8, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)

        ok2, jpg = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 75])
        with LOCK:
            STATE["head"] = head
            STATE["hands"] = hands
            STATE["people"] = n_people
            STATE["fps"] = round(fps, 1)
            STATE["ts"] = int(now * 1000)
            if ok2:
                LATEST_JPEG[0] = jpg.tobytes()


# ---------- Flask ----------
app = Flask(__name__)


@app.after_request
def cors(resp):
    # allow the renderer to consume the stream from any origin (incl. file://)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp

PAGE = """<!doctype html><meta charset=utf-8>
<title>WISP perception</title>
<style>body{font-family:system-ui;background:#0F0B07;color:#F5EFE3;margin:0;padding:28px}
a{color:#F2B45C}img{max-width:100%;border:1px solid #333;border-radius:8px;margin-top:14px}
pre{background:#18120B;padding:12px;border-radius:8px;color:#BCB2A0}</style>
<h2>WISP perception service</h2>
<p>Endpoints: <a href="/camera">/camera</a> (debug video) ·
<a href="/state">/state</a> (SSE) · <a href="/health">/health</a></p>
<img src="/camera" alt="debug feed">
<pre id="s">connecting…</pre>
<script>
const es=new EventSource('/state');
es.onmessage=e=>{document.getElementById('s').textContent=e.data;};
</script>"""


@app.route("/")
def index():
    return render_template_string(PAGE)


@app.route("/state")
def state():
    def gen():
        while True:
            with LOCK:
                payload = json.dumps(STATE)
            yield f"data: {payload}\n\n"
            time.sleep(1 / 30.0)
    return Response(gen(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/camera")
def camera():
    def gen():
        while True:
            with LOCK:
                jpg = LATEST_JPEG[0]
            if jpg is not None:
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n")
            time.sleep(1 / 15.0)
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/wisp")
def wisp():
    # the device serves its own renderer/experience UI (same-origin, no CORS)
    import os
    path = os.path.expanduser("~/wisp.html")
    if os.path.exists(path):
        with open(path) as f:
            return f.read()
    return "<p>wisp.html not deployed yet.</p>", 404


@app.route("/health")
def health():
    with LOCK:
        return dict(STATE, service="wisp-perception", model="yolov8n-pose")


if __name__ == "__main__":
    threading.Thread(target=worker, daemon=True).start()
    # give the worker a moment to open the camera + load the model before serving
    time.sleep(1)
    app.run(host="0.0.0.0", port=5001, threaded=True)
