# glossary.md — terms in my own words

Definitions I actually understand beat definitions I copied. These are starter
drafts (written with the agent) — **rewrite each in your own words** as it clicks.

---

### The stack from silicon up
- **SoC** — System on a Chip. CPU + GPU + memory + camera processor, all on one
  piece of silicon. The Jetson is an SoC, not a CPU with a separate graphics card.
- **CUDA** — NVIDIA's system for running code on the GPU instead of the CPU. The
  GPU has 1000+ tiny cores; CUDA spreads math across all of them at once.
- **CUDA core** — one of the many small parallel workers on the GPU. Great at doing
  the same simple math on lots of data simultaneously (exactly what neural nets are).
- **Tensor core** — specialized GPU unit that does matrix-multiply (the core
  operation of a neural net) extremely fast, especially at low precision.
- **cuDNN** — NVIDIA library of pre-optimized neural-net building blocks
  (convolutions, etc.) that runs on CUDA. PyTorch calls into it.
- **DLA** — Deep Learning Accelerator. A separate fixed-function chip on the Jetson
  just for inference, frees up the GPU. (Not used yet.)
- **ISP** — Image Signal Processor. Hardware that turns raw camera sensor data into
  a usable image (debayering, exposure, white balance). Lives on the SoC.

### Camera / video
- **CSI / MIPI** — the fast ribbon-cable camera interface wired straight into the
  SoC's ISP. Lower latency than USB. The IMX708 uses this.
- **GStreamer** — a pipeline system for video: chain elements with `!` and data
  flows through (`source ! convert ! sink`). How we get camera frames into Python.
- **nvarguscamerasrc** — NVIDIA's GStreamer source element that pulls frames from a
  CSI camera through the ISP. The first stage of our pipeline.
- **NVMM** — NVIDIA Multimedia Memory. GPU-side memory that lets video stay on the
  GPU without copying back to CPU ("zero-copy"). Faster.
- **MJPEG** — Motion JPEG. A "video" stream that's just a rapid sequence of JPEG
  images. Dead simple to stream over HTTP — how the browser sees the feed.

### Models / inference
- **Inference** — running a trained model to get a prediction (vs *training*, which
  is teaching it). On the Jetson we do inference.
- **YOLO** — "You Only Look Once." A fast object-detection model family — draws
  boxes + labels around things in one pass. `yolov8n` = the nano (smallest) variant.
- **TensorRT** — NVIDIA's compiler that takes a model and rebuilds it into a
  hyper-optimized engine for this exact GPU. The fast path; ~2× over plain PyTorch.
- **ONNX** — a portable model file format. The middle step: PyTorch → ONNX → TensorRT.
- **Precision (FP32/FP16/INT8)** — how many bits represent each number. Fewer bits
  = smaller + faster + slightly less accurate. The "precision pyramid."
- **Quantization** — converting a model to lower precision (e.g. FP32 → INT8) for
  speed, with a calibration step to limit accuracy loss.
- **NMS** — Non-Max Suppression. Cleanup step that merges overlapping duplicate
  boxes into one. The torchvision operator that broke during install.
- **ABI** — Application Binary Interface. The low-level contract between compiled
  libraries. torch and torchvision must share the same ABI or they won't link —
  the root of tonight's `nms does not exist` error.

### Ops
- **JetPack** — NVIDIA's bundle: the OS (L4T) + CUDA + cuDNN + TensorRT, versioned
  together. "JetPack 6.4" pins all of them.
- **L4T** — Linux for Tegra. NVIDIA's Ubuntu fork for Jetson.
- **power mode / nvpmodel** — caps how much power/clock the board uses. MAXN_SUPER
  = unlocked. Lower modes save power but throttle compute.
- **wheel (.whl)** — a pre-built Python package. `pip install` unpacks it. Must
  match Python version + CPU architecture (here: cp310 + aarch64).
