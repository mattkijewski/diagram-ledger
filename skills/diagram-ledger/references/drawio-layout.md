# Rendered draw.io layout checks

For every new or revised draw.io source, including a source prepared for Lucidchart import, run the structural checker and then this rendered check when its dependencies are available. The renderer uses native draw.io text bounds and connector paths; it does not guess routes from XML coordinates. It checks every uncompressed page separately, including files that reuse cell IDs across pages.

## One-time setup

The optional runtime needs Node.js, Playwright and an installed Chrome/Chromium browser. Reuse existing dependencies first. No rendering command installs packages or fetches a viewer automatically.

To explicitly install the pinned draw.io viewer into the user's cache:

```sh
python3 "<skill-directory>/scripts/setup_drawio.py" --install
```

Without `--install`, this command only checks the cache and exits nonzero if it is missing or has the wrong checksum. The renderer verifies that checksum again before executing the viewer. Use `--viewer /path/to/viewer.js` with both scripts, or `DIAGRAM_LEDGER_DRAWIO_VIEWER`, for a custom cache location.

If Playwright is missing, an optional project-local setup is:

```sh
npm install --prefix .diagram-ledger-tools playwright@1.62.1
```

Use an existing Chrome installation with `--browser chrome`. Alternatively, use an already-installed Playwright Chromium by omitting that flag. Installing a browser or downloading dependencies requires the user's installation authorization; do not do it silently as part of drawing. On Windows use `py -3` instead of `python3`.

The viewer is a separate [draw.io runtime dependency](https://github.com/jgraph/drawio/tree/e159fbf1b1446a37dd68e952ac3db7519735e4f4), pinned to version 29.0.3 and a SHA-256 checksum in `scripts/drawio-runtime.json`. Its [license](https://github.com/jgraph/drawio/blob/e159fbf1b1446a37dd68e952ac3db7519735e4f4/LICENSE) applies to that dependency. The viewer is downloaded separately, not redistributed inside the skill ZIPs. Diagrams stay local; rendering blocks resource requests and diagram scripts.

## Run before delivery

```sh
python3 "<skill-directory>/scripts/check_diagram.py" diagrams/service-architecture/service-architecture.drawio
node "<skill-directory>/scripts/render_drawio.mjs" diagrams/service-architecture/service-architecture.drawio --out diagrams/service-architecture/exports/layout-check-01 --browser chrome --modules .diagram-ledger-tools/node_modules
```

Use a **new output directory for each attempt**. An existing directory is rejected so an earlier passing report cannot masquerade as the latest result. Omit `--modules` if Playwright resolves normally, or point it to the host's existing `node_modules` directory.

Outputs include `audit.json`, `page-1.png` and `page-1.svg`, with additional numbered exports for every page. `audit.json` records the source SHA-256, viewer version/hash, page IDs and names, preview scaling and findings. A successful command exits 0 with `status: "pass"`; findings or unsupported content exit nonzero. Missing dependencies and invalid input never count as a pass. A preview existing on disk does not prove success.

Inspect both the report and the images. Fix every actionable finding, rerun into a fresh directory after the last source change, and deliver the final audit alongside the source. In revisions, also regenerate the preservation receipt for that same final source. Do not claim a verified layout if the renderer was unavailable, failed, or inspected an older source; explain the specific limitation and any manual review actually performed.

## Findings and repairs

- `routeTextCollisions` identifies the edge and label cell IDs. Move the route around the label, reserve a clear corridor, or move the relationship label beside its line. The check includes container headings and endpoint labels. An edge's own label is exempt only when the renderer finds its opaque background; unrelated labels are still protected.
- `routeNodeCollisions` identifies connections passing through unrelated rectangular node bounds. Add explicit waypoints and entry/exit ports. Automatic orthogonal routing alone does not avoid every intervening box. Leave room for arrowheads and use separate tracks for multiple connections.
- `textOverlaps` identifies overlapping label bounds. Increase spacing, wrap text or enlarge affected nodes; do not shrink text until it becomes unreadable.
- `unsupported` identifies geometry that cannot receive a clean automatic pass. Preserve it and perform native review; do not remove elements to make the checker pass.

Keep labels, IDs, connection direction and grouping unchanged while repairing visual layout unless the user's request changes their meaning. For a dense architecture, prefer an overview and focused detail pages when appropriate. If retaining one canvas, widen its corridors and canvas rather than drawing through boxes. Do not suppress findings or classify ordinary nodes as containers to hide crossings. A demonstrated false positive can be explained with visual evidence, but the automated result remains a finding.

## Scope and limits

The supported input is uncompressed `mxfile` XML with direct cells, basic shapes, text/HTML labels, nested containers and straight/polyline connectors. The renderer measures native canvas coordinates independently of preview scaling. Background groups are explicit containers or top-aligned boxes enclosing a complete node; their bodies may be crossed, while their headings remain protected. This inference is reported in `containers` and should be reviewed.

The audit uses label rectangles and line centerlines. Rounded bends are approximated by their segments; nonrectangular node boundaries are approximated by their boxes. Opaque backgrounds on other labels do not excuse wrong routes. Curved connectors, hidden/collapsed content, unsupported shapes, math typesetting, compressed pages and object wrappers cannot receive a clean automatic result. Expand/export a supported copy only when meaning can be preserved; otherwise report native review as required. Remote images, fonts and other resources are blocked.

A pass does not prove semantic accuracy, readable zoom level, perfect arrowheads, zero line-to-line crossings or Lucidchart import fidelity. Inspect the preview at an appropriate scale and read the full-size SVG when the overview is reduced. Excalidraw, Mermaid and SmartDraw still need their own native visual checks; this renderer does not certify them. SVG/HTML use the separate `render.mjs --strict yes` workflow in [verification.md](verification.md).
