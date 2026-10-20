# Precision for common technical diagrams

## Architecture and deployment

Containment is a claim. Every inside node must fit wholly within the boundary, including its bottom/right edge, with visible padding. Every outside node must be fully outside. A caption cannot correct contradictory geometry. Use the container annotations and measurements in [verification.md](verification.md) for SVG. Inventory each node's owner, runtime/network scope, and managed/external status independently. Nest only the dimension the boundary names. A managed database or object store must not drift inside a network box simply because it needs room near the application.

Choose a dominant flow and assign ranks, then reserve a separate corridor for storage access, monitoring, and feedback edges. Place storage where both producers and consumers have visible access without routing through other services. A central bus is appropriate only if the system actually has a shared bus. Crossing lines do not imply a junction unless explicitly marked.

For each edge, write the source, target, and verb before drawing. “Worker polls Queue” is Worker→Queue; “Queue delivers job to Worker” is Queue→Worker. Do not mix request direction with payload direction without labels that distinguish them. Use endpoint-specific ports, and inspect the final segment of every routed connection.

On a required single canvas with many nodes, use sensible regions, a taller canvas, and route corridors. Preserve every required component and relationship. Larger diagrams need more space, not smaller labels or arbitrary deletions.

## Flowchart

Place the successful path on a clear vertical or horizontal axis. Put exception outcomes alongside their decision; put correction/retry routes outside the main flow. Reserve those outside lanes before placing the first node.

Each decision is a question with labeled outcomes. Make the label close enough to its outgoing segment that it cannot be mistaken for a neighboring branch. A Yes/No label belongs outside the diamond, not on top of its border. Diamonds often need more width than rectangular nodes for the same text; inspect the actual diagonal boundary, not only its bounding box.

Preserve responsibility named in the brief. “Finance checks evidence” should remain “Finance: check evidence” or sit in an explicitly labeled Finance lane; shortening it to “Check evidence” alone loses ownership. The same applies to approval roles, handoffs, and operator actions.

Route a loop back to the precise step named by the brief. Do not return to a nearby review step when the intended behavior restarts submission. Show terminal rejections as endings; do not invent an outgoing connection to make the layout symmetrical.

## Sequence

Use fixed participant columns, time downward, participant headers, and visible lifelines. Messages connect lifelines rather than the header cards. Allocate row heights based on label wrapping and nested fragments. Reserve a left gutter for fragment labels.

Use an enclosing `alt` fragment with a clear divider for mutually exclusive branches. Put branch guards in each region. Place a retry wholly inside the successful-refresh branch; a message below the fragment runs after either branch and changes the meaning. A self-message or explicit local-action box can show display/navigation behavior.

Differentiate requests from responses consistently (for example solid vs dashed) and name the convention. Arrow direction carries sender/receiver meaning even when the line is dashed. Show acceptance separately from eventual completion for asynchronous work.

## Logical ER and physical schema

Use [the explicit-cardinality example](../assets/data-model.svg) as the starting notation when text endpoint labels are allowed. Before drawing, transcribe each supplied relationship into a small table: entity A, cardinality at A, entity B, cardinality at B. Compare every rendered endpoint against that table after drawing. This is a semantic check, not a geometry check.

Use entity/table boxes with a name band and field rows. Align the field names and mark keys beside fields. Preserve composite keys: two fields independently marked PK belong to one composite primary key; clarify that with a concise note when ambiguity is likely.

Put relationship cardinality adjacent to its endpoint. Default to explicit `1`, `0..*`, and `1..*` labels when the user allows either labels or crow's-foot notation. Custom crow's-foot drawing adds avoidable opportunities to invert optionality; use it when required or when following an existing valid notation. Never invent abbreviations such as `*.1`. Add a short legend if notation needs explanation. Keep enough edge length between the cardinality labels and entity borders.

For “each Order has one Customer; a Customer has zero or many Orders,” put `1` at Customer and `0..*` at Order. For “an Order has one or many OrderItems,” the item endpoint is `1..*`, not `0..*`. A many-to-many join entity preserves both foreign-key relationships; do not also draw a direct association that implies a different model.

Logical diagrams may omit physical indexes and types; physical schemas must preserve supplied types, constraints, and nullable foreign keys. Do not invent unspecified multiplicity or schema constraints.
