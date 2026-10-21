# Diagrams for Confluence

Confluence is a publishing destination. Keep the chosen editable source and all generated exports under the project's `diagrams/<subject-and-view>/` folder with matching descriptive stems.

## Choose the route

- **draw.io:** recommended when the team has the draw.io Confluence app. Produce `.drawio`; use the installed app's editor to import it and embed the resulting diagram. This supports editing through the integration.
- **Lucidchart:** use when the team already works in Lucid. Follow [lucidchart.md](lucidchart.md) to prepare and verify the beta import first, then embed the imported document through the Lucidchart integration. Confluence Cloud integration requires a Lucid Team or Enterprise plan and admin configuration.
- **No diagram app:** provide a PNG exported from the selected source and the editable source itself. The user inserts the PNG into the page and attaches the source for later editing. The image is a static preview; replace it after source changes.

Do not add Confluence as a separate format choice or require another diagram tool for Confluence. Honor an explicitly requested format or project preference. When the user delegates the choice, use draw.io; if the integration is unknown, explain both the app and attachment routes without blocking local generation.

## Prepare the handoff

1. Save the source, for example `diagrams/payment-service-architecture/payment-service-architecture.drawio`.
2. For an attachment workflow, export `diagrams/payment-service-architecture/exports/drawio/payment-service-architecture.png` using the native app or an available compatible renderer. Inspect it at the page's intended width. If export is unavailable, deliver the source and explain how to export PNG; do not claim a preview was generated.
3. Supply a short caption and meaningful alt text in the delivery message. State whether the page will show an editable integration or a static preview.
4. Give instructions for the selected route. For Confluence Cloud attachments, `/images` or `/files` opens the insertion flow. For configured Lucid integration, insert **Lucidchart Diagrams**, select the imported document and choose appropriate access settings.

Creating local files does not itself publish them to Confluence. Upload or edit a page only when the user requests that action. Do not claim the integration was tested merely because the source passed local checks.

These instructions cover Confluence Cloud. For Data Center, use the installed app's matching documentation rather than assuming Cloud menus or plan requirements apply.

## Final layout gate

Apply the [layout gate](layout-checks.md) to the selected source format before publishing, then inspect the actual Confluence embed or attached preview at its displayed width. A local source pass does not prove that an integration or scaled page display stays readable.
