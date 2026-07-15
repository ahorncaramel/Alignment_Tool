# Specification — Calcium Imaging → CYP11B2 IHC Alignment Tool (v1)

## 0. Purpose of this document

This is an implementation brief for a coding-focused developer (human or LLM) who was **not** part of the design conversation. It states what to build, how it must behave, and — importantly — *why* certain choices were made, so that the implementer does not "improve" the design in ways that break its scientific intent. Where a rationale is given, treat it as a constraint, not a suggestion.

The tool is a research instrument used by a single scientist on a single workstation. It is **not** a product for many users. Favour clarity, determinism, and inspectability over generality, configurability, or architectural sophistication. Do not over-engineer.

---

## 1. Scientific context (background, not requirements)

The user performs live calcium imaging on fresh human adrenal tissue slices. Each slice is later fixed and stained for CYP11B2 (aldosterone synthase) by immunohistochemistry (IHC). To relate calcium activity to CYP11B2-positive tissue, the user must know **where on the stained slice each calcium recording was taken**.

Currently this is done by hand in PowerPoint: the user drags each recording's field-of-view image onto the IHC image, resizes, rotates, and fades it until tissue features line up, judging by eye. This tool replaces that manual step with a purpose-built aligner that captures each placement **quantitatively** as a coordinate transform, so the result is faster, reproducible, and auditable.

Between live imaging and staining, the slice undergoes fixation and dehydration, which deform the tissue **non-uniformly** (shrinkage, holes, local stretching that differ across the slice). This biological fact drives several design decisions below and must not be "optimised away."

---

## 2. Core concept — what the tool actually produces

The primary deliverable of the tool is a **coordinate system**: for each calcium recording, a definitive placement on the IHC image expressed as a **similarity transform**:

- **scale** (uniform across the whole batch — see §5)
- **rotation** θ (per recording)
- **translation** x, y (per recording)

in the coordinate frame of the IHC image.

Everything else in the tool exists to let the user produce, inspect, adjust, and export this transform table. **The exported transform table is the product.** File loading, layout, and the GUI are supporting machinery.

### 2.1 Why a similarity transform, and why per-window (do not change this)

The true mapping from live tissue to stained tissue is non-rigid (see §1). We deliberately model it as **piecewise similarity**: non-rigid across the whole slice, but approximately a similarity transform (translate + rotate + uniform-scale) within each *small* recording window. Over a small patch, even a large global deformation is approximately linear, so a per-window similarity transform captures almost all of the real alignment while remaining **auditable** — three human-readable numbers per window that can be sanity-checked and reproduced.

Do **not** replace this with a single global transform (the slice deforms non-uniformly, so one transform cannot fit all windows), and do **not** escalate to affine or elastic/non-rigid registration (those can represent stretch/shear/warp but are effectively impossible to inspect or defend in a scientific methods section). This limitation is intentional and will be stated explicitly in the user's methods. v2 may add per-window local distortion; v1 must not.

---

## 3. Scope

### 3.1 In scope for v1
- Load one **experiment**'s recordings and its IHC image.
- Detect and report missing / misspelled / unreadable flat images.
- Lay out labelled recording images beside the IHC image.
- Interactive placement: per-window rotate and drag; single uniform batch scale (drag-to-resize and numeric entry).
- Independent, stepped transparency on the IHC layer and on each recording.
- Non-destructive display-contrast controls on each recording image.
- Autosave, session-scoped undo (down to load-point), and Save As versioning.
- Export the transform table (CSV) plus an action log.

### 3.2 Explicitly out of scope for v1 (do not build)
- **Per-window local distortion** (stretch/shear/warp to match holes, dehydration, stretched regions). This is v2. v1 must be structured so this can be added later without a rewrite (see §12), but must not implement it.
- **Mastersheet-driven IHC lookup.** In v1 the user supplies the IHC image manually (see §4.2). Resolving experiment → slice → IHC via the mastersheet is v2.
- **Spatial correlation of calcium activity with CYP11B2-positive regions** (the downstream analysis that consumes the transform table). Separate future phase.
- Automatic registration / fiducial detection. Placement is manual, by eye.

---

## 4. Inputs

### 4.1 Folder structure and recording identity

The user points the tool at a root processing folder. The hierarchy is:

```
Processing/
  OP_006/
    Ex_006_03/
      Rec_006_03_01/
      Rec_006_03_02/
      ...
```

- `OP_<opnum>` — one surgery.
- `Ex_<opnum>_<expnum>` — one experiment (calcium imaging session on one slice). **The slice/IHC identity cannot be derived from this name**; in v1 it is supplied manually (§4.2).
- `Rec_<opnum>_<expnum>_<recnum>` — one recording.

The tool operates on **one experiment at a time** (one `Ex_*` folder). Recording identity comes **from the folder structure**, not from any external lookup.

### 4.2 IHC image (manual in v1)

At the start of a session the tool must present a required step in which the user identifies the IHC image for the experiment being worked on (e.g. an explicit "select the IHC image for Ex_006_03" prompt/confirmation). The tool must **log** which IHC file was used for which experiment, so this manual choice becomes a recorded fact rather than an invisible step.

IHC images may be JPEG or another common format and may carry **no** pixel-size metadata (see §5.2).

### 4.3 Flat images — the placement unit

The tool does **not** open raw calcium stacks/movies. For each recording, the user has pre-computed an average image over frames 100–150, saved as:

```
Flatrec_Rec_006_03_01   (in that recording's folder, in a standard image format)
```

The **flat image is the unit the tool places.** For each recording implied by the folder structure, the tool locates its flat image and uses it as that recording's field-of-view still.

The flat image must be clear enough to show two landmark types the user aligns by: **the "harp strings"** (a fixed pattern present on every recording) and **the tissue outline**. The tool does not need to detect these; it only needs to display the image well enough for the user to see them (see §8 display-contrast).

### 4.4 Pre-flight report on flat images (required)

For every recording under the experiment, the tool must report the flat image's status, distinguishing (do **not** collapse these into one generic "missing"):

1. **Present & readable** — usable.
2. **Missing** — no matching file found.
3. **Suspected misspelling** — a file that *nearly* matches the expected `Flatrec_<recid>` name (surface as a "did you mean X?" so the user can correct naming).
4. **Present but unreadable** — matches the name but cannot be opened/decoded.

This report is shown before/at the start of placement and is itself an audit artifact. The tool must never silently skip a recording.

---

## 5. Scale (size)

### 5.1 Uniform across the batch (hard rule)

All recordings in one experiment were acquired on the same objective and are placed on the same IHC image; it is physically wrong for one to be scaled differently from another. Therefore **scale is a single shared value for the whole batch**, governed by **one** scale control, not one per window. Resizing (by drag or by number) rescales **all** windows together. The tool must make it structurally impossible to give two windows different scales in v1.

### 5.2 Manual is primary; metadata is an optional pre-fill

Pixel-size metadata **cannot be assumed**: JPEG carries no reliable pixel-size, so an IHC image exported as JPEG has physically lost it. Therefore:

- **Manual scale entry is the primary, always-available, authoritative path.** A numeric field sets the shared batch scale directly.
- The tool should **attempt** to read pixel size (µm/pixel) from both the flat images (e.g. OME-TIFF/OME-XML) and the IHC image, **display what it found or "none found,"** and **pre-fill** the scale field from metadata *only if* it is available on both sides.
- The user can always override the pre-filled value. Manual entry always wins.

The tool must be fully usable with pure-JPEG inputs and **no** metadata whatsoever. Do not make the metadata path a dependency.

### 5.3 Scale controls
- **Numeric entry field** for the single shared batch scale (authoritative view).
- **Drag-to-resize** on any window, which updates the shared value and rescales all windows.
- The two are two views of one value and must always agree.

---

## 6. Rotation and position

- **Rotation** θ is **per recording** (each window rotates independently), via drag-rotate and/or a numeric entry — implementer's discretion on the interaction, but the value must be inspectable/settable.
- **Position** (x, y) is **per recording**, via drag.

---

## 7. Layout and labels

- On load, the tool lays the flat images out **beside** the IHC image, in recording order, so the user can pick them up and place them.
- Each flat image carries a **label showing only the short recording number** (e.g. `1`, `2`, `3` — the `<recnum>` tail), so it stays uncluttered and readable while the user works against a paper labbook.
- The label is a **working tool**, not decoration: it must stay attached to its image through rotation, scaling, and dragging, and must remain **legible regardless of the image's transparency or what is beneath it** — i.e. the label does **not** inherit the image's opacity; it stays crisp on top.
- **Internally and in all exports, the full recording ID (`Rec_006_03_01`) is retained.** Display short, store/export full. A CSV row must be unambiguous months later.

Whether the label also appears in any exported overlay figure is deferred (see §11 note); v1 requires it as an on-screen placement aid at minimum.

---

## 8. Transparency and display-contrast

### 8.1 Transparency (opacity) — both layers, stepped
- Independent opacity control on **the IHC layer** and on **each calcium window**.
- Discrete stepper: **0% to 90% transparency in 10-percentage-point steps** (i.e. opacity 100% → 10%). **No free slider; 100% transparency (fully invisible) is not offered** — a placed window must always remain at least faintly visible.
- Being able to fade both layers lets the user judge the match in both directions (window-through-stain and stain-through-window).

### 8.2 Display-contrast — non-destructive (required in v1)
- Each flat image has **display-only** contrast controls (brightness/contrast, or preferably min/max display-range like Fiji).
- These change **only how the image is rendered**, never the pixel data and never any file on disk. This lets the user recover faint harp strings / tissue outline from a washed-out flat image **without regenerating it**, which is the user's biggest anticipated time-sink.
- (If the frames-100–150 average genuinely lost the information, this cannot recover it — that is acceptable and out of the tool's control.)

---

## 9. Compositing / rendering model

Treat this as an explicit **layered composite** with a fixed z-order:

1. **Bottom:** IHC image (with its own opacity).
2. **Middle:** calcium windows (each with its own opacity, rotation, scale, position).
3. **Top:** labels (never faded).

The z-order must be held explicitly by the program. State this up front rather than discovering it later.

---

## 10. Persistence: autosave, undo, Save As (three separate mechanisms)

These are related but architecturally distinct. Keep them separate.

- **Autosave:** the current placement state is continuously persisted to the working session, so a crash or accidental close loses nothing. Autosave writes only to the tool's own session store — **never** to any input file (flat images, IHC image, folders).
- **Undo / redo:** an **in-memory** history for the current session. Undo steps backward through edits, with a **floor at the state when the file/session was last opened** — a snapshot taken at load. It does not go further back than load-point. Autosave must not corrupt this baseline (autosave persists current state; undo replays session history against the load snapshot).
- **Save As:** explicitly forks a **named version** the user can return to. This is deliberate versioning, distinct from autosave's single rolling working state.

A saved/reopened session that restores placements is itself an audit record; restoring must reproduce placements exactly.

---

## 11. Output — the transform table (the product)

On export, produce a **CSV**, one row per recording, in the IHC image's coordinate frame. Each row must contain at least:

- **full recording ID** (`Rec_006_03_01`) — unambiguous.
- **short number** (optional convenience column).
- **x, y** — translation in the IHC image coordinate frame. *State the convention explicitly in the file/header:* what the origin is (e.g. top-left of the IHC image, +y direction) and what point of the window x,y refers to (e.g. window centre vs top-left corner).
- **rotation** θ — with **units and sign convention stated** (e.g. degrees, positive = counter-clockwise).
- **scale** — the shared batch scale (same value on every row is expected and correct).
- Enough additional fields to make the placement **lossless / reconstructable** (e.g. window pixel dimensions, and — if used — the pixel-size values and their source: metadata vs manual).

The convention statements are mandatory: an exported transform is useless if the reader cannot tell what the numbers mean. Prefer writing conventions into a header/comment block or an accompanying sidecar, and keep the CSV machine-parseable.

**Also export an action log** recording at least: which experiment was worked on, which IHC file was used (§4.2), the flat-image pre-flight results (§4.4), the scale value and whether it came from metadata or manual entry, and the time of export. This log is a first-class auditability output, not an afterthought.

*(Deferred, not v1: an exported rendered overlay figure — the composited IHC+windows image — for use in papers/figures. Design v1 so this could be added, but do not build it now unless trivial.)*

---

## 12. Engineering expectations

"Written the way an experienced programmer would" here means **fit-to-context**, not maximal architecture. Concretely:

- **Separate the alignment/transform logic from the GUI.** The transform math (constructing a similarity transform from scale/θ/x,y, mapping points between window and IHC frames, producing the export rows) must live in a module that can be **tested without the GUI**. This is the single most important structural requirement.
- **Transform math in one place, with conventions defined once** and reused (origin, axis directions, angle sign/units). No duplicated or contradictory transform code.
- **Deterministic and reproducible:** the same placements always yield the same exported numbers.
- **Never write to inputs.** Flat images, IHC images, and the source folders are read-only to the tool. All tool output (session store, versions, CSV, logs) goes to a separate location.
- **Explicit handling of the §4.4 failure modes** — no silent skips, no crashes on a missing/unreadable image.
- **Sensible logging** of the actions listed in §11.
- **An internal seam for v2:** the per-window transform should be represented so that a richer per-window model (local distortion) can replace/extend the similarity transform later **without rewriting** the GUI, persistence, or export layers. Do not implement v2; just don't wall it off.
- **Do not gold-plate.** No plugin systems, no premature abstraction layers, no support for hypothetical multi-user or multi-experiment-at-once scenarios. One scientist, one experiment at a time, one workstation.

Framework, language, and GUI-toolkit choices are left to the implementer **except** where they conflict with the above (in particular: the transform logic must be GUI-independent and testable, and the tool must be non-destructive to inputs). The user's environment is Windows with a Python toolchain, so a Python solution is the natural default unless the implementer has a strong, stated reason otherwise.

---

## 13. Summary of the v1 interaction, end to end

1. User points the tool at one experiment's folder (`Ex_006_03`).
2. Tool discovers recordings from the folder structure and locates each `Flatrec_*` image; shows the pre-flight report (present / missing / misspelled / unreadable).
3. User identifies/confirms the IHC image for this experiment; tool logs it.
4. Tool reads pixel size from both sides if available, displays what it found, and pre-fills the shared batch scale if possible; otherwise the user enters scale manually.
5. Tool lays out the labelled flat images (short number) beside the IHC image.
6. Guided by a paper labbook and by matching harp strings / tissue outline, the user rotates each window individually and drags it onto the IHC, adjusting per-window and IHC opacity (stepped) and per-image display-contrast (non-destructive) as needed. Scale stays uniform across all windows.
7. Work autosaves continuously; the user can undo back to load-point and can Save As named versions.
8. On export, the tool writes the transform CSV (full ID, x, y, θ, scale, conventions, reconstruction fields) plus an action log.

The transform CSV is the product; everything else serves it.
