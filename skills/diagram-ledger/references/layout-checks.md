# Layout checks for every destination

A structurally valid source can still have lines through text. Check each selected output after the final edit, read its audit and inspect its preview at the intended reading size. Repair the source and rerun into a fresh directory. Preserve the editable source; the renderer never rewrites it.

## One command

From the user's project, pass the exact source files that will be delivered:

```sh
python3 "<skill-directory>/scripts/check_layout.py" diagrams/service-architecture/service-architecture.drawio diagrams/service-architecture/service-architecture.excalidraw diagrams/service-architecture/service-architecture.mmd diagrams/service-architecture/service-architecture.svg diagrams/service-architecture/service-architecture-lucidchart.drawio diagrams/service-architecture/service-architecture-smartdraw.vson --out diagrams/service-architecture/exports/layout-check-01 --modules /path/to/node_modules
```

For one format, pass only that source. Use a new output directory for every run. The summary `audit.json` links individual renderer reports and records source SHA-256 hashes. Native renderer reports include PNG/SVG previews and finding IDs. Every supplied file is checked even if another fails. Any failed, unsupported, unavailable or pending destination makes the bundle exit nonzero. A pass is never inferred from a different format. Verify that the hashes still match the delivered sources.

The destination is inferred from the extension and the `-lucidchart.drawio` naming convention. Use `--destination lucidchart` for an explicitly named Lucidchart source without that suffix. Markdown files have every fenced `mermaid` block checked. Keep fences flush left with three backticks. HTML means a self-contained page with inline SVG.

## Coverage

| Destination | Local check | Remaining review |
| --- | --- | --- |
| draw.io | Native viewer, all pages; measured label and route geometry | Readability, arrowheads, meaning; unsupported shapes/routes |
| Excalidraw | Native `exportToSvg`; actual text bounds and sampled strokes | Native editing behavior; unsupported elements and bound connector masks |
| Mermaid | Native parser and SVG for flowchart, sequence, state and ER | Destination renderer/version/theme may differ |
| SVG / HTML | Strict browser audit of text, annotated routes and containment | Unannotated connections, arbitrary graphics and meaning |
| Lucidchart | Checks the draw.io import source | **Native import check required**; source pass is not Lucidchart pass |
| SmartDraw | Checks VSON structure | **Native import check required**; SmartDraw determines layout |

The Excalidraw subset is rectangles, ellipses, diamonds, text, arrows and lines without frames or links. Unsupported imported features must be preserved and reported, not removed to obtain a pass. Bound arrow labels currently require native mask review; for a new scene, a free relationship label beside its route can be checked automatically.

The Mermaid preview uses the pinned native renderer, a neutral theme and opaque edge-label backgrounds so lines cannot show through their own labels. The report records these settings. Another Markdown host may use different defaults: inspect that host before claiming its rendering passed. Configuration directives/frontmatter and other Mermaid families require native review and are rejected by this automatic path. Excalidraw/Mermaid curves are sampled every 1.5 native pixels; tiny intersections may be missed. Node bounds are approximations. Sequence message routes are checked; lifelines and decorative strokes are not treated as connectors. SVG routes need the annotations described in [verification.md](verification.md).

No automated pass certifies readability, line-to-line crossings, arrowhead direction, semantics or another application's import. Always inspect the actual images too. Do not label pending native imports as fully verified. For an app review, record the app/version, exact source hash, screenshot/export and observations in the bundle index; keep the automated report intact. If access is unavailable, deliver the source with that specific limitation.

## Optional local setup

First check existing host runtimes. Rendering needs Node.js 22+, Python 3.9+ and Chrome (or installed Playwright Chromium via `--browser chromium`). Install these optional packages only when authorized; they are not bundled in the ZIPs:

```sh
npm install --prefix .diagram-ledger-tools --save-exact playwright@1.62.1 @excalidraw/excalidraw@0.18.0 mermaid@12.2.0 esbuild@0.25.12 react@18.3.1 react-dom@18.3.1
python3 "<skill-directory>/scripts/setup_drawio.py" --install
```

Use `--modules /absolute/path/.diagram-ledger-tools/node_modules` or `DIAGRAM_LEDGER_NODE_MODULES` from any project. The native package versions are checked before rendering; a different version needs validation rather than silently receiving a pass. The draw.io setup is separately pinned and checksum-verified; see [drawio-layout.md](drawio-layout.md).

All subsequent rendering stays local. Native packages and fonts are read from the installed dependencies; network requests are blocked. Missing dependencies are unverified, not successful. For Windows use `py -3` instead of `python3`.
