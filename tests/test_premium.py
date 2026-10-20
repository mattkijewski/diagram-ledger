import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/diagram-ledger'
spec = importlib.util.spec_from_file_location('checker2', SKILL/'scripts/check_diagram.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class HtmlChecks(unittest.TestCase):
    def check(self, content):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory)/'diagram.html'
            file.write_text(content, encoding='utf-8')
            return checker.check(file)

    def test_html_doctype_and_inline_svg(self):
        svg = (SKILL/'assets/review-flow.svg').read_text(encoding='utf-8')
        self.assertEqual(self.check('<!DOCTYPE html><html><body>'+svg+'</body></html>'), [])

    def test_multiple_svg_and_broken_second(self):
        svg = (SKILL/'assets/review-flow.svg').read_text(encoding='utf-8')
        self.assertTrue(self.check(svg + '<svg><path></svg>'))

    def test_html_active_content(self):
        svg = (SKILL/'assets/review-flow.svg').read_text(encoding='utf-8')
        for bad in ['<script>alert(1)</script>', '<img src="https://example.com/a.png">',
                    '<body onload="alert(1)">', '<style>@import "remote.css";</style>']:
            with self.subTest(bad=bad):
                self.assertTrue(self.check(bad + svg))

    def test_empty_and_truncated_html(self):
        self.assertTrue(self.check('<html><p>Not a diagram</p></html>'))
        self.assertTrue(self.check('<svg><text>Missing close'))


@unittest.skipUnless(os.environ.get('DIAGRAM_LEDGER_BROWSER_TESTS') == '1', 'optional browser tests: set DIAGRAM_LEDGER_BROWSER_TESTS=1')
class BrowserChecks(unittest.TestCase):
    def render(self, bad=False, boundary_bad=False):
        # Same graph: either a clean route or an outward arrow crossing a third node.
        route = 'M180 130 H290 V250 H270' if bad else 'M180 130 H240'
        target_x, target_y = (240, 220) if bad else (240, 100)
        extra = '<g data-node="block"><rect data-body="" x="210" y="115" width="45" height="30" fill="white"/></g><text x="210" y="135" font-size="16">Collision</text>' if bad else ''
        boundary_bottom = 140 if boundary_bad else 190
        boundary = f'<g data-container="region"><rect data-body="" x="35" y="60" width="170" height="{boundary_bottom-60}" fill="none" stroke="gray"/></g>'
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="500" height="360" viewBox="0 0 500 360" role="img" aria-labelledby="t d">
        <title id="t">Routing test</title><desc id="d">Two connected nodes.</desc>
        <rect width="500" height="360" fill="white"/>
        {boundary}<g data-node="a" data-within="region"><rect data-body="" x="60" y="100" width="120" height="60" fill="white" stroke="black"/><text x="90" y="138" font-size="16">Source</text></g>
        <g data-node="b" data-outside="region"><rect data-body="" x="{target_x}" y="{target_y}" width="120" height="60" fill="white" stroke="black"/><text x="{target_x+25}" y="{target_y+38}" font-size="16">Target</text></g>
        {extra}<path data-edge="ab" data-from="a" data-to="b" d="{route}" fill="none" stroke="black"/>
        </svg>'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            file = root/'fixture.svg'
            file.write_text(svg, encoding='utf-8')
            command = ['node', str(SKILL/'scripts/render.mjs'), str(file), '--out', str(root/'render'), '--browser', 'chrome', '--strict', 'yes']
            modules=os.environ.get('DIAGRAM_LEDGER_NODE_MODULES')
            if modules:
                command += ['--modules', modules]
            result=subprocess.run(command, capture_output=True, text=True, timeout=60)
            audit_file=root/'render/audit.json'
            self.assertTrue(audit_file.exists(), result.stderr)
            audit=json.loads(audit_file.read_text(encoding='utf-8'))
            return result.returncode, audit

    def test_clean_control_passes(self):
        code,audit=self.render(False)
        self.assertEqual(code,0,audit)
        self.assertEqual(audit['svgs'][0]['annotatedEdgeIssues'],[])

    def test_partial_containment_fails(self):
        code,audit=self.render(boundary_bad=True)
        self.assertNotEqual(code,0)
        issues=audit['svgs'][0]['containerIssues']
        self.assertTrue(any(i['node']=='a' and 'not fully inside' in i['problem'] for i in issues),issues)

    def test_route_collision_and_wrong_direction_fail(self):
        code,audit=self.render(True)
        self.assertNotEqual(code,0)
        issues=audit['svgs'][0]['annotatedEdgeIssues']
        self.assertTrue(any(i['problem']=='route crosses unrelated node' for i in issues), issues)
        self.assertTrue(any(i['problem']=='final segment points away from target' for i in issues), issues)
        self.assertTrue(audit['svgs'][0]['routeTextCollisions'],audit)


if __name__ == '__main__':
    unittest.main()
