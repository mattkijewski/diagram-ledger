# Explore an idea through diagrams

Use this workflow when the user wants a thinking partner for a new project or an evolving architecture. The idea can be a game, application, workflow, physical process or another system. Do not require a repository full of code, a finished specification or a technology choice before helping.

## Discover just enough

Reflect the idea briefly, then ask the one question whose answer most changes the design. Use what the user has already told you; do not repeat answered questions or front-load a questionnaire. Offer a few concrete options when helpful, without forcing the user to pick from them.

For “I want to build a game,” a useful first question is what players do or whether they play alone or together. Which question matters most depends on the brief. Do not assume multiplayer servers, accounts, purchases, an engine or a cloud provider. Separate the player/gameplay loop from software architecture when both views are useful.

Recommend a small starting design when enough is known. Explain significant alternatives in terms of the user's goal, complexity and tradeoffs. Mark proposals and assumptions explicitly. Verify current product-specific capabilities or pricing through available official sources if those claims are needed; otherwise stay at the conceptual level. A recommendation becomes an accepted decision only when the user's reply supports it.

## Discuss → sketch → revise

- **Explore:** answer questions and compare alternatives in conversation. “What if we added co-op?” requests exploration; it does not automatically change the accepted design. Keep alternatives separate and named if drawn.
- **Sketch:** when a drawing would help and the user has asked to build the diagram together, create a small draft using known requirements and explicitly labeled assumptions. Ask the normal format question only if still unresolved, then wait for the answer. Do not require a complete specification or another approval round once drawing is authorized.
- **Revise:** act on accepted changes such as “Let's add co-op” or “Remove accounts.” Explain the affected components and relationships, then update the diagram using the revision workflow. Preserve stable IDs and unaffected layout. A discussion-only turn does not need a new diagram version.

After a meaningful update, link the current diagram, briefly state what changed and identify the next consequential open question. Ask it only if useful; do not keep the conversation going with a mandatory question when the user wants a finished handoff. Honor “just discuss,” “draw it now,” “choose for me,” or “finish this version.”

## Keep the working context with the diagram

Once saving a draft or when the user asks to save the brainstorm, use the normal `diagrams/<subject-and-view>/` folder. Keep a concise `brainstorm.md` beside the source with:

- The project's goal, audience and known constraints.
- Accepted decisions and their reasons.
- Proposals, assumptions and unresolved questions, clearly separated from decisions.
- A short record of material changes, including superseded decisions.
- Relative links to the current diagram, any named alternatives and the next useful step.

Use this as a maintained summary, not a verbatim transcript. Include it in the bundle index when there is one. Purely conversational exploration does not require filesystem output.

Keep the notes as grounded as the drawing. An accepted decision must be traceable to something the user stated or accepted; preserve its level of specificity. “Desktop” does not establish Windows, macOS and Linux support, and a puzzle game does not establish a “relaxing” target audience. Put such suggestions under proposals or open questions, while keeping the user's explicit desktop requirement accepted. When reviewing notes, correct unsupported claims instead of carrying them into later sessions.

Before handing off a saved update, check that the notes link to the latest source, relative links resolve, component names match the diagram, and superseded decisions are clearly historical. If the notes contain an inventory, copy IDs from the current source; a renamed display label does not rename the stable ID in either the diagram or the notes. Keep validation status accurate: a preservation receipt can pass while the visual audit still fails.

On “continue this brainstorm,” read that folder's notes and current sources before asking the next question. Reconcile them with the latest user message and any manual edits. If several brainstorms could match, ask which one. Context persists through these files, not a promise of memory across unrelated chats or machines; the user must bring the folder when moving work.

## Keep formats and meaning in sync

Use the chosen format throughout the conversation; do not repeat the chooser at each revision. If all formats were selected, follow [all-formats.md](all-formats.md) for shared inventory, consistency and unsupported outputs. You may suggest using one working format while exploring, but do not silently narrow the user's all-format choice.

Use [revision.md](revision.md) for actual source changes, with immutable baselines and supported receipts. Keep alternate proposals separate from the current design until selected. A proposed component must remain visibly proposed even if it appears in a polished draft. Brainstorming and drawing do not themselves authorize implementing the application, installing dependencies or provisioning services.

## Example conversation

User: “Help me brainstorm a game. I want to build the architecture as we talk.”

Assistant: “What kind of game do you have in mind, and what would the player do most of the time?”

User: “A single-player farming game for desktop. It should work offline.”

Assistant: Propose a small local design around input, game rules, world state, rendering and local saves, labeled as a proposal. Explain that offline play does not establish a need for a backend. Ask for the output format before the first drawing if none is set.

User: “Use Excalidraw. Start there.”

Assistant: Create the draft and notes in `diagrams/farming-game-architecture/`. Keep unchosen engine details open.

User: “What would change if we supported co-op later?”

Assistant: Explain the design implications and alternatives without treating co-op as accepted or replacing the current offline design.

User: “Keep it offline for now. Add a mod-loading boundary.”

Assistant: Revise the current diagram narrowly, record the decision and preserve the earlier source.
