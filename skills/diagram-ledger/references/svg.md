# Presentation SVG

Create a standalone SVG with the `http://www.w3.org/2000/svg` namespace, explicit width and height, and a matching positive `viewBox`. Use `assets/review-flow.svg` as a working example of a labeled decision and accessible structure, not a required layout.

For node/edge diagrams, add the semantic annotations in [verification.md](verification.md) so the browser can check actual node fit and route endpoints. Read that guide before generating a substantial SVG.

Give the root `role="img"` and `aria-labelledby` referencing a meaningful `title` and `desc`. Prefix IDs with a diagram slug to reduce collisions when several drawings are embedded. The description should explain the relationships, not just repeat the title.

Use real `text` with explicit `tspan` line breaks; SVG does not reliably wrap text automatically. Keep actual Unicode characters and XML-escape reserved characters. Use local/system font stacks. Set colors and critical typography on exported elements or a self-contained stylesheet; do not rely on the surrounding webpage.

Pass raw text to an XML serializer and let it escape once. Use `—`, `•` and `→` directly; `&amp;#8212;` would display the literal code `&#8212;`. In hand-written XML, encode a literal ampersand as `&amp;`; do not pre-escape strings passed to a serializer. Repair affected text nodes individually, preserving any intentionally displayed code examples.

Define arrowheads in `defs` and attach them using local `url(#id)` references. Draw group surfaces first, then routed connections, then nodes and labels. That layering does not excuse routes through unrelated nodes. Route around them. Choose marker size, stroke width, and attachment points together so the arrowhead lands at the intended boundary.

Keep gradients, filters, animation, remote assets, `foreignObject`, and scripts out of the default output. They complicate portability and are unnecessary for ordinary diagrams. Adapt this only to an explicit need, with an appropriate viewer/export check.

If a web wrapper is requested, use an accessible figure with a caption. Put a wide SVG in a local `overflow-x:auto` wrapper; set its width to the intended display width and prevent unintentional flex shrinking. Keep the body width inside the viewport. Do not repeat the title in both HTML and SVG unless each serves a distinct purpose. For a wide diagram, allow local scrolling or offer a detail view rather than shrinking all labels until they cannot be read.

Run `python3 "<skill-directory>/scripts/check_diagram.py" output.svg` for basic structural checks. The checker verifies XML, IDs, accessible naming, finite positive canvas dimensions, and local reference targets. It rejects active content and obvious external dependencies in its supported static subset. It is not a security sanitizer and does not measure geometry, compute contrast, or detect label collisions.

Render and inspect at the intended delivery size. Verify font fallback, non-Latin labels, marker clipping, and background contrast. Generate raster/PDF exports from the final source with an available renderer; deliver the SVG as well. Do not imply that an independently drawn preview is an exact export of a draw.io source.

## Final layout gate

Run the unified [layout gate](layout-checks.md) on the final SVG/HTML source. It invokes the strict browser audit; annotate connections and boundaries as described in the verification guide. Inspect the preview and repair findings before delivery.
