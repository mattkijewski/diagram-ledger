import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/diagram-ledger/scripts'
MODULES = os.environ.get('DIAGRAM_LEDGER_NODE_MODULES')
VIEWER = os.environ.get('DIAGRAM_LEDGER_DRAWIO_VIEWER')


def fixture(clear=False, html=False, label='', mask=True):
    root = ET.Element('mxfile')
    page = ET.SubElement(root, 'diagram', id='test', name='Routing')
    model = ET.SubElement(page, 'mxGraphModel')
    cells = ET.SubElement(model, 'root')
    ET.SubElement(cells, 'mxCell', id='0')
    ET.SubElement(cells, 'mxCell', id='1', parent='0')
    for ident, x, value in [('a', 30, 'Source'), ('obstacle', 240, '<b>Blocked label</b>' if html else 'Blocked label'), ('b', 450, 'Target')]:
        node = ET.SubElement(cells, 'mxCell', id=ident, parent='1', vertex='1', value=value,
                             style=f'html={int(html)};whiteSpace=wrap;fontSize=16;fillColor=#FFFFFF;strokeColor=#64748B;')
        ET.SubElement(node, 'mxGeometry', x=str(x), y='100', width='140', height='80', **{'as': 'geometry'})
    edge = ET.SubElement(cells, 'mxCell', id='a-to-b', parent='1', edge='1', source='a', target='b', value=label,
                         style='edgeStyle=none;html=0;endArrow=block;fontSize=14;exitX=1;exitY=0.5;entryX=0;entryY=0.5;' + ('labelBackgroundColor=#FFFFFF;' if mask else 'labelBackgroundColor=none;'))
    geometry = ET.SubElement(edge, 'mxGeometry', relative='1', **{'as': 'geometry'})
    if clear:
        points = ET.SubElement(geometry, 'Array', **{'as': 'points'})
        for x, y in [(190, 140), (190, 240), (430, 240), (430, 140)]:
            ET.SubElement(points, 'mxPoint', x=str(x), y=str(y))
    return root


@unittest.skipUnless(shutil.which('node'), 'Node required for geometry checks')
class GeometryChecks(unittest.TestCase):
    def test_segment_intersections_and_container_rules(self):
        source = r'''
import assert from 'node:assert/strict';
import {segmentIntersectsBox as hit,auditLayout} from MODULE;
const box={x:40,y:40,width:20,height:20};
assert(hit({x:0,y:50},{x:100,y:50},box));
assert(hit({x:50,y:0},{x:50,y:100},box));
assert(hit({x:0,y:0},{x:100,y:100},box));
assert(!hit({x:0,y:0},{x:100,y:20},box));
assert(!hit({x:0,y:40},{x:100,y:40},box));
assert(hit({x:0,y:49},{x:100000,y:49},box));
const edge={id:'e',edge:true,source:'a',target:'b',points:[{x:0,y:50},{x:100,y:50}]};
const node={id:'middle',vertex:true,box,label:'Middle',text:box};
let result=auditLayout([edge,node]);assert.equal(result.routeTextCollisions.length,1);assert.equal(result.routeNodeCollisions.length,1);
result=auditLayout([edge,{...node,container:true}]);assert.equal(result.routeTextCollisions.length,1);assert.equal(result.routeNodeCollisions.length,0);
result=auditLayout([{...edge,label:'Own label',text:box,opaqueLabel:true}]);assert.equal(result.routeTextCollisions.length,0);
result=auditLayout([{...edge,label:'Own label',text:box}]);assert.equal(result.routeTextCollisions.length,1);
result=auditLayout([{...edge,curved:true}]);assert.equal(result.unsupported.length,1);
result=auditLayout([{...edge,points:[null,null]}]);assert.equal(result.unsupported.length,1);
'''.replace('MODULE', json.dumps((SCRIPTS/'layout_geometry.mjs').as_uri()))
        result = subprocess.run(['node', '--input-type=module', '-e', source], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_runtime_never_claims_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            file = root/'input.drawio'
            ET.ElementTree(fixture()).write(file, encoding='utf-8')
            result = subprocess.run(['node', str(SCRIPTS/'render_drawio.mjs'), str(file), '--out', str(root/'out'), '--viewer', str(root/'absent.js')], capture_output=True, text=True, timeout=30)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('runtime unavailable', result.stderr)
            self.assertFalse((root/'out/audit.json').exists())


class SetupChecks(unittest.TestCase):
    def test_setup_requires_explicit_download_and_rejects_bad_digest(self):
        spec = importlib.util.spec_from_file_location('setup_drawio', SCRIPTS/'setup_drawio.py')
        setup = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(setup)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/'viewer.js'
            target.write_bytes(b'old cache')
            with patch('sys.argv', ['setup_drawio.py', '--viewer', str(target)]), patch.object(setup.urllib.request, 'urlopen') as request:
                with self.assertRaises(SystemExit):
                    setup.main()
                request.assert_not_called()
            with patch('sys.argv', ['setup_drawio.py', '--viewer', str(target), '--install']), patch.object(setup.urllib.request, 'urlopen') as request:
                request.return_value.__enter__.return_value.read.return_value = b'corrupted download'
                with self.assertRaises(SystemExit):
                    setup.main()
                self.assertEqual(target.read_bytes(), b'old cache')


@unittest.skipUnless(os.environ.get('DIAGRAM_LEDGER_BROWSER_TESTS') == '1', 'optional native browser tests')
class DrawioBrowserChecks(unittest.TestCase):
    def render(self, document):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            file = root/'input.drawio'
            if isinstance(document, str):
                file.write_text(document, encoding='utf-8')
            else:
                ET.ElementTree(document).write(file, encoding='utf-8')
            baseline = file.read_bytes()
            cmd = ['node', str(SCRIPTS/'render_drawio.mjs'), str(file), '--out', str(root/'audit'), '--browser', 'chrome']
            if MODULES:
                cmd += ['--modules', MODULES]
            if VIEWER:
                cmd += ['--viewer', VIEWER]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
            report = root/'audit/audit.json'
            self.assertTrue(report.exists(), result.stderr)
            audit = json.loads(report.read_text(encoding='utf-8'))
            self.assertEqual(audit['sourceSha256'], hashlib.sha256(baseline).hexdigest())
            self.assertEqual(file.read_bytes(), baseline)
            if audit['status'] == 'pass':
                repeat = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                self.assertNotEqual(repeat.returncode, 0)
                self.assertIn('EEXIST', repeat.stderr)
                self.assertEqual(json.loads(report.read_text(encoding='utf-8')), audit)
            for page in audit['pages']:
                self.assertTrue((root/'audit'/page['preview']).stat().st_size > 0)
                self.assertTrue((root/'audit'/page['svg']).stat().st_size > 0)
            return result.returncode, audit

    def test_crossing_detected_with_cell_ids(self):
        code, audit = self.render(fixture())
        self.assertEqual(code, 1, audit)
        findings = audit['pages'][0]
        self.assertIn({'edge': 'a-to-b', 'label': 'obstacle', 'text': 'Blocked label'}, findings['routeTextCollisions'])
        self.assertIn({'edge': 'a-to-b', 'node': 'obstacle'}, findings['routeNodeCollisions'])

    def test_repaired_route_passes(self):
        code, audit = self.render(fixture(clear=True))
        self.assertEqual(code, 0, audit)
        self.assertEqual(audit['status'], 'pass')

    def test_rich_html_label_crossing_detected(self):
        code, audit = self.render(fixture(html=True))
        self.assertEqual(code, 1, audit)
        self.assertTrue(any(i['label'] == 'obstacle' for i in audit['pages'][0]['routeTextCollisions']), audit)

    def test_masked_own_label_passes_but_unmasked_fails(self):
        code, audit = self.render(fixture(clear=True, label='Calls API'))
        self.assertEqual(code, 0, audit)
        code, audit = self.render(fixture(clear=True, label='Calls API', mask=False))
        self.assertEqual(code, 1, audit)
        self.assertTrue(any(i['label'] == 'a-to-b' for i in audit['pages'][0]['routeTextCollisions']), audit)

    def test_transparent_label_background_does_not_hide_collision(self):
        document = fixture(clear=True, label='Calls API', mask=False)
        edge = document.find('.//mxCell[@edge="1"]')
        edge.set('style', edge.get('style').replace('labelBackgroundColor=none', 'labelBackgroundColor=transparent'))
        code, audit = self.render(document)
        self.assertEqual(code, 1, audit)
        self.assertTrue(audit['pages'][0]['routeTextCollisions'])

    def test_curved_and_hidden_geometry_cannot_claim_clean(self):
        for change in ('curved', 'hidden'):
            document = fixture(clear=True)
            if change == 'curved':
                edge = document.find('.//mxCell[@edge="1"]')
                edge.set('style', edge.get('style') + 'curved=1;')
            else:
                document.find('.//mxCell[@id="obstacle"]').set('visible', '0')
            code, audit = self.render(document)
            self.assertEqual(code, 1, audit)
            self.assertTrue(audit['pages'][0]['unsupported'], audit)

    def test_all_pages_checked_with_repeated_cell_ids(self):
        document = fixture(clear=True)
        second = fixture().find('diagram')
        second.set('id', 'second')
        document.append(second)
        code, audit = self.render(document)
        self.assertEqual(code, 1, audit)
        self.assertEqual(len(audit['pages']), 2)
        self.assertFalse(audit['pages'][0]['routeTextCollisions'])
        self.assertTrue(audit['pages'][1]['routeTextCollisions'])

    def test_nested_container_example_passes(self):
        code, audit = self.render((ROOT/'skills/diagram-ledger/assets/service-map.drawio').read_text(encoding='utf-8'))
        self.assertEqual(code, 0, audit)
        self.assertIn('backend', audit['pages'][0]['containers'])

    def test_compressed_or_invalid_xml_fails_closed(self):
        for source in ['<mxfile><diagram>compressed</diagram></mxfile>', '<mxfile><diagram>']:
            code, audit = self.render(source)
            self.assertEqual(code, 1, audit)
            self.assertEqual(audit['status'], 'error')
            self.assertTrue(audit['errors'])

    def test_remote_content_does_not_pass_or_execute(self):
        document = fixture(clear=True, html=True)
        document.find('.//mxCell[@id="obstacle"]').set('value', '<img src="https://example.com/no-upload" onerror="document.body.dataset.executed=1">')
        code, audit = self.render(document)
        self.assertNotEqual(code, 0, audit)
        self.assertTrue(audit['blockedRequests'] or audit['errors'], audit)


if __name__ == '__main__':
    unittest.main()
