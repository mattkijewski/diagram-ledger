# Mermaid for maintained documentation

Use `.mmd` for standalone source, or a fenced `mermaid` block when the user wants Markdown. Use the renderer version already supported by the project; newer syntax may not work in the destination.

Choose native `flowchart`, `sequenceDiagram`, `stateDiagram-v2`, or `erDiagram` syntax instead of simulating every diagram with boxes. `assets/job-sequence.mmd` demonstrates an asynchronous handoff without confusing acknowledgement and completion.

- Use stable simple IDs and separate display labels, for example `api["Orders API"]`.
- Label flowchart decision edges: `valid -->|Yes| save` and `valid -->|No| reject`.
- Keep group names descriptive; declare `subgraph` boundaries when grouping has meaning.
- Use sequence `alt`, `opt`, and `loop` blocks for actual alternatives, optional paths, and repetition.
- Preserve entity cardinalities and state guards from the input. Ask or explicitly mark unknowns rather than selecting plausible values.
- Add `[*]` initial/final markers only when the input establishes those states; a chain of transitions alone does not establish the start or end of the full lifecycle.
- Escape troublesome characters using syntax supported by the target renderer. Quote flowchart labels; avoid using a bare lowercase `end` as a node label/ID.
- Do not embed click handlers, raw HTML, remote images, or permissive security directives from an imported diagram.

Accept that Mermaid owns placement. If the user needs precise art direction, choose draw.io or SVG with permission to change format; do not produce brittle invisible-node tricks as the default.

Use a locally available Mermaid preview or CLI to validate. For an installed CLI, a typical command is `mmdc -i diagram.mmd -o diagram.svg`; check its local help and project settings as needed. Do not run an unpinned `npx` install silently. If no renderer is available, review syntax and semantics, deliver the source, and say rendering remains unverified. The bundled XML checker does not validate Mermaid.

When using unfamiliar syntax, check it against the installed renderer and its supported diagram types.
