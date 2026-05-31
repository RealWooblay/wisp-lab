# measurements.md — every number, with the conditions

Don't trust feel. Write down what you measured and the conditions you measured it
under. Numbers without conditions are noise.

---

## YOLOv8n object detection — imgsz=640, Orin Nano Super (25W / MAXN_SUPER)

| Runtime | Precision | ms / inference | inferences/sec | notes |
|---|---|---|---|---|
| PyTorch (CPU) | FP32 | ~1000 | ~1 | first run, GPU not engaged — "slow af" |
| PyTorch (CUDA) | FP32 | 31.6 isolated / ~40 live | ~25–31 | the `.pt` model on GPU |
| **TensorRT** | **FP16** | **14.8 isolated** | **~68** | the `.engine` — **~2.7× over live PyTorch** |

Measured: 2026-05-26.

### Honest note on the TensorRT gain
Only ~2.7×, not the "4–8×" rule-of-thumb — because `yolov8n` is so small that
fixed overhead (image resize, NMS, data movement) dominates, and TensorRT can't
shrink that. On bigger models where compute dominates, the relative gain is larger.

---

## The bottleneck shifted after TensorRT (the key lesson)

- IMX708 camera max = **14 fps** → one frame every ~71 ms.
- Inference at 14.8 ms is **far inside** that 71 ms budget.
- Result: the system is now **camera-bound**, not compute-bound.
- Live FPS sits ~14 no matter how fast inference gets.
- **~56 ms/frame of idle GPU time = free headroom** → can run a bigger, more
  accurate model (e.g. yolov8m) and still hold 14 fps. That's the next experiment.

> Latency-budget rule: at any moment ONE thing is the limit. Find it before
> optimizing anything else.
