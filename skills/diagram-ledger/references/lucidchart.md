# Lucidchart import — beta

Use this destination when the user selects Lucidchart. Deliver a `.drawio` source, an inventory of nodes/connections, and the import steps. Use the [draw.io guide](drawio.md); keep ordinary shapes, plain text and direct connectors. Avoid custom stencils, HTML labels and complex nesting unless the user can test them.

The [review-flow sample](../assets/imports/review-flow-lucidchart.drawio) is an original four-node import test. A structural pass validates the source graph, not Lucidchart's conversion.

## User import

1. Open the generated source in draw.io/diagrams.net. Inspect it, then save/export a `.drawio` or XML copy through that application. This produces an application-saved copy for import.
2. In Lucidchart's Documents page, choose **+ New → Import documents** and select the exported copy.
3. Check every label, arrow direction and branch. Move a shape and edit its text to check actual editability.

Lucid currently allows free accounts to import/view but requires a paid plan to edit imported documents. Explain this requirement without initiating a purchase or trial.

Do not rename arbitrary JSON to `.lucid`. Lucid's Standard Import is a separate ZIP/JSON and authenticated API workflow; it is not implemented here.

For revisions, retain the draw.io source and the imported document separately. A draw.io revision receipt applies only to that source pair, never to Lucidchart's resulting document. If the user edited in Lucidchart, use a new export as the baseline; do not assume the previous local source still represents it.

Status: destination import and editing are awaiting user testing. Report any conversion losses instead of promising identical layout.

## Final layout gate

Run the unified [layout gate](layout-checks.md) on the `-lucidchart.drawio` source. A passing draw.io render is recorded as source-layout pass with `native-check-required` for Lucidchart. Import into Lucidchart, inspect lines and labels at the intended size, and record the exact source hash plus a native screenshot/export in the bundle index. If app access is unavailable, keep the native check pending.
