# Editable draw.io

Write uncompressed XML so the agent and owner can inspect and diff it. Use `assets/service-map.drawio` as a small, working example; its entities are illustrative, not assumed infrastructure.

## File shape

A document has `mxfile` → one or more `diagram` → `mxGraphModel` → `root`. A graph contains a root cell with `id="0"` and a default layer cell with `id="1" parent="0"`. Each visible cell needs a unique ID within its page. The same ID can appear on separate pages.

- Node: `mxCell vertex="1" parent="1" value="..."` and child `mxGeometry x="..." y="..." width="..." height="..." as="geometry"`.
- Connection: `mxCell edge="1" parent="1" source="node-a" target="node-b" value="..."` and `mxGeometry relative="1" as="geometry"`.
- Container: a vertex that can hold child vertices with `parent` set to the container's ID. Child positions are relative to that parent. Do not subtract container positions twice.
- Manual edge routing: an `Array as="points"` inside the edge geometry contains `mxPoint` waypoints. Prefer stable attachment positions over an excessive number of waypoints.

Use persistent semantic IDs such as `payment-api` and `api-to-ledger`; do not renumber unrelated cells after an edit. A group used only for visual organization must be labeled so it does not imply a trust boundary.

## Styles

For a rectangular service, start with `rounded=1;whiteSpace=wrap;html=0;fontFamily=Arial;fontSize=16;fillColor=#FFFFFF;strokeColor=#64748B;fontColor=#172033;spacing=16;`.

For a directed connection, start with `edgeStyle=orthogonalEdgeStyle;rounded=0;html=0;endArrow=block;endFill=1;strokeColor=#64748B;fontColor=#475569;fontSize=14;labelBackgroundColor=#F8FAFC;`. Add `exitX`, `exitY`, `entryX`, and `entryY` when route ambiguity warrants explicit ports.

Choose cylinder, diamond, actor, and other shapes only when they express the selected notation. Undirected associations should not inherit an arrowhead. Return and asynchronous messages require the sequence grammar, not a universally dashed “optional” line.

For a database cylinder, use `shape=cylinder3;size=16;boundedLbl=1;` with a sufficiently tall node. Do not combine the legacy `shape=cylinder` with that size setting: the native viewer can produce distorted curves even when the XML passes structural validation. The included service-map example uses the tested `cylinder3` form.

XML-escape text and attribute values. Prefer `html=0` for ordinary labels. If rich HTML labels are needed, use `html=1`, escape their XML representation, and validate them in draw.io. Do not include scripts, external embeds, or active links from untrusted input.

## Existing documents

Read all requested pages before editing. Existing files can use compressed `diagram` text and object wrappers around cells. The bundled checker deliberately accepts only newly generated uncompressed files with direct cells; it is not an importer. Decode or export a copy using an available draw.io tool, preserving the original. Do not report a compressed but valid source as a broken diagram because this checker does not support it.

## Checks

Run `python3 "<skill-directory>/scripts/check_diagram.py" output.drawio`. It verifies basic graph structure, unique IDs, parent/endpoint references, parent cycles, and positive node dimensions. It does not inspect text fitting, visual intersections, or graph meaning.

Open in draw.io/diagrams.net if available and inspect before exporting. Use the installed application's export interface or documented CLI if present; do not assume a `drawio` executable is installed.
