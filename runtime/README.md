# WISP runtime — local spatial runtime (software)

The software half of WISP, built to be **ready for the projector before the
projector arrives**. Everything here runs on the Jetson + a screen as a stand-in
output; when the real projector is connected, you swap the display and calibrate.

## Architecture

```
  EYES                      DIRECTOR                 PROJECTOR
  perception        →       planner          →       renderer + projection map
  (wisp_perception.py)      (in wisp.html)           (wisp.html)
  camera → pose →           idle / engaged /         off-axis head-tracked
  head + hands (3D)         interacting              parallax  +  corner-pin warp
        │                                                   ▲
        └──────────────  SSE /state (30 Hz)  ───────────────┘
```

- **`wisp_perception.py`** (Jetson) — the Eyes. Opens the IMX708, runs
  YOLOv8n-pose on the GPU, derives **head** (x, y, z) and **hands** (wrists),
  and streams them as Server-Sent Events. Also serves a debug video + the UI.
- **`wisp.html`** (renderer) — the Director + Projector. Consumes the stream,
  drives a head-tracked off-axis parallax scene, shows a hand cursor + object
  highlighting, runs a simple planner, and includes the projection-mapping
  (corner-pin / keystone) framework for the real projector.

## Run it

On the Jetson (note the `LD_LIBRARY_PATH` — required for the GPU torch):

```bash
export WISP_MODEL_PATH="$HOME/yolov8n-pose.pt"
LD_LIBRARY_PATH="$HOME/libcusparselt/lib:$LD_LIBRARY_PATH" \
  python3 runtime/wisp_perception.py
```

Then on the Mac, open the device-served UI (same-origin, no CORS):

```
http://<jetson-host>:5001/wisp        ← the experience (renderer)
http://<jetson-host>:5001/camera      ← debug feed: pose skeleton + head/hand markers
http://<jetson-host>:5001/state       ← raw SSE perception stream (JSON)
http://<jetson-host>:5001/health      ← status JSON
```

(The renderer also runs from a local copy of `wisp.html`. Pass the Jetson state
endpoint as `?state=http://<jetson-host>:5001/state`; CORS is enabled. It falls
back to **mouse control** when no head is tracked.)

## Controls (in the renderer)

- **Move** — your head drives the view (or the mouse as fallback).
- **Hand** — raise a hand; a cursor appears and the nearest object highlights.
- **M** — toggle projection-mapping calibration; drag the 4 corners to keystone
  the output onto a surface. Saved to `localStorage`.
- **R** — reset the mapping to identity.

## Stage status

| Stage | What | Status |
|---|---|---|
| 1 | Perception — head/eye/hand tracking, 3D head estimate | ✅ built, deployed, streaming (~8.6 FPS pose) |
| 2 | Head-driven render — parallax follows the real head | ✅ built (full visual check needs a person in frame) |
| 3 | Hand interaction — cursor + object highlight | ✅ built |
| — | Planner — idle / engaged / interacting / mouse | ✅ built |
| — | Projection-mapping framework — corner-pin keystone | ✅ built (calibration is done against the real surface) |
| — | First experience — recessed dark-room scene | ✅ built |

## Honest limits / what still needs the hardware

- **Depth (z) is approximate.** It's derived from the pixel distance between the
  eyes vs a ~63 mm interpupillary assumption. Reliable x/y; usable z. Real
  accuracy needs **camera intrinsic calibration** (focal length / distortion).
  Tunable constants are at the top of `wisp_perception.py` (`EYE_PX_*`, `EYE_Z_*`).
- **Camera is 14 fps** (IMX708 single mode) → head tracking is usable but not
  buttery. A faster sensor mode or motion prediction is a later improvement.
- **Pose runs in PyTorch (~8.6 FPS).** TensorRT-exporting `yolov8n-pose` (as we
  did for detection) would speed it up — a clean optimization step.
- **Projector-camera calibration + look tuning** can only be done with the real
  projector on a real wall. The corner-pin framework and the renderer are ready
  for it; the actual mapping + brightness/contrast are dialed in on the hardware.

## Verify (with a person)

1. Open `/camera` — stand in frame; you should see the pose skeleton lock onto
   you, with the head/hand readout updating in the overlay bar.
2. Open `/wisp` — the HUD should read **connected** and **ENGAGED** when your
   head is tracked; move side to side and the room should shift (parallax).
   Raise a hand → cursor + nearest-object highlight (**INTERACTING**).
