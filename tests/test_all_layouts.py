import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT/'skills/diagram-ledger/scripts'
ASSETS = ROOT/'skills/diagram-ledger/assets'
sys.path.insert(0, str(SCRIPTS))
import check_layout

MODULES = os.environ.get('DIAGRAM_LEDGER_NODE_MODULES')


class DestinationChecks(unittest.TestCase):
    def test_smartdraw_requires_native_layout_even_with_valid_source(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(check_layout.subprocess, 'run') as render:
                result = check_layout.check_one(ASSETS/'imports/review-flow-smartdraw.vson', 'auto', Path(folder)/'audit')
            self.assertEqual(result['status'], 'native-check-required')
            self.assertEqual(result['structure'], 'pass')
            self.assertEqual(result['sourceLayout'], 'unverified')
            render.assert_not_called()

    def test_mixed_bundle_never_claims_all_pass_and_does_not_skip_later_files(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)/'audit'
            command = [sys.executable, str(SCRIPTS/'check_layout.py'), str(ASSETS/'imports/review-flow-smartdraw.vson'), str(Path(folder)/'missing.drawio'), '--out', str(out)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 1)
            report = json.loads((out/'audit.json').read_text())
            self.assertEqual(report['status'], 'not-fully-verified')
            self.assertEqual(len(report['outputs']), 2)
            self.assertEqual(report['outputs'][0]['status'], 'native-check-required')
            self.assertEqual(report['outputs'][1]['status'], 'unverified')

    def test_destination_extension_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            result = check_layout.check_one(ASSETS/'review-flow.excalidraw', 'smartdraw', Path(folder)/'audit')
            self.assertEqual(result['status'], 'unverified')
            self.assertTrue(result['errors'])

    def test_missing_runtime_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(check_layout.subprocess, 'run', side_effect=FileNotFoundError('node unavailable')):
                result = check_layout.check_one(ASSETS/'review-flow.excalidraw', 'auto', Path(folder)/'audit')
            self.assertEqual(result['status'], 'unverified')


@unittest.skipUnless(os.environ.get('DIAGRAM_LEDGER_BROWSER_TESTS') == '1', 'optional cross-format browser checks')
class NativeFormatChecks(unittest.TestCase):
    def render(self, text, suffix):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root/('diagram'+suffix)
            source.write_text(text, encoding='utf-8')
            baseline = source.read_bytes()
            command = ['node', str(SCRIPTS/'render_scene.mjs'), str(source), '--out', str(root/'render'), '--browser', 'chrome']
            if MODULES:
                command += ['--modules', MODULES]
            process = subprocess.run(command, capture_output=True, text=True, timeout=120)
            report = root/'render/audit.json'
            self.assertTrue(report.exists(), process.stderr)
            result = json.loads(report.read_text(encoding='utf-8'))
            self.assertEqual(result['sourceSha256'], hashlib.sha256(baseline).hexdigest())
            self.assertEqual(source.read_bytes(), baseline)
            if result['status'] == 'pass':
                self.assertTrue((root/'render/preview.png').is_file())
                self.assertTrue((root/'render/diagram.svg').is_file())
                self.assertFalse(result['blockedRequests'])
            return process.returncode, result

    def test_excalidraw_clean_native_example(self):
        code, report = self.render((ASSETS/'review-flow.excalidraw').read_text(), '.excalidraw')
        self.assertEqual(code, 0, report)
        self.assertEqual(report['findings']['edgeCount'], 4)

    def test_excalidraw_local_handwritten_font(self):
        scene = json.loads((ASSETS/'review-flow.excalidraw').read_text())
        for element in scene['elements']:
            if element['type'] == 'text':
                element['fontFamily'] = 1
        code, report = self.render(json.dumps(scene), '.excalidraw')
        self.assertEqual(code, 0, report)

    def test_excalidraw_crossing_text_is_detected(self):
        scene = json.loads((ASSETS/'review-flow.excalidraw').read_text())
        arrow = next(e for e in scene['elements'] if e['id'] == 'submit')
        label = next(e for e in scene['elements'] if e['id'] == 'submit-note')
        label.update(x=arrow['x']+30, y=arrow['y']-10)
        code, report = self.render(json.dumps(scene), '.excalidraw')
        self.assertEqual(code, 1, report)
        self.assertTrue(any(i['label'] == 'submit-note' for i in report['findings']['routeTextCollisions']), report)

    def test_excalidraw_crossing_unrelated_node_is_detected(self):
        scene = json.loads((ASSETS/'review-flow.excalidraw').read_text())
        arrow = next(e for e in scene['elements'] if e['id'] == 'approve')
        arrow.update(points=[[0, 0], [-150, 0], [-150, 230], [130, 230], [130, 0]], width=280, height=230)
        code, report = self.render(json.dumps(scene), '.excalidraw')
        self.assertEqual(code, 1, report)
        self.assertTrue(any(i['node'] == 'revise' for i in report['findings']['routeNodeCollisions']), report)

    def test_mermaid_four_families_render_and_measure_routes(self):
        sources = [
            'flowchart LR\n A[Source] -->|Calls API| B[Target]',
            (ASSETS/'job-sequence.mmd').read_text(),
            'stateDiagram-v2\n Draft --> Published: Approve',
            'erDiagram\n CUSTOMER ||--o{ ORDER : places',
        ]
        for source in sources:
            with self.subTest(family=source.splitlines()[0]):
                code, report = self.render(source, '.mmd')
                self.assertEqual(code, 0, report)
                self.assertGreater(report['findings']['edgeCount'], 0, report)

    def test_mermaid_native_label_mask_does_not_hide_unrelated_crossings(self):
        code = r"""
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import fs from 'node:fs/promises';
import path from 'node:path';
import {measureScene} from MEASURE;
import {auditLayout} from GEOMETRY;
const req=createRequire(MODULES ? path.join(MODULES,'_test.cjs') : SCRIPT);
const {chromium}=req('playwright');
let root=path.dirname(req.resolve('mermaid'));
while(!await fs.stat(path.join(root,'package.json')).then(()=>true,()=>false))root=path.dirname(root);
const browser=await chromium.launch({channel:'chrome'});
try {
 const page=await browser.newPage();
 await page.route('**/*',route=>route.abort());
 await page.setContent('<main id="scene"></main>');
 await page.addScriptTag({path:path.join(root,'dist/mermaid.js')});
 await page.evaluate(async()=>{
  mermaid.initialize({startOnLoad:false,securityLevel:'strict',theme:'neutral',htmlLabels:false,themeCSS:'.edgeLabel .background {opacity:1 !important;}'});
  document.querySelector('#scene').innerHTML=(await mermaid.render('test','flowchart LR\nA[Source] -->|Calls API| B[Target]')).svg;
 });
 let measured=await page.evaluate(measureScene,{format:'mermaid'});
 assert.equal(auditLayout(measured.states).routeTextCollisions.length,0);
 await page.evaluate(()=>document.querySelector('.edgeLabel .background').style.setProperty('opacity','0','important'));
 measured=await page.evaluate(measureScene,{format:'mermaid'});
 assert(auditLayout(measured.states).routeTextCollisions.some(c=>c.text==='Calls API'));
 // A background only protects its own edge. A second native route through the
 // same label must still be diagnosed, even with the backplate restored.
 await page.evaluate(()=>{
  document.querySelector('.edgeLabel .background').style.setProperty('opacity','1','important');
  const route=document.querySelector('.flowchart-link').cloneNode(true);
  route.id='unrelated';route.setAttribute('data-id','unrelated');
  document.querySelector('.flowchart-link').parentNode.appendChild(route);
 });
 measured=await page.evaluate(measureScene,{format:'mermaid'});
 assert(auditLayout(measured.states).routeTextCollisions.some(c=>c.edge==='unrelated'&&c.text==='Calls API'));
}finally{await browser.close();}
"""
        for token, value in [('MEASURE', (SCRIPTS/'measure_scene.mjs').as_uri()), ('GEOMETRY', (SCRIPTS/'layout_geometry.mjs').as_uri()), ('MODULES', MODULES), ('SCRIPT', str(SCRIPTS/'render_scene.mjs'))]:
            code = code.replace(token, json.dumps(value))
        result = subprocess.run(['node', '--input-type=module', '-e', code], capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_mermaid_invalid_and_embedded_configuration_fail(self):
        for source in ['flowchart LR\n A[broken', '%%{init: {"securityLevel":"loose"}}%%\nflowchart LR\nA-->B', 'pie\n"A":2']:
            code, report = self.render(source, '.mmd')
            self.assertEqual(code, 1, report)
            self.assertTrue(report['errors'])

    def test_unified_svg_html_markdown_and_import_source_status(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            svg = root/'view.svg'
            svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="400" height="120" viewBox="0 0 400 120" role="img" aria-labelledby="t d"><title id="t">Example</title><desc id="d">A readable label</desc><text x="30" y="60" font-size="18">A readable label</text></svg>')
            html = root/'view.html'
            html.write_text('<!doctype html><html><body>'+svg.read_text()+'</body></html>')
            markdown = root/'view.md'
            markdown.write_text('```mermaid\nflowchart LR\nA[First]-->B[Second]\n```\n\n```mermaid\nstateDiagram-v2\nDraft --> Ready\n```\n')
            for index, file in enumerate([svg, html, markdown, ASSETS/'imports/review-flow-lucidchart.drawio']):
                result = check_layout.check_one(file, 'auto', root/f'audit-{index}', MODULES)
                expected = 'native-check-required' if file.suffix == '.drawio' else 'pass'
                self.assertEqual(result['status'], expected, result)
                self.assertEqual(result['sourceLayout'], 'pass', result)
                if file.suffix == '.md':
                    self.assertEqual(len(result['renderers']), 2)

    def test_svg_crossing_fails_unified_gate(self):
        source = '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="150" viewBox="0 0 400 150" role="img" aria-labelledby="t d"><title id="t">Crossing</title><desc id="d">A line crossing a label</desc><text x="130" y="80" font-size="18">Blocked label</text><path data-route="" d="M20 75 H350" stroke="black" fill="none"/></svg>'
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            file = root/'crossing.svg'
            file.write_text(source)
            result = check_layout.check_one(file, 'auto', root/'audit', MODULES)
            self.assertEqual(result['status'], 'fail', result)
            self.assertEqual(result['structure'], 'pass', result)
            self.assertTrue(result['renderers'], result)


if __name__ == '__main__':
    unittest.main()
