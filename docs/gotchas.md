# gotchas.md — "I will never forget this"

Hard-won lessons. Each one cost real time. Add to this every session.

---

## Jetson / camera

- **CSI cameras do NOT hot-plug.** Plug in the IMX708 → `sudo reboot`. The driver
  only probes the sensor at boot. No reboot = `/dev/video0` never appears.
- **Ribbon orientation matters and is silent when wrong.** Contacts/blue stripe
  must face the right way. Wrong way = no error, just "No cameras available."
  Take a photo before you change it.
- **IMX708 has ONE sensor mode: `4608x2592 @ 14fps`.** Your GStreamer caps MUST
  match. Requesting 30fps → `Frame Rate specified is greater than supported`.
- **`nvargus` daemon gets wedged** if you kill camera apps repeatedly. Symptom:
  `nvbuf_utils: dmabuf_fd -1 mapped entry NOT found`. No app-level retry fixes
  it. Fix: `sudo systemctl restart nvargus-daemon` (or reboot).

## Python / dependency hell

- **`torch X+cpu` + a torchvision version that doesn't exist on PyPI = they came
  as a matched pair from somewhere else.** Don't break the pair by swapping only
  one. Find the provenance of a broken state before debugging it.
- **NVIDIA's Jetson torch needs exact partner libs:** match cuDNN major version
  (wheel `nv24.08` → cuDNN 9) and supply `libcusparseLt` separately.
- **torchvision must be ABI-matched to torch.** Prebuilt PyPI wheels fail against
  NVIDIA's torch with `operator torchvision::nms does not exist`. Build from source.
- **pip rejects renamed wheels.** Keep the full canonical filename
  (`torch-2.5.0a0+...-cp310-cp310-linux_aarch64.whl`), don't shorten it.
- **A source `.egg` install can be shadowed** by a leftover pip flat dir of the
  same package. Delete the flat dir so the new build actually loads.

## Shell / ops

- **`pkill -f cam_yolo_live.py` kills your own SSH command** — the pattern matches
  the command string running it. Filter on the process name instead:
  `ps -eo pid,comm,args | awk '$2 ~ /^python/ && /cam_yolo_live/ {print $1}'`.
- **The Jetson has no outbound internet** over USB-direct. Download wheels/libs on
  the Mac, push with `scp`. `pip install <name>` from the Jetson will hang on DNS.

## Meta (the most valuable ones)

- **Ask: is my bottleneck _information_ or _capability_?** If more info changes the
  next move → keep probing. If you already know the answer and lack a tool/part →
  stop probing, go get the tool. (Cost me ~4 motor-test reruns to learn this.)
- **Demo every milestone, then journal it BEFORE changing anything.** We lost
  ~6 working states tonight by improving them before recording how they worked.
