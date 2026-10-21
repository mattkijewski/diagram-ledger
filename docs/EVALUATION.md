# Validation and scope

This document describes checks for Diagram Ledger 3.2.2. Automated tests, model behavior and native application compatibility are separate forms of evidence.

## Automated checks

The regression suite covers diagram structure, malformed input, element bindings, revision preservation, required outcomes, installer backups and rollback, gallery rebuilding and Unicode handling. Label-encoding cases cover single XML escaping, HTML labels, JSON Unicode strings, visibly over-escaped text and the explicit exception for intentional entity-code examples. Optional browser tests check measured rendering, route collisions and containment.

Release verification checks local references, example sources, bundled revision receipts, archive contents and SHA-256 fingerprints. The build produces reproducible skill and portable ZIPs. GitHub CI runs core checks on Linux with Python 3.9 and 3.14, Windows with Python 3.14, and browser checks on Linux. Consult the release notes and CI result for the exact release's outcome.

## Workflows exercised

- Claude sessions exercised an architecture brainstorm from an incomplete game idea through accepted changes, diagram revisions, notes updates and a fresh-session handoff. Corrective feedback was needed and connection interruptions occurred; this is not evidence of unattended reliability.
- A personal Claude installation generated a multi-format bundle inside a separate repository. Source checks do not establish equivalent rendering in every destination.
- The included Excalidraw scene was inspected in its editor. Moving a node preserved its attached label and connected arrows; undo restored the position. This check covers the included example, not all generated scenes.
- The gallery contains teaching examples with editable sources and revision receipts. They demonstrate the utilities; they are not a record of autonomous model performance.

## Known limits

Native Cursor execution remains untested. Utility tests on Windows do not establish native Claude or Cursor behavior on that platform. Lucidchart and SmartDraw import/editability checks remain pending; their destinations are beta, and SmartDraw covers basic flowcharts only.

Automated revision receipts cover supported uncompressed draw.io and annotated standalone SVG sources. Other formats require retained sources, a manual change record and native visual review. Source checks do not prove that a diagram correctly models a system, that labels fit, or that a destination app preserves the source.

Model behavior varies with the prompt, model and available tools. Development trials were reviewed by the same assistant involved in building the skill. They are limited observations, not an independent reliability study.
