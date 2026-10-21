# Measure, inspect, repair

The reliable loop is: write source → run structural checks → render → inspect measured findings and image → repair source → render again. A final preview must match the final source, not an earlier revision.

For draw.io sources, use the native [draw.io layout workflow](drawio-layout.md). The SVG/HTML renderer below does not import draw.io.

## Local preview

The optional renderer uses an existing Playwright installation and browser. It does not download dependencies. Typical use:

```sh
node "<skill-directory>/scripts/render.mjs" diagrams/content-review-flow/content-review-flow.html --out diagrams/content-review-flow/exports/svg --browser chrome --strict yes
```

If Playwright is outside normal Node resolution, add `--modules /path/to/node_modules`. Use `--width 1200` to set the browser viewport; it does not rewrite the SVG canvas. Omit `--browser chrome` to use Playwright's already-installed Chromium. The host may provide equivalent screenshot/render tools; use them when appropriate.

Outputs: `preview.png`, `audit.json`, and one standalone `diagram-N.svg` per inline SVG. Page scripts and HTTP(S) requests are disabled. Inspect the PNG using the host's image-reading tool. Review the SVG export too if that is the delivery artifact: CSS-inlined export is convenient but advanced effects and referenced fonts still need inspection.

`--strict yes` returns a nonzero exit for measured text overlap, labels outside the canvas, text below 12 display pixels, annotated geometry findings, or blocked network requests. A finding is evidence to investigate; manual inspection decides whether an intentional overlap is appropriate. Do not erase annotation or suppress a warning to pass a check while leaving the visible defect.

Use strict mode for verification, and read `audit.json` as well as the image. A PNG being created does not mean the audit passed. Resolve connector-label collisions and other actionable findings before claiming a clean render; if a finding is a false positive, identify it and explain the visual evidence rather than silently omitting it from the handoff.

Do not dismiss overlapping labels, a connector crossing an unrelated component, or arrows too short to read as merely a “tight layout.” Route through clear space or separate affected elements; preserve unrelated nodes during revisions and expand the canvas if needed. If the user's constraints prevent a repair, report the unresolved visual failure and the smallest needed layout change instead of saying the meaning is clear.

## Useful semantic SVG annotations

For hand-authored architecture, flowchart, ER, and other node/edge SVGs, use stable IDs and these attributes. They add no visible decoration and make checking possible:

```xml
<g id="orders-api" data-node="orders-api">
  <rect data-body="" x="80" y="160" width="200" height="88"/>
  <text x="180" y="210" text-anchor="middle">Orders API</text>
</g>
<g data-edge="api-to-store" data-from="orders-api" data-to="orders-store">
  <path data-route="" d="M280 204 H400" marker-end="url(#arrow)"/>
</g>
```

Place node labels inside their annotated node group. Put `data-body` on the visible boundary shape. For a labeled edge, keep the route and label together in its edge group. Use `data-node` only for actual diagram nodes, not page titles or decorative group backgrounds. Mark sequence lifelines and fragments using their own IDs rather than pretending they are rectangular nodes. Use `data-message` (not `data-edge`) for sequence messages: the node endpoint checker does not model lifelines. Sequence message direction and branch membership still require semantic review.

For network, trust, ownership, or deployment boundaries, annotate the boundary as a **container**, never as a node:

```xml
<g data-container="application-network">
  <rect data-body="" x="280" y="160" width="600" height="480"/>
  <text x="304" y="192">Application network</text>
</g>
<g data-node="api" data-within="application-network">...</g>
<g data-node="managed-store" data-outside="application-network">...</g>
```

Annotate every node's required membership using `data-within` or `data-outside`; multiple container IDs are space-separated. The checker measures the whole node body, with 12 px minimum clearance for inside nodes. Place children below the container heading with at least 24 px visual clearance. A node centered inside but protruding across the bottom is **outside the contract**; enlarge the container or move the node. Do not dismiss this as intentional overlap. Nested scopes need membership in each relevant ancestor.

Route to the actual component body, not its surrounding group or boundary. A line ending at a managed-storage container is not a connection to the Object store inside it. A `route ends more than 10 px from target` finding needs an actual geometry check and repair; proximity to a surrounding group is not a false positive.

The renderer measures actual browser text bounds, font scaling, text overlap, canvas clipping, and marked routes crossing labels. It recognizes simple opaque rectangle masks drawn after a route. Annotated node checks measure padding, approximate rectangular containment, text contrast against a flat fill, and node overlap. Annotated edge checks sample the route for transit through unrelated node boxes, endpoint distance, and the final tangent pointing toward the target. Paths must be SVG geometry (`path`, `line`, or `polyline`), not a group standing in for a path.

Limitations: shape bounding boxes are not exact polygons; sample-based intersection checks may miss tiny intersections; transparency and gradient contrast need manual checking; labels on routes, arrowhead clipping, and edge crossings still need image review. A semantic inventory is necessary to catch omitted edges: perfect geometry cannot prove that a missing connection exists.

## Review at delivery size

1. Trace every required relationship from its source to its arrowhead. Read the label and confirm the direction. An arrow ending close to a node can still point away from it.
2. Inspect each decision branch, loop, optionality marker, and trust boundary against the brief.
3. Scan every label for fit, overlap, and size. A SVG font-size of 16 becomes 8 px when the graphic is scaled by half.
4. Check routes for transit through unrelated nodes and through labels. Check dense crossings for accidental junctions.
5. Check all four canvas edges and the footer. Allow outer margins and arrowhead extent.
6. Inspect exports after the last edit. Report structural and visual checks separately.

## Targeted revisions

Read [revision.md](revision.md) when changing an existing drawing. Compare stable IDs, geometry, and relationships before and after. A correction that improves one route but breaks another is not finished.

## Final layout gate

For every selected destination, start with the unified [layout gate](layout-checks.md). It invokes this strict SVG/HTML renderer and the corresponding native renderers for other formats, keeping pending app imports separate from source passes.
