# Alignment Tool -- how to use it

This is the practical "how do I drive this thing" guide. For the underlying
design rationale and data model, see [`alignment_tool_spec.md`](alignment_tool_spec.md);
this file just documents what's actually on screen today (the spec predates
several features below and doesn't describe menus/buttons concretely).

## Starting it

```
cd path\to\Alignment_Tool
.\.venv\Scripts\alignment-tool.exe
```

## Opening an experiment

On launch (or **File > Open Experiment...**):

1. **Pick a Processing root** the first time (remembered afterwards via
   "Change Processing folder...") -- the read-only folder tree containing
   your `OP_*/Ex_*` experiments and recordings.
2. **Pick an output folder**, kept entirely separate from Processing --
   everything the tool writes (session store, versions, CSV, action log,
   aligned PNG) goes here, mirroring the Processing tree's structure. Inputs
   are never written to.
3. Pick an experiment from the list and click **Open**.
4. A **pre-flight report** shows which recordings were found, missing, or
   unreadable before you start.
5. **Select the IHC image** for this experiment (a required, explicit,
   logged step -- there is no automatic lookup in this version).
6. If a previous session for this experiment exists, you're asked whether to
   **resume** it or start fresh.

## The canvas

The IHC image sits at the bottom; each recording's flat image is a
draggable window on top, labelled with its short number.

- **Drag** a window to move it.
- **Mouse wheel / touchpad scroll** anywhere (over a window or empty canvas)
  pans the view -- it never rotates or scales a window.
- **Ctrl+wheel** zooms the view.
- **Ctrl+0** or **View > Fit to Window** fits the view to everything placed.
- Rotation and scale are never set from the canvas: rotate the selected
  window via **Selected window rotation (deg)** in the Controls panel, and
  resize all windows via **Batch scale** (all windows share one scale, spec
  S5.1 -- there is no per-window size).

All of the above (except view zoom) is frozen once alignment is **locked**
(see below).

## The Controls panel (right-hand dock)

Top to bottom:

- **Recordings list** -- double-click any entry to jump the view to that
  recording (works for dropped ones too). Shows `(dropped)` and
  `[activity: ...]` tags where relevant.
- **Batch scale** -- the one shared scale field; the only way to resize
  windows (all windows share one scale, there is no per-window size).
- **IHC transparency** (0-9) -- fades the IHC layer.
- **Selected window transparency** (0-9) -- fades just the selected window.
- **Selected window rotation (deg)** -- the only way to rotate the selected
  window; use the up/down arrows for 1°/step or type an exact angle.
- **Selected window display contrast** -- min/max remap for on-screen
  viewing only; never touches the source pixel data. "Reset to full range"
  clears it.
- **Drop selected recording / Restore selected recording** -- toggles
  whether the selected recording is excluded from the export. A dropped
  window stays visible (translucent red tint) and selectable -- it isn't
  hidden or deleted, and clicking the same button un-drops it in one step
  regardless of what else you've edited since.
- **Lock alignment / Unlock alignment** -- see below.
- **Start CYP11B2 Review / Start Activity Review**, **Activity** and
  **CYP11B2** manual groups -- only visible once locked, see below.
- **Selected ruler length (px)** -- active only when a ruler (not a
  recording) is selected; see "Ruler" below.

## Alignment lock, then CYP11B2 review, then Activity review

A deliberate three-pass workflow: align first unbiased, then judge CYP11B2
before Activity, so neither judgement is coloured by already knowing the
other or the placement.

1. While **unlocked** (the default), placement (drag/rotate/scale) is
   editable, and every review control is **hidden entirely** -- not just
   disabled -- so there's nothing to glance at while still aligning.
2. Click **Lock alignment** once you're done positioning every recording.
   Placement becomes frozen, and the review controls appear.
3. Click **Start CYP11B2 Review**. This walks the aligned recordings one at
   a time: every other window is hidden, the IHC is forced fully visible,
   and the current window starts fully opaque. Use **"Hide recording (show
   IHC only)"** to flip it fully transparent and inspect the bare tissue
   underneath, then flip back, as many times as you need. Click **Yes /
   No / Undecided** to record a decision and auto-advance to the next one
   (**<- Previous** / **Skip ->** to navigate without deciding, **Stop
   review** to bail out and resume later). All the temporary
   hide/show/IHC-visibility changes are undone automatically when the
   review ends -- your normal transparency settings return exactly as they
   were.
4. **Start Activity Review** stays disabled until every aligned recording
   has been through step 3 -- even if your answer for one was "Undecided",
   that still counts as reviewed. This is enforced, not just suggested: you
   cannot judge Activity for anything until CYP11B2 review is complete for
   everything. Once unlocked, it works exactly like step 3, and Activity is
   additionally shown live as a green/red outline on the window (and
   carried into the exported PNG); CYP11B2 deliberately gets **no on-screen
   visual treatment** anywhere, so judging one is never visually biased by
   the other.
5. The **manual Activity/CYP11B2 groups** (Present/Absent/Undecided-style
   buttons for whichever single recording is currently selected) still work
   for one-off corrections outside the guided review, and count as
   "reviewed" the same way a guided step does.
6. **Unlock alignment** re-hides all of the above and re-enables placement
   editing, but never discards anything already marked or reviewed --
   toggling back and forth to fix a placement is expected, not a one-way
   commitment.

Sessions saved before this guided-review feature existed load fine: a
recording that already had a real CYP11B2/Activity decision is treated as
already reviewed; one still at the untouched "undecided" default is treated
as not yet reviewed (so it can't be misread as "reviewed, genuinely
undecided" and skipped).

## Ruler (visual aid only -- not exported, not part of the transform)

**View > Add Ruler...** creates a draggable ruler line with evenly spaced
division marks (default: 5000 µm total, 1000 µm between marks, in dodger
blue). It scales with the IHC image as you zoom, same as everything else on
the canvas. Use it to:

1. Drag it onto the IHC image and stretch its end handle (or type an exact
   value into "Selected ruler length (px)" in the Controls panel once it's
   selected) to match an existing reference bar baked into the IHC image.
2. Once matched, its division marks are a ground truth for real-world
   distance -- use them to eyeball a recording window's known feature
   spacing (e.g. "harp" electrode spacing) and adjust the batch scale until
   they visually agree.

## Undo / redo

**Edit > Undo/Redo** (Ctrl+Z / Ctrl+Y) walks back/forward through every
committed edit -- placement, scale, transparency, contrast, drop/restore,
lock toggle, activity/CYP11B2 marks. It's floored at the state the session
was loaded/resumed at (never further back). For reversing a single drop or
lock toggle specifically, prefer the dedicated toggle button -- it's a
one-click reversal independent of how many other edits happened in between.

## Output (File menu)

- **Save As Version...** -- snapshots the current session to a named,
  timestamped file under `<output>/.../versions/`, independent of autosave.
- **Export Transform CSV...** writes three files together to
  `<output>/<same path as the experiment under Processing>/`:
  - **`transform_export.csv`** -- one row per *discovered* recording (not
    just placed ones), with its status, x/y/rotation/scale, CYP11B2/Activity
    state *and* whether each was actually reviewed (see above -- "undecided"
    is a real answer, distinct from "not reviewed yet"), both the flat image
    path and the IHC image path, and an explicit coordinate-convention
    header -- self-contained enough to read without the tool.
  - **`aligned_composite.png`** -- the IHC image with every placed,
    non-dropped recording window rendered on top at its true
    position/rotation/scale/contrast/opacity, numbered, and outlined
    green/red if Activity was marked. Rendered at the IHC image's native
    resolution from the exact same transform math as the CSV.
  - **`action_log.txt`** -- experiment, IHC file used, pre-flight results,
    scale value/source, export timestamp.

Autosave (`session_autosave.json` in the same output folder) happens
automatically ~0.5s after every edit -- it's what "resume this session" on
next launch reads from.
