# Example collection

Choose an example by the problem it teaches; replace its domain rather than treating it as a universal template.

| Example | What to learn |
| --- | --- |
| [Revision study](revision/README.md) | Preserve an owner's drawing, allow only requested edits, and verify required outcomes with exact source fingerprints. Includes SVG and native draw.io. |
| [Service map](service-map.drawio) | Native editable shapes, nested ownership and orthogonal connections. |
| [Review flow](review-flow.svg) | Decision branches, return paths and text that stays readable. |
| [Excalidraw review flow](review-flow.excalidraw) | Native whiteboard shapes with attached labels, bound arrows and an explicit revision loop. |
| [Lucidchart import test](imports/review-flow-lucidchart.drawio) | Simple native draw.io source for the beta Lucidchart import workflow; destination testing pending. |
| [SmartDraw import test](imports/review-flow-smartdraw.vson) | Basic VisualScript flowchart with a return edge; destination testing pending. |
| [Data model](data-model.svg) | Precise PK/FK notation, relationship multiplicity and a join entity. |
| [Publish sequence](publish-sequence.mmd) | Idempotent request handling plus asynchronous outbox delivery; acknowledgement and failure are distinct branches. |
| [Job sequence](job-sequence.mmd) | A smaller sequence starting point. |
| [Project style](style.example.md) | Project-specific typography, color and notation without changing the installed skill. |

All architectures are illustrative. The publish sequence is a proposed design, not a claim about an existing system. A real implementation also needs atomic uniqueness enforcement for concurrent request keys, claim expiration and retry policy; add these when they are part of the requested view. A timeout does not prove the subscriber failed to receive an event.
