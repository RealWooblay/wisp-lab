# concepts.md — the technical knowledge (your textbook)

The conceptual backbone from our sessions. Re-read this; rewrite bits in your
own words as they click. Tools change; these ideas don't.

---

## 1. The machine-vision model landscape

Vision models sort by **what they output**:

| Family | Answers | Output | WISP use |
|---|---|---|---|
| Classification | "what is this image?" | one label | — |
| **Detection** (YOLO) | "what's where?" | boxes + labels | objects in view |
| Segmentation | "which exact pixels?" | masks | precise outlines |
| **Pose / keypoints** | "where are the joints?" | skeleton / landmarks | **head, eye, hand tracking** |
| **Vision-Language (VLM)** | "describe / reason" | words | "what plant / recipe is this?" |

Pick by: **speed** (per-frame vs per-query), **where it runs** (device vs cloud),
**specialist vs generalist**, **output type** (coordinates vs words).

## 2. Specialist vs generalist (why not just use GPT-4V)

- A **fine-tuned specialist** beats a giant VLM **at its one narrow task** — and only there — because: (a) capacity concentrated on one job, (b) trained on more of *your* specific data, (c) architecture built for the output (fast coordinates). It's also ~100× smaller/faster and runs locally.
- A **generalist (GPT-4V)** wins at **breadth, novelty, open-ended reasoning.**
- **Fine-tuning adds knowledge only when the generalist lacks it** (rare/novel domains). For common things the generalist already knows, fine-tuning buys **speed + locality**, not new knowledge. (Same as the text-LLM intuition: fine-tuning shapes *form*; knowledge comes from pretraining — but for vision on novel tasks, fine-tuning genuinely teaches new capability.)
- **The size law:** knowledge lives in parameters → "knows everything" *requires* huge size → huge size *can't* run fast on an edge device. So "knows everything + fast + local" is physically impossible. On the device you're *forced* to specialize. (GPT-4V ≈ 1.8T params on a GPU rack; YOLOv8n ≈ 3.2M params, 15ms on the Jetson — ~500,000× difference.)

## 3. Cloud vs edge — why WISP must be local

Four reasons cloud fails for real-time on-device:
1. **Latency** — cloud round-trip is 0.5–3s; the Jetson is 15ms. *For real-time, latency IS quality* — a brilliant answer that arrives too late is worthless.
2. **Offline** — WISP must work without internet.
3. **Privacy** — weak as a *purchase* driver (people trade it for convenience), but real for in-home cameras.
4. **Cost** — per-frame cloud calls at scale = impossible.

Key mental models:
- **Bottleneck: information or capability?** More info changes the next move → keep probing. You already know the answer and lack a tool/part → stop, go get the tool.
- **The physics-protected tier:** anything that *acts in real time on what it sees* (self-driving brake, laser weeder, WISP's projection loop) **must be local** — speed of light + jitter set a floor no network "solves." Starlink fixes the *pipe*, not the model's *thinking time*, and not the round-trip floor.
- **Two diverging tracks, both growing:** frontier cloud VLMs (max capability) + tiny edge models (real-time, private, offline). Durable architecture = **hybrid** (fast local reflexes + occasional bigger model, local or cloud).
- **Future-proof = the judgment to split tasks by tier.** The real-time/embodied tier is permanent; the specific tools (YOLOv8, TensorRT, JetPack) churn.

## 4. How a flat display creates depth (the depth-perception science)

- **Your retina is 2D.** Even for real scenes, the image on it is flat — your **brain reconstructs depth from cues.** Depth is perceived, not received.
- **Pictorial cues work from any flat image:** occlusion (overlap), perspective (converging lines), relative size, shading, texture gradient. This is why **photos, film, and paintings look 3D** despite being flat at one distance.
- **Motion parallax** = the cue head-tracking *adds*: as you move, near things shift more than far things. Turns "a flat picture with depth" into "a window you can look around." Photos lack it.
- **Hard limits a flat wall CANNOT fake:** **stereopsis** (two eyes, different angles → a flat wall gives both the same image → "flat") and **accommodation/vergence** (focus & eye-convergence fixed at the wall → "flat").
- **Consequence:** the illusion is strongest **at a distance + in motion** (parallax dominates, stereo weak); it **breaks up close + holding still** (stereo wins, says "flat wall"). WISP works as *ambient depth at a distance*, not a solid object you inspect at arm's length.

## 5. Projection reality (WISP's honest ceiling)

- **Not a hologram.** 2D **additive light** on a flat surface. A perceptual 3D illusion for **one tracked, moving viewer**. Someone beside you sees a smear.
- **No true black** (black = the wall), washed by ambient light → looks best in a **dim room**. Translucent/glowing, not solid.
- Content "behind the wall" (a recessed window) is robust; content "in front" **clips at the projection edges** and breaks.
- **You cannot evaluate projected light with a screen simulation** — a picture of a projection on a flat emissive screen is still just a screen. The screen sim only validates the **geometry/math**; the *look* must be judged with a **real projector on a real wall.** (Hard lesson learned the long way.)

## 6. Off-axis (asymmetric) frustum — the parallax math

The core of *all* view-dependent rendering (AR/VR/WISP). The screen is a fixed
rectangle (a window); the eye is at an arbitrary point; the view frustum
**shears** so its apex is the eye and its near rectangle matches the screen
edges. In `prototypes/parallax/index.html`, `applyParallaxProjection()`:
```
left   = (-W/2 - eyeX) * near/eyeZ
right  = ( W/2 - eyeX) * near/eyeZ
bottom = (-H/2 - eyeY) * near/eyeZ
top    = ( H/2 - eyeY) * near/eyeZ
```

## 7. Edge optimization (from the GPU work)

- **Precision pyramid:** FP32 → FP16 → INT8 → INT4. Each step ~halves size, ~doubles speed, costs some accuracy.
- **TensorRT** recompiles a model into an engine tuned for *this exact GPU* (fuses ops, picks fastest kernels). ~2.7× over PyTorch on yolov8n (small models are overhead-bound, so the gain is modest; bigger models gain more).
- **Latency budget:** at any moment ONE thing is the limit. After TensorRT we became **camera-bound** (IMX708 = 14fps), so faster inference bought no FPS — the bottleneck moved.

---

## Things to learn next (Stage 1+)
- **3D-from-2D:** recover head `x,y` from eye keypoints + `z` (depth) from inter-eye pixel distance vs known ~63mm IPD.
- **Camera intrinsics / calibration** (focal length, distortion).
- **Pose estimation** (keypoint models).
- **Coordinate-frame transforms** — camera space → screen/world space (where the hard bugs live).
- **Streaming** head pose Jetson → browser (WebSocket).
- **Hand keypoints** for interaction; later **projector-camera calibration**.
