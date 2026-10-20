# Excalidraw

Deliver a UTF-8 `.excalidraw` scene containing native, selectable shapes, editable text and bound arrows. Use this format for whiteboard discussions, concept maps and sketch-style architecture. Roughness is a visual treatment; it must not obscure arrow direction or ownership.

## Author the scene

Start from the original [review flow example](../assets/review-flow.excalidraw) for working field and binding combinations. Replace its domain, IDs and layout with the user's model; it is not a universal architecture.

The file is a JSON object with `type: "excalidraw"`, `version: 2`, `source: "diagram-ledger"`, an `elements` array, an `appState` object and a `files` object. A self-contained shape-only diagram uses `files: {}`. Do not add collaboration state or unrelated editor preferences.

- Give each element a unique, stable string `id`. Keep IDs when revising or renaming. Preserve `seed` so unchanged strokes do not acquire a different sketch shape. Use numeric coordinates and dimensions, not strings or NaN.
- For a new drawing, prefer rectangles, diamonds, ellipses, text and simple arrows. The bundled checker supports those plus lines. It intentionally does not validate images, freehand strokes, frames, embedded content or every native editor feature. Preserve those features in imported drawings and report the checker limitation instead of deleting them.
- Bound node labels are separate `text` elements: set `containerId` to the shape ID and add `{"id": "LABEL_ID", "type": "text"}` to the shape's `boundElements`. An arrow label may use the same mechanism with the arrow as its container. Keep `text` and `originalText` consistent. Set positive `fontSize` and `lineHeight`, alignment and sufficient text bounds.
- Bind arrows at both ends when they express relationships. Set `startBinding` and `endBinding` to the endpoint IDs with their binding geometry; list the arrow in each endpoint's `boundElements`. Follow the example's two-way references. A line drawn near a node without a binding may look connected but will detach when the node moves.
- Arrow `points` are local offsets from its `x, y`, beginning at `[0, 0]`. Horizontal arrows can have zero height; vertical arrows can have zero width. Set `endArrowhead: "arrow"` for a directed relationship. Keep the points, width and height consistent; route outside unrelated shapes.
- Use `groupIds` for editor grouping, not as a substitute for a visible, labeled ownership boundary. Array order determines stacking. Put backgrounds first, then connections, then nodes and labels as appropriate.

Use restrained roughness (0 or 1), generous spacing, and a small palette. Use Excalidraw's supported font choices; `fontFamily: 2` is a conventional sans-serif option used in the example. Custom CSS font names from a project style cannot be applied verbatim. Fit and recheck labels in the native editor.

The example uses legacy `elementId`/`focus`/`gap` bindings for portability. Current Excalidraw imports them as `elementId`/`mode`/`fixedPoint` bindings. The checker accepts both; preserve the representation an imported file already uses. Fixed points are two normalized coordinates in the target's bounds, and native modes are `orbit`, `inside` or `skip`. Check visual attachment after conversion.

If the environment already supplies `@excalidraw/excalidraw`, its `convertToExcalidrawElements` helper can expand element skeletons into native elements. A skeleton with `label`, `start` and `end` convenience fields is **not** a finished scene file: normalize it before saving. Avoid regenerating existing IDs during revisions.

## Check and open

```sh
python3 "<skill-directory>/scripts/check_diagram.py" diagram.excalidraw
```

The checker checks basic JSON structure, geometry, IDs, points and two-way label/arrow references. It does not measure text, prove route clearance, render, or verify requested meaning.

Open the file in an available Excalidraw editor using **Open** or by dropping the file onto the canvas. Review labels and routes at a readable zoom. Move a connected node temporarily to verify that its label and arrows follow, then undo. Export PNG/SVG from the native editor or an installed Excalidraw export utility when requested, and always deliver the original scene too. Do not send private content to a hosted editor without authorization. If native rendering is unavailable, deliver the file and clearly state which checks remain undone.

## Revise and convert

Retain an exact original, write down allowed changes, edit a separate copy, and review a source diff plus both native renders. Preserve IDs, coordinates, grouping, bindings, seeds and unrelated styles. Do not flatten a scene to SVG or an image merely to simplify editing.

`revision.py` does **not** support Excalidraw revision contracts. Deliver a manual change log with the source pair and identify this limit. A structural pass is not a field-preservation receipt. For conversion, reconcile every node, edge, label and group; explain any unsupported notation.
