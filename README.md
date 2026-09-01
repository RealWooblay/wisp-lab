# WISP Lab

An embedded-AI workbench for a local spatial computer: real-time perception on
an NVIDIA Jetson, head-tracked rendering, hand interaction, and projection
mapping for ordinary surfaces.

WISP is the product direction behind the lab—a camera, microphone, speaker,
projector, and local compute packaged as a home object. This repository keeps
the working runtime, reproducible device notes, experiments, and product
concept together.

## Current system

```text
IMX708 camera
  -> YOLO pose inference on Jetson
  -> head + hand state over Server-Sent Events
  -> planner and head-tracked renderer
  -> corner-pin projection mapping
  -> physical surface
```

| Capability | Current result |
| --- | --- |
| Jetson Orin Nano Super + JetPack 6.4.7 | Running |
| IMX708 CSI camera | Streaming |
| YOLOv8n detection with TensorRT FP16 | 31.6 FPS at 640px |
| YOLOv8n-pose perception | About 8.6 FPS |
| Head-tracked parallax renderer | Implemented |
| Hand cursor and object highlighting | Implemented |
| Four-corner projection calibration | Implemented |

## Repository map

| Path | Purpose |
| --- | --- |
| [`runtime/`](runtime/) | Perception service, planner, renderer, and projection mapping |
| [`src/`](src/) | Earlier live-camera and TensorRT detection milestone |
| [`docs/`](docs/) | Version pins, measurements, concepts, gotchas, and dated run logs |
| [`prototypes/`](prototypes/) | Browser-based interaction and parallax experiments |
| [`site/`](site/) | Product concept and use-case presentation |

The runtime separates perception from presentation. The Jetson publishes a
small stream of head and hand state; the renderer owns interaction, scene
planning, and projection calibration. That boundary makes the visual layer
testable without the camera and lets the perception implementation evolve
independently.

## Run the spatial runtime

On the Jetson:

```bash
export WISP_MODEL_PATH="$HOME/yolov8n-pose.pt"
LD_LIBRARY_PATH="$HOME/libcusparselt/lib:$LD_LIBRARY_PATH" \
  python3 runtime/wisp_perception.py
```

Then open the device-served renderer at `http://<jetson-host>:5001/wisp`.
The camera debugger, state stream, and health check are available at
`/camera`, `/state`, and `/health` respectively.

See [`runtime/README.md`](runtime/README.md) for controls and verification, and
[`docs/versions.md`](docs/versions.md) for the pinned Jetson software stack.

## Engineering approach

- Benchmark each hardware milestone and record the environment that produced it.
- Keep model binaries and generated engines outside Git; their paths are supplied
  through `WISP_MODEL_PATH`.
- Fail visibly when the camera or model cannot start—there is no fake success path.
- Preserve honest constraints: depth is estimated from pose geometry, the current
  camera mode is limited to 14 FPS, and final calibration requires a projector.

## Next technical milestones

1. Calibrate camera intrinsics and replace approximate depth constants.
2. Export the pose model to TensorRT and measure end-to-end motion latency.
3. Add prediction/smoothing appropriate for head-tracked projection.
4. Calibrate projector-camera geometry on a physical surface.
5. Package the Jetson runtime reproducibly instead of relying on a hand-built host.
