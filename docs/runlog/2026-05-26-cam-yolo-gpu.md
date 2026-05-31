# 2026-05-26 — live camera + YOLO on GPU

**Goal:** get the IMX708 camera streaming to the Mac with real-time object
detection running on the Jetson GPU.

**Outcome:** ✅ GPU YOLOv8n benchmarked at **31.6 FPS**. Web app written and
deployed. One step left to *see* it live (nvargus daemon restart — see below).

---

## What worked, in order

1. **Camera detection.** `/dev/video0` missing at first. Cause: CSI ribbon
   orientation + CSI cameras don't hot-plug. Fixed orientation, rebooted →
   kernel detected IMX708 (`nv_imx708` module loaded, `/dev/video0` appeared).

2. **GStreamer pipeline.** First grab failed: `Frame Rate specified is greater
   than supported`. The IMX708 only offers `4608x2592 @ 14fps`. Rewrote the
   pipeline to request that native mode, then hardware-downscale to 960x540 via
   `nvvidconv`. Worked.

3. **Flask install.** Missing, and Jetson has no internet. Downloaded aarch64
   wheels on the Mac, scp'd over, installed offline.

4. **First run = CPU, ~1 FPS.** `torch 2.10.0+cpu` was installed (CPU-only build
   from the now-dead jetson-ai-lab index). Camera live, but YOLO crawling.

5. **GPU PyTorch — the dependency saga.** (Full detail in `docs/versions.md`.)
   - `nv24.08` wheel → `ImportError: libcusparseLt.so.0` (not shipped in JP6.4)
   - `nv24.07` wheel → `libcudnn.so.8` missing (we have cuDNN 9, not 8)
   - back to `nv24.08` + downloaded `libcusparseLt 0.6.3.2` separately → **torch
     GPU works**, `cuda available: True`, device `Orin`
   - torchvision then broke: `operator torchvision::nms does not exist` (ABI
     mismatch). PyPI wheels didn't fix it.
   - **built torchvision 0.20.0 from source** against NVIDIA torch (~30 min
     compile) → NMS works → **YOLO on GPU = 31.6 FPS** ✓

---

## Still open

- **Live view blocked by `nvargus` daemon wedge** from repeatedly killing the app
  during debugging. Symptom: `nvbuf_utils: dmabuf_fd -1 mapped entry NOT found`.
  Fix (needs sudo on the Jetson): `sudo systemctl restart nvargus-daemon`,
  then relaunch the app. The 31.6 FPS benchmark already PROVES the GPU path —
  this is just clearing stuck camera state.

---

## Lessons → moved to gotchas.md
- bottleneck = information vs capability (the motor-test trap earlier in the day)
- find the provenance of a broken state before debugging it
- demo + journal before changing anything (we lost ~6 working states)
- `pkill -f` self-kill; renamed wheels; source-egg shadowed by pip flat dir
