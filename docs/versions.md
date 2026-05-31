# versions.md — the reproducibility file

**The test of this file:** if I wiped the Jetson and reflashed, could I rebuild
the working GPU stack using only what's written here? If yes, I own it.

Last verified: **2026-05-26**, YOLOv8n on GPU @ **31.6 FPS** (imgsz=640).

---

## Hardware

| | |
|---|---|
| Board | NVIDIA Jetson Orin Nano **Super** (Engineering Reference Dev Kit) |
| Compute | 1024 CUDA cores + 32 Tensor cores, 6-core ARM Cortex-A78AE |
| RAM | 7.4 GiB (unified — shared CPU+GPU) |
| Disk | 468 GB (24 GB used) |
| Power mode | **25 W / MAXN_SUPER** (`nvpmodel -m 1`) — max performance |
| Camera | **IMX708** (Raspberry Pi Camera Module 3), CSI, on **CAM0** |

**IMX708 quirk:** sensor exposes exactly ONE mode — `4608x2592 @ 14fps`. Any
GStreamer pipeline MUST request that; asking for 1280x720@30 fails.

---

## System stack (shipped with JetPack — do not touch)

| Component | Version |
|---|---|
| JetPack / L4T | R36.4.7 (`/etc/nv_tegra_release`) |
| CUDA | 12.6.11 |
| cuDNN | 9.3.0.75 |
| TensorRT | 10.3.0 |
| Python | 3.10.12 |
| OpenCV (cv2) | 4.5.4 (GStreamer support: YES) |

---

## The hand-built GPU stack (this is the fragile part)

The Jetson has **no internet** (USB-direct only), and the old community wheel
index `jetson-ai-lab.com` is **DEAD**. Everything below was downloaded on the
Mac and pushed over scp.

### 1. GPU PyTorch — `torch 2.5.0a0+nv24.08`
- Source: `https://developer.download.nvidia.com/compute/redist/jp/v61/pytorch/torch-2.5.0a0+872d972e41.nv24.08.17622132-cp310-cp310-linux_aarch64.whl`
- Install: `python3 -m pip install --user --no-deps --force-reinstall <wheel>`
- **Keep the canonical filename** — pip rejects renamed wheels.
- Why this one: `nv24.08` needs cuDNN 9 (we have 9.3) ✓. The older `nv24.07`
  wants cuDNN 8 ✗.

### 2. `libcusparseLt 0.6.3.2` — torch 2.5's missing dependency
- JetPack 6.4 does NOT ship this. Without it: `ImportError: libcusparseLt.so.0`.
- Source: `https://developer.download.nvidia.com/compute/cusparselt/redist/libcusparse_lt/linux-aarch64/libcusparse_lt-linux-aarch64-0.6.3.2-archive.tar.xz`
- Extracted to `~/libcusparselt/`
- Made findable (added to `~/.bashrc`):
  `export LD_LIBRARY_PATH=$HOME/libcusparselt/lib:$LD_LIBRARY_PATH`

### 3. torchvision 0.20.0 — **BUILT FROM SOURCE**
- PyPI/prebuilt wheels give `RuntimeError: operator torchvision::nms does not
  exist` — ABI mismatch against NVIDIA's torch build.
- Source: `https://github.com/pytorch/vision` tag `v0.20.0`
- Build (on the Jetson, ~30 min):
  ```bash
  cd ~/vision-0.20.0
  export LD_LIBRARY_PATH=$HOME/libcusparselt/lib:$LD_LIBRARY_PATH
  export BUILD_VERSION=0.20.0 FORCE_CUDA=1
  python3 setup.py install --user
  ```
- **Then delete the pip-installed flat dir** so the source .egg wins:
  `rm -rf ~/.local/lib/python3.10/site-packages/torchvision`

### 4. ultralytics 8.4.23 + Flask 3.1.3
- ultralytics was already present.
- Flask installed offline from Mac-downloaded aarch64 wheels (no Jetson internet).

---

## Verified result
```
torch 2.5.0a0+nv24.08   cuda: True   device: Orin   cuda runtime: 12.6
torchvision 0.20.0      NMS: works
YOLOv8n imgsz=640 on GPU: 31.6 ms/frame  ≈  31.6 FPS
```
CPU baseline for the same model was ~1 FPS → GPU is a ~30× speedup.
