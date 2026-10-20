# Pick a visual grammar

Use the row closest to the reader's question. These are semantic checks, not templates that determine the content.

Read [technical-patterns.md](technical-patterns.md) for architecture, flowchart, sequence, and data-model diagrams where precise notation or routing matters.

| Question | Diagram | Preserve and verify |
| --- | --- | --- |
| What components interact? | Architecture / data flow | Component roles, direction, protocol or payload where supplied, scope boundaries. Define whether arrows mean data movement, calls, or dependencies. |
| Where does it run? | Deployment | Environments, hosts, services, network/trust boundaries. Separate hosted resources from the software that runs on them. |
| What happens next? | Flowchart | Start/end, actions, decisions with labeled outcomes, reachable exits, exception paths. Do not add retry loops unless supported. |
| Who talks to whom over time? | Sequence | Participants, chronological message order, requests versus responses, alternative/optional/loop fragments. A queue acknowledgement is not job completion. |
| Which condition is the object in? | State machine | States, triggers, guards, actions, initial/final states, valid transitions. Actions are not automatically states. |
| How does the data relate? | ER / schema | Entities, key fields, optionality, cardinality, foreign-key direction. Confirm unspecified cardinalities instead of guessing. Distinguish logical models from physical schemas. |
| Who owns each step? | Swimlane | One consistent ownership dimension per lane, ordered actions, handoffs, branch outcomes. A lane boundary is not elapsed time. |
| When does it happen? | Timeline / Gantt | Dates, durations, dependencies, units, timezone when relevant. If timing is unknown use an ordered process instead of a proportional axis. |
| What contains or reports to what? | Tree / organization map | Parent relationships, ownership/reporting meaning, shared nodes. Use a graph if an item has several parents; do not duplicate it without indicating identity. |
| How do these ideas connect? | Concept map / loop | Named relationships, hierarchy or feedback direction. A circular arrangement alone does not establish causality. |
| What changes between versions? | Before/after | Stable object identity, aligned layout, explicit added/removed/changed labels. Include rewired edges as changes, not only recolored nodes. |

## Complex cases

An overview may abstract a subsystem into one node if the detailed view preserves its internals and external connections. Explain what was collapsed. Do not omit an error branch, security boundary, or relationship cardinality merely to simplify the page.

For quantitative diagrams (Sankey, funnel, chart), use supplied values and correct proportional encoding. Verify totals, units, time range, and scale. If values are unavailable, use a labeled conceptual process rather than invented proportions. This skill does not provide a statistical chart renderer.

For imported diagrams, inventory each page separately. Retain source identifiers when practical. Record a compact list of intentional changes and unsupported features; do not silently flatten subgraphs, sequence fragments, annotations, or hyperlinks that matter to the request.
