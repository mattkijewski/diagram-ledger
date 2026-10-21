# One diagram, multiple editable sources

Use this workflow for “All formats,” “all,” menu choice 7, or an explicit subset. All formats means the four standard sources plus Lucidchart and SmartDraw import sources; it does not require accounts, uploads or every possible preview format.

## Model once, represent consistently

1. Establish one inventory of entities, directed relationships, branch labels and containers from the brief. Save it as `model.json` in the diagram's subject folder, using stable IDs and recording material assumptions. This is a lightweight inventory, not a universal conversion schema.
2. Read each selected format guide. Produce sources from that shared inventory; adapt layout and styling to each format without inventing or dropping relationships. Prefer the same diagram family across the bundle where supported. Do not add initial/final states, implied transitions or containment absent from the inventory just because a notation commonly uses them. For example, `Draft → Review → Published` does not establish `[*] → Draft` or `Published → [*]`.
3. Keep all selected sources in one subject folder. For example:

   ```text
   diagrams/content-review-flow/
     model.json
     content-review-flow.drawio
     content-review-flow.excalidraw
     content-review-flow.mmd
     content-review-flow.svg
     content-review-flow-lucidchart.drawio
     content-review-flow-smartdraw.vson
     README.md
   ```

   `README.md` is the bundle index: link each source, summarize how to open/import it and record actual validation and conversion limits. Optional previews belong in `exports/<format>/` below this folder. Use only the requested sources for a subset.
4. For Lucidchart, make a separately named import source following [lucidchart.md](lucidchart.md). It may match the regular draw.io file byte-for-byte if already suitable; explain that both target the same file format. Do not invent a native `.lucid` file.
5. For SmartDraw, follow [smartdraw.md](smartdraw.md). The supported beta subset is basic flowcharts. For a diagram whose meaning cannot be faithfully represented by that subset, complete the other formats and mark SmartDraw **unsupported for this diagram** in the bundle index. Explain the specific loss and offer an alternate view; do not silently turn a sequence, ER model or architecture boundary into a misleading flowchart, and do not emit an empty placeholder or claim all six were completed.

## Check and hand off

Run the [unified layout gate](layout-checks.md) with **every selected source** after the final edit. Read the summary and each detailed audit, inspect every available preview, and repair findings. Record per-format source hashes, reports and preview links in the bundle index. Lucidchart and SmartDraw stay `native-check-required` until actual destination-app review is recorded; this intentionally prevents an all-format bundle from claiming full verification from local checks alone. Run the applicable structural checker separately on each supported source. Parse/render Mermaid when its renderer is available. Reconcile every source against the inventory: nodes, directions, labels, branches and containment must agree, or have an explicit format limitation. Render and inspect each with an available compatible renderer; record unavailable rendering and pending native imports separately from structural passes.

Link the bundle index and summarize which sources were produced, which checks ran and any unsupported outputs. Source generation is not proof of native app import or visual equivalence. Generate previews only when useful or requested, without silently installing dependencies.

## Revise the bundle

Treat a revision requested for the whole diagram as a revision to all existing bundle formats. Reconcile the inventory against the current sources before editing; it must not override manual changes made since generation. Preserve originals and use the [revision workflow](revision.md), with separate receipts for supported files and manual change logs for the others. Update the shared inventory and bundle index to point to the revised sources.

If the user explicitly edits only one format, scope the change accordingly and mark the other representations as out of sync in the index. Do not silently replace manual edits or claim all representations were updated.
