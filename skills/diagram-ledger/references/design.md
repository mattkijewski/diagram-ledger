# Visual decisions

## A calm technical default

Use a neutral canvas, clear sans-serif type, deliberate spacing, and strong relationship labels. The diagram should work in grayscale. An explicit user style can replace these defaults.

| Role | Light default | Dark alternative |
| --- | --- | --- |
| Canvas | `#F8FAFC` | `#111827` |
| Surface | `#FFFFFF` | `#1F2937` |
| Primary text | `#172033` | `#F9FAFB` |
| Secondary text | `#475569` | `#CBD5E1` |
| Important boundary / connector | `#64748B` | `#94A3B8` |
| Emphasis | `#155E75` | `#67E8F9` |
| Emphasis surface | `#ECFEFF` | `#164E63` |

Use the light palette unless the surrounding document or user asks for dark. Do not switch colors solely because the subject is technical. Accent light surfaces with dark emphasis text; on a dark emphasis surface use the dark palette's light emphasis text. Avoid using colors across palettes without checking their contrast.

Use system sans-serif (`Arial, Helvetica, sans-serif`) for labels and headings. Use monospace only where preserving technical tokens helps. Defaults at native canvas scale: title 28–32 px, node names 16–18 px, edge labels 14–16 px, secondary labels 14 px. Adjust for the intended output size: a 1200 px graphic shown at 600 px halves every label. A large drawing may need a detail view rather than smaller text.

Start with an 8 px spacing rhythm, 16–24 px node padding, 48–80 px between connected nodes, and at least 32 px outer margins. These are starting points; arrow labels and content determine actual spacing. A 1.5–2 px stroke and 6 px corner radius work for ordinary technical components. Use standard notation where a shape carries meaning.

## Hierarchy and routing

- Write a title that tells the reader what is being explained. Use a subtitle only for scope, date, or a material assumption.
- Align peers; give each group a named boundary and enough padding to separate its children from its heading.
- Label boundaries with their meaning, such as “Production network” or “Owned by Billing.” Never draw a generic box that mixes deployment and ownership implicitly.
- Prefer short orthogonal connections for architecture and flowcharts. Use straight or curved paths where the diagram's notation calls for them, such as tree branches or loop diagrams.
- Put labels near the relationship they describe with a clear text background or sufficient whitespace. Avoid repeated lines that share the same track and hide endpoints.
- Reserve a heading strip inside each container that routes cannot cross. Keep labels at least 6 px from their route; offset a label beside a vertical segment instead of centering it across the segment. If a label must sit on a route, draw an opaque mask after the route and before the text.
- Leave enough visible line between connected shapes for the arrowhead and its label. Adjacent/touching shapes cannot communicate a directed transition reliably.
- Use distinct ports or attachment positions for several connections to the same side of a shape.
- Reserve an outer route for a feedback loop. Do not make a return path look like the main forward path.
- Make uncertain/proposed items explicit with text. Do not overload one dashed style to mean asynchronous, optional, external, and uncertain at once.
- Use a legend only for encodings a reader cannot infer from labels or standard notation.

## Accessibility and exports

Target at least 4.5:1 text contrast for ordinary text and 3:1 for essential graphical marks against their adjacent background. If tokens change, calculate contrast or use a contrast checker; a familiar-looking palette is not proof. Give status a word or symbol as well as a color. Avoid red/green as the only distinction.

Provide an accessible title and meaningful description for SVG. For other formats, supply a short textual explanation with the delivery. Keep text as text unless the user specifically needs outlined fonts. Use Unicode as real text, not vendor-specific icon fonts.

Export only after layout review. Check that transparent backgrounds will remain readable in the destination. Keep legend, notes, and arrowheads inside the export bounds. No animation is necessary for a good static explanation.
