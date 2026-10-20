# Webhook delivery · a revision study

**Brief:** Rename Dispatcher to Delivery worker. Add a quarantine inside the delivery platform for events rejected by the worker, with a directed worker → quarantine connection labeled “rejected”. Preserve every other ID, relationship, coordinate, style and page setting.

This example demonstrates a controlled revision, not a complete production architecture. It makes no claim about retries, durability of the quarantine or exactly-once delivery. The unused lower portion of the original platform is deliberate room for an extension.

| Format | Original | Revised | Contract | Generated receipt |
| --- | --- | --- | --- | --- |
| SVG | [before.svg](svg/before.svg) | [after.svg](svg/after.svg) | [contract](svg/contract.json) | [receipt](svg/receipt/index.html) |
| draw.io | [before.drawio](drawio/before.drawio) | [after.drawio](drawio/after.drawio) | [contract](drawio/contract.json) | [receipt](drawio/receipt/index.html) |

Each receipt records three allowed changes: one label change, one added node, one added edge. Required assertions verify the renamed label, the new node's ownership and the new connection's direction and label. Existing geometry and styles remain identical. The original sources, revised sources and contract are included in each receipt and bound to SHA-256 fingerprints.

**Try breaking it:** move an existing node, change an unrelated fill, reverse the new edge or omit the rename. Re-run `scripts/revision.py check` with the original contract and a fresh output directory. The check must fail. Do not regenerate the baseline to make it pass.

For a normal revision, create the contract from the request before editing. The repository's deterministic example builder produces the documented final demonstration pair; it is not evidence that Claude performed this edit.
