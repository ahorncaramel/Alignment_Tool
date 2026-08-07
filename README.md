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
- **Mouse wheel** over a window rotates it (1°/step, **Shift**+wheel for
  10°/step).
- **Ctrl+wheel** over a window changes the **batch scale** (all windows
  share one scale, spec S5.1 -- there is no per-window size).
- **Ctrl+wheel** over empty canvas zooms the view.
- **Ctrl+0** or **View > Fit to Window** fits the view to everything placed.

All of the above (except view zoom) is frozen once alignment is **locked**
(see below).

## The Controls panel (right-hand dock)

Top to bottom:

- **Recordings list** -- double-click any entry to jump the view to that
  recording (works for dropped ones too). Shows `(dropped)` and
  `[activity: ...]` tags where relevant.
- **Batch scale** -- the one shared scale field; typing here is equivalent
  to Ctrl+wheel-resizing any window.
- **IHC transparency** (0-9) -- fades the IHC layer.
- **Selected window transparency** (0-9) -- fades just the selected window.
- **Selected window rotation (deg)** -- type an exact angle for the selected
  window instead of using the mouse wheel.
- **Selected window display contrast** -- min/max remap for on-screen
  viewing only; never touches the source pixel data. "Reset to full range"
  clears it.
- **Drop selected recording / Restore selected recording** -- toggles
  whether the selected recording is excluded from the export. A dropped
  window stays visible (translucent red tint) and selectable -- it isn't
  hidden or deleted, and clicking the same button un-drops it in one step
  regardless of what else you've edited since.
- **Lock alignment / Unlock alignment** -- see below.
- **Activity** and **CYP11B2** groups -- only visible once locked, see below.
- **Selected ruler length (px)** -- active only when a ruler (not a
  recording) is selected; see "Ruler" below.

## Alignment lock, then Activity / CYP11B2 marking

This is a deliberate two-pass workflow: align first, unbiased, then judge
afterwards.

1. While **unlocked** (the default), placement (drag/rotate/scale) is
   editable, and the Activity/CYP11B2 controls are **hidden entirely** --
   not just disabled -- so there's nothing to glance at while still aligning.
2. Click **Lock alignment** once you're done positioning a recording.
   Placement becomes frozen (drag/wheel-rotate/batch-scale stop affecting
   locked windows), and the Activity/CYP11B2 groups appear.
3. **Activity**: mark each selected recording "Activity (green)", "No
   activity (red)", or "Undecided". Shown live as a green/red outline on the
   window and carried into the exported PNG.
4. **CYP11B2**: mark "Present" / "Absent" / "Undecided" -- independent of
   Activity, and deliberately given **no on-screen visual treatment** (not
   even in the export), so judging one doesn't visually bias the other.
5. **Unlock alignment** re-hides the two groups and re-enables placement
   editing, but never discards anything already marked -- toggling back and
   forth to fix a placement is expected, not a one-way commitment.

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
    just placed ones), with its status, x/y/rotation/scale, both the flat
    image path and the IHC image path, and an explicit coordinate-convention
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
