# wisp-lab

My workbench for learning embedded AI on the NVIDIA Jetson — and the foundation
for **WISP** (AI projector startup). Code + lab notebook in one place.

> **Rule #1:** Demo every milestone, then write down what made it work *before
> changing anything.* If I can rebuild the system from `docs/versions.md` alone,
> I own it. If I can't, I got lucky.

---

## Where this is right now

| Thing | Status |
|---|---|
| Jetson Orin Nano Super, JetPack 6.4.7 | ✅ working |
| IMX708 CSI camera | ✅ detected, streaming |
| GPU PyTorch (CUDA 12.6) | ✅ working (hand-installed — see `docs/versions.md`) |
| YOLOv8n object detection on GPU | ✅ **benchmarked 31.6 FPS** @ imgsz=640 |
| Live web stream (`src/cam_yolo_live.py`) | ✅ runs — view at `http://192.168.55.1:5000` |

**This is scaffolding, not foundation.** The GPU stack is a hand-built hack
(source-compiled torchvision, manually placed `.so`, an `LD_LIBRARY_PATH`
bandaid). It runs, but it will not survive a reflash. `docs/versions.md` is what
makes it reproducible. Containerizing it properly is a later milestone.

---

## The learning journey

The app in `src/` is the textbook. We don't learn concepts in the abstract — we
understand and extend one real thing.

1. **See it** — view the live feed in a browser
2. **Own it** — this repo (done)
3. **Understand it** — read `cam_yolo_live.py` line by line; each line is a concept
4. **Extend it** — latency overlay → TensorRT export → INT8 → model swaps
5. **Aim it at WISP** — face/head tracking → projector + head-tracked parallax

North star: **WISP** — a ceramic AI lantern with camera + mic + speaker + laser
projector, all on-device, no cloud. First capability it needs is real-time
vision I fully control. That's what this repo is building toward.

---

## Repo layout

```
src/                    the code that runs on the Jetson
  cam_yolo_live.py      live camera + YOLOv8n + MJPEG web stream
docs/
  versions.md           EVERY pinned version + URL that works (reproducibility gold)
  glossary.md           every term, defined in my own words
  gotchas.md            "I will never forget this" — hard-won lessons
  runlog/               one dated file per session: tried / broke / fixed
```

## How it runs (today)

The Jetson is reached over USB-direct at `192.168.55.1` (user `wooblay`).
The app needs `libcusparseLt` on the library path:

```bash
# on the Jetson
LD_LIBRARY_PATH=$HOME/libcusparselt/lib:$LD_LIBRARY_PATH python3 ~/cam_yolo_live.py
# then open http://192.168.55.1:5000 on the Mac
```

See `docs/versions.md` for the full stack and `docs/runlog/` for how it got here.
