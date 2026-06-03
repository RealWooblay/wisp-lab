# Research log — head-tracked parallax (WISP core effect)

A living document. We add to it as the experiment progresses: what we tried,
what we saw, screenshots/video, findings, open questions. This is the WISP
"magic" — view-dependent 3D rendering driven by the viewer's head.

---

## Goal / hypothesis

If we track the viewer's eye position and render a 3D scene with a matching
**off-axis projection**, a flat display becomes a convincing window into a 3D
world — and the illusion holds as the viewer moves. (Johnny Lee, 2007, proved
this on a plain monitor with Wii head-tracking.) If it holds on a screen, the
next question is whether it survives **projection** onto a real surface.

## Architecture (mirrors real WISP)

- **Jetson = perception** (edge / real-time tier): camera → eye position → stream.
- **Browser = the "projector"** (stand-in): Three.js renders the parallax scene.
- **Screen stands in for the projector** while prototyping — zero projector hardware.

## Build stages

| Stage | What | Real-work concept | Status |
|---|---|---|---|
| 0 | Render driven by **mouse** | off-axis frustum math | ✅ built |
| 1 | **Head tracking** on Jetson | 3D-from-2D (recover head x,y,z from image) | next |
| 2 | **Connect** mouse → real head | camera→screen coordinate alignment | — |
| 3 | **Hand tracking** for interaction | keypoints → scene interaction | — |

---

## Stage 0 — mouse-driven parallax  *(2026-05-26)*

`prototypes/parallax/index.html`. Self-contained Three.js page; mouse = eye x/y,
scroll = eye depth (z). The core is `applyParallaxProjection()` — an asymmetric
view frustum whose apex is the eye and whose near rectangle is the screen edges.

**Status:** working. Objects at different depths shift relative to each other as
the eye moves → readable depth.

### Captures
- `prototypes/parallax/captures/stage0-screen.png` — idealized screen mode _(to add)_
- `prototypes/parallax/captures/stage0-projector.png` — projector-sim mode _(to add)_
- `prototypes/parallax/captures/stage0-parallax.mov` — short clip showing motion _(to add)_

---

## Finding — screen vs projector (important)

The parallax **geometry is identical** regardless of display. But a projector
differs from a screen in two ways that affect whether the illusion survives:

1. **Photometric washout.** Screen = emissive → perfect blacks, full contrast.
   Projector = *additive light on a surface* → no true black (black = the wall),
   lower contrast, color shifted by the surface, washed by ambient light.
   **The emissive screen flatters the effect** — it looks punchier here than it
   will on a wall.
2. **Surface geometry.** Screen is flat and square to the viewer. Projector
   throws onto an arbitrary surface at an angle → the image must be *warped to
   the surface* (projection mapping) **in addition to** the parallax warp.
   Two transforms, not one.

**Projector-sim mode** (press `P`) approximates #1 only: dim wall background,
lifted blacks, reduced contrast, edge vignette. It is an *approximation* — an
emissive screen cannot truly reproduce additive-light-with-no-black.

> **Open question (needs a real projector to answer):** does the depth illusion
> survive the contrast loss and surface texture of real projection? Schedule a
> test with an actual short-throw projector on a matte wall.

---

## Open questions / TODO
- Camera framerate: IMX708 gives only **14 fps** — likely too slow for *smooth*
  head tracking (want 30–60). Test; consider a faster sensor mode or prediction.
- Latency budget for the full loop (capture → head pose → stream → render).
- How much does a visible frame/edge help the illusion? (projector has no bezel)
- Depth (z / lean-in) estimation accuracy from a single camera.
