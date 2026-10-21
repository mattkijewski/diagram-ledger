# Test the Lucidchart and SmartDraw beta imports

Included in **3.4.0** as beta import workflows. Structural checks pass; import fidelity and editability in Lucidchart/SmartDraw remain unverified. Use this guide to test the samples and your generated diagrams in the destination apps.

## 1. Try the prepared samples first

Both samples describe exactly four nodes and four directed relationships:

| From | To | Label |
| --- | --- | --- |
| Draft | Review | Submit |
| Review | Published | Approved |
| Review | Revise | Needs edits |
| Revise | Draft | Return to draft |

### Lucidchart

Sample: [review-flow-lucidchart.drawio](../skills/diagram-ledger/assets/imports/review-flow-lucidchart.drawio).

1. Open the sample in draw.io/diagrams.net, inspect it, then save/export a `.drawio` copy. Use that saved copy for import.
2. In Lucidchart's Documents page, select **+ New → Import documents** and import that copy.
3. Confirm all four nodes and four labeled arrows. Edit “Review” to “Editorial review,” move that node, and confirm the connectors stay attached.

A free Lucidchart account can import/view; editing imported documents requires a paid plan. A plan restriction is not proof of a failed file. Do not start a paid plan just for this test unless you want one.

### SmartDraw

Sample: [review-flow-smartdraw.vson](../skills/diagram-ledger/assets/imports/review-flow-smartdraw.vson).

1. Open a blank SmartDraw drawing. Choose **+ → Insert Content → Add Data Visualization → VisualScript**.
2. Upload the `.vson` sample. This is the VisualScript import route, not image insertion.
3. Check the four nodes and arrows against the table. Edit “Review,” move a node and confirm the diagram remains editable. SmartDraw chooses the positions; compare meaning rather than identical coordinates.

The sample uses `ShapeConnector`; existing files may use `ShapeList`. If the importer rejects the file or omits branches, retain the file and exact error for investigation rather than accepting a partial diagram.

## 2. Test generation in Claude Code or Cursor

Download the [3.4.0 portable ZIP](https://github.com/mattkijewski/diagram-ledger/releases/download/v3.4.0/diagram-ledger-portable.zip), extract it and run the installer from its `diagram-ledger-package` directory:

```sh
python3 install.py --target both --scope user --update
```

Use `py -3` on Windows. `--update` backs up the previous installation. Open the project you want to diagram in Claude Code or Cursor and start a new session.

First test the menu:

```text
/diagram-ledger Draw a content review workflow: Draft goes to Review.
Approved reviews go to Published. Reviews needing edits go to Revise,
which returns to Draft. Ask me which output I want before drawing.
```

Expect seven numbered choices (six destinations plus All formats) in ordinary chat text, without a separate selection widget or a second menu. Reply **5** or **Lucidchart**, or **6** or **SmartDraw**. It should create only the selected source and explain the import steps.

Without specifying a filename, confirm the result goes under the active project's `diagrams/content-review-flow/` with a descriptive name such as `content-review-flow-lucidchart.drawio` or `content-review-flow-smartdraw.vson`. It must not write into the installed skill. Previews and revision evidence belong inside that subject folder too.

Also test **7** or **all** on the same four-node flow. Expect six sources (including the separately named Lucidchart `.drawio`), `model.json` and a `README.md` index in one subject folder. Compare all four nodes and four labeled relationships across every source. An unavailable renderer or pending native import must remain marked as such.

To test use from another repo, install the personal Claude copy, start a fresh Claude session in a separate repository with no project-specific skill, and request that flow in all formats. Confirm the bundle is created in that repository, without installing a project copy there. Repeat with a single format to check the same folder convention.

If an already-open session still shows the old four-choice menu, choose **Type something** and enter `Lucidchart` or `SmartDraw`, or restart the session to reload the updated skill. To update a personal installation used outside this project, run `python3 install.py --target claude --scope user --update` from the package folder.

Then test direct selection:

```text
/diagram-ledger Create a SmartDraw flowchart for that review process.
Save diagrams/content-review-flow/content-review-flow-smartdraw.vson, check its structure and give me import steps.
```

```text
/diagram-ledger Create that review process for Lucidchart.
Save diagrams/content-review-flow/content-review-flow-lucidchart.drawio and give me the import steps.
```

Import each generated result and repeat the editing checks above. These tests evaluate actual agent output in addition to the prepared fixture.

## 3. Record the destination-app results

| Check | Lucidchart | SmartDraw |
| --- | --- | --- |
| Sample imports without errors | Pending | Pending |
| Four nodes and four correct labeled arrows | Pending | Pending |
| Text editable; moved node keeps connections | Pending | Pending |
| Generated file imports and preserves requested meaning | Pending | Pending |

Record any error text, missing labels/connections or unexpected layout behavior. Automated checks validate the local source only. Draw.io receipts cannot prove Lucidchart conversion fidelity; SmartDraw's VSON has no automated revision receipts.

To rebuild and verify the release archives from a source checkout:

```sh
python3 scripts/build_import_examples.py
python3 scripts/build_release.py
python3 scripts/verify_release.py
```

## Brainstorming regression checks

Use a separate empty project and start with a vague game idea. Expect a meaningful discovery question before the format menu. Supply an offline, single-player brief with an undecided engine and choose SVG so both receipts and local render checks can be exercised.

After the first draft, ask “What if we added online co-op?” Check that it remains an unaccepted alternative and that the current diagram is unchanged. Then accept a concrete architecture change, such as inserting a Save Manager between state and storage. Check the new relationships, preserved original source, notes, and revision receipt.

Start a fresh session, point to the saved brainstorm folder, and request a narrow rename. It should recover the current source and known constraints from the files, retain the selected format and engine uncertainty, and update the notes without inventing requirements. Test a visual polish turn too: it must create a receipt covering the final source, not reuse a receipt from before the polish.

For each delivered revision, verify that the final source hash matches a passing receipt, the current-source link in the notes resolves, and the final strict render audit has no unresolved actionable findings. Retain failed attempts in test evidence. This workflow needs actual model execution; static skill validation alone does not test conversational behavior.
