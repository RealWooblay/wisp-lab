# Research log — head-tracked parallax (WISP core effect)

A living document. The WISP "magic" — view-dependent 3D rendering driven by the
viewer's head. See `docs/concepts.md` for the underlying theory.

---

## Setup (important)

- **The Jetson is the real target.** All tracking/inference runs there.
- **The development machine is a mirror** — it reflects the code and serves as
  the prototyping screen for observing what's running on the Jetson.
- The screen demos are for developing the **math/algorithm**, NOT for judging the
  projected look (see finding below).

## Goal / hypothesis

Track the viewer's eye position, render a 3D scene with a matching **off-axis
projection**, and a flat display becomes a window into 3D that holds as the
viewer moves (Johnny Lee, 2007). Open question: does it survive real projection.

## Build stages

| Stage | What | Real-work concept | Status |
|---|---|---|---|
| 0 | Render driven by **mouse** | off-axis frustum math | ✅ done |
| 1 | **Head / eye / hand tracking** on Jetson | pose model + 3D-from-2D | ✅ built — `runtime/wisp_perception.py` |
| 2 | **Connect** real head → render | head drives the off-axis parallax | ✅ built — `runtime/wisp.html` |
| 3 | **Hand interaction** | wrist keypoints → cursor + highlight | ✅ built — `runtime/wisp.html` |
| 4 | **Real projector** on a wall | calibration + look-test | ⏳ needs hardware |

**The full software runtime is built and deployed** (perception + planner +
renderer + projection-mapping framework). See `runtime/README.md`. Live visual
validation (a person in frame) and the projector calibration are the remaining
hardware-time steps.

---

## Stage 0 — done

`prototypes/parallax/index.html`. Off-axis frustum parallax, mouse = eye.
Iterated through: floating shapes → recessed room → projector-sim → and finally a
**clean dark-wall projection sim** (glowing objects on a receding ground, soft
edges feathering into the wall). Toggles: `F` freeze, `O` projection on/off.

**What it proved:** the parallax *math* works. **What it can't prove:** how real
projected light looks (see finding).

---

## Findings

### Screen vs projector
- Parallax **geometry** is identical on any display.
- A projector adds: **photometric washout** (no true black, additive light,
  ambient-washed, best in a dim room) and **surface-warp** (project onto angled/
  non-flat surfaces). The emissive screen **flatters** the effect.

### You cannot fake projected light on a screen  *(hard lesson)*
A picture of a projection, shown on a flat emissive screen, is still a screen —
it carries the screen's own limits. The screen sim is only valid for the
**math**; the **look/feel must be judged on a real projector + real wall.**

### Why it looks 3D at all (depth perception)
Pictorial cues (occlusion, perspective, size, shading) give depth in any flat
image — same as a photo. Head-tracking adds **motion parallax** (the window cue).
**Hard limits:** stereopsis + focus can't be faked on a flat wall → effect is
strong at a distance / in motion, breaks up close / holding still. Full theory in
`docs/concepts.md` §4–5.

---

## Stage 1–3 — BUILT ✅  (see `runtime/`)

Done as planned below — perception, head-driven render, hand interaction,
planner, and the projection-mapping framework are all built and deployed.
Original plan, kept as the record:

1. **Pose model** — get `yolov8n-pose` onto the Jetson (download on Mac → scp,
   since the Jetson has no internet). It gives eyes/nose/ears (head) + wrists (hands).
2. **See it tracking** — run pose on the live camera, draw keypoints, stream to
   the browser. Watch your own eyes/nose/wrists tracked in real time.
3. **3D head estimation** — `x,y` from eye keypoints; **`z` (depth) from the pixel
   distance between the eyes vs the known ~63mm spacing.** The real CV work.
4. **Connect to parallax** — stream head pose → the demo uses your head, not the mouse.
5. **Hands** — wrist keypoints → interaction (later, a hand-specific model for fingers).

(Optionally TensorRT-export the pose model later, as we did for detection, once
tracking is confirmed working.)

## Open questions / TODO
- IMX708 is **14 fps** — likely too slow for *smooth* head tracking (want 30–60);
  test, consider a faster sensor mode or motion prediction.
- Full-loop latency budget (capture → pose → 3D estimate → stream → render).
- Depth (z) estimation accuracy from a single camera.
- Eventually: a real short-throw projector to test the actual look.
