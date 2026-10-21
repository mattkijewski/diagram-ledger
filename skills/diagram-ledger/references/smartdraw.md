# SmartDraw VisualScript import — beta

Use `.vson` JSON for this destination. Do not invent an `.sdr` file or substitute an SVG image for editable diagram objects. Start with the original [review-flow sample](../assets/imports/review-flow-smartdraw.vson), replacing its domain with the user's requested process.

## Flowchart authoring

Set `Version` to `"1.0"` and `Template` to `"Flowchart"`. Each shape needs a distinct positive integer `ID`. Nest child shapes under `ShapeConnector` entries with `ShapeConnectorType: "Flowchart"`, a `Direction`, and a `Shapes` array. A connector's children form an ordered flow; use separate connectors for separate branches. Use `LineLabel` on a child for its incoming edge label. Back-edges belong in root `Returns` using existing `StartID` and `EndID` values.

Use `ShapeConnector` for new files; existing files may use the older `ShapeList` spelling. The checker accepts either, but not both on one shape. Keep one spelling consistently and do not change it blindly to hide an import failure. Report which source spelling failed in the target application.

SmartDraw controls placement. Preserve the graph and labels, but do not promise exact source coordinates, layout stability or equivalent custom styling.

Write `Label` and `LineLabel` as plain Unicode strings and serialize as JSON. Do not HTML-escape punctuation or ampersands; use `—`, `•`, `→` and `&` directly. Verify the resulting labels during import.

## Verify and deliver

Run `python3 "<skill-directory>/scripts/check_diagram.py" diagram.vson`. This validates only the basic flowchart subset: structure, IDs, branch lists and return references. Native import is still required.

For the user: in SmartDraw, select **+ → Insert Content → Add Data Visualization → VisualScript**, then upload the `.vson`. Inspect labels and branches, move a node and edit its text. Deliver the source and a brief inventory so the imported graph can be compared.

Keep the source and a manual change log for revisions. Automated revision receipts do not cover VSON or the resulting SmartDraw document. This beta does not validate floor plans, tables, frames, custom symbols or every VisualScript feature; do not delete imported features just to pass the narrow checker. Application import/editability testing remains pending.
