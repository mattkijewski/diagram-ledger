"""Displayed label text must survive the correct XML/HTML/JSON decode layers."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT/'skills/diagram-ledger'
spec = importlib.util.spec_from_file_location('label_checker', SKILL/'scripts/check_diagram.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class LabelEncodingChecks(unittest.TestCase):
    def drawio(self, label, html=False):
        root = ET.parse(SKILL/'assets/service-map.drawio').getroot()
        cell = root.find(".//mxCell[@id='client']")
        cell.set('value', label)
        cell.set('style', 'html=1;' if html else 'html=0;')
        return root

    def test_unicode_and_single_xml_escape_are_valid(self):
        text = 'Core — API • worker → storage & logs < 5'
        xml = ET.tostring(self.drawio(text), encoding='unicode')
        self.assertIn('&amp; logs &lt; 5', xml)
        self.assertEqual(checker.check_drawio(ET.fromstring(xml)), [])
        for encoded in ('&#8212;', '&#x2014;'):
            self.assertEqual(checker.check_drawio(ET.fromstring(xml.replace('—', encoded))), [])

    def test_double_escaped_plain_labels_fail(self):
        for text in ('Core &#8212; API', 'Core &#x2014; API', 'A &amp; B', 'A &bull; B', 'A &#8594; B'):
            with self.subTest(text=text):
                parsed = ET.fromstring(ET.tostring(self.drawio(text)))
                self.assertTrue(any('literal entity text' in e for e in checker.check_drawio(parsed)))

    def test_html_labels_decode_only_one_html_layer(self):
        good = '<b>Core &#8212; API &amp; logs &lt; 5</b>'
        self.assertEqual(checker.check_drawio(ET.fromstring(ET.tostring(self.drawio(good, html=True)))), [])
        bad = '<b>Core &amp;#8212; API &amp;amp; logs</b>'
        self.assertTrue(any('literal entity text' in e for e in checker.check_drawio(ET.fromstring(ET.tostring(self.drawio(bad, html=True))))))

    def test_svg_and_inline_svg_text(self):
        root = ET.parse(SKILL/'assets/review-flow.svg').getroot()
        node = root.find('.//{http://www.w3.org/2000/svg}text')
        node.text = 'A — B & C'
        self.assertEqual(checker.check_svg(ET.fromstring(ET.tostring(root))), [])
        node.text = 'A &#8212; B &amp; C'
        ET.register_namespace('', 'http://www.w3.org/2000/svg')
        content = ET.tostring(root, encoding='unicode')
        with tempfile.TemporaryDirectory() as folder:
            for extension, source in (('svg', content), ('html', '<!doctype html>'+content)):
                path = Path(folder)/('diagram.'+extension)
                path.write_text(source, encoding='utf-8')
                self.assertTrue(any('literal entity text' in e for e in checker.check(path)))

    def test_json_labels_are_plain_text(self):
        scene = json.loads((SKILL/'assets/review-flow.excalidraw').read_text(encoding='utf-8'))
        label = next(e for e in scene['elements'] if e['type']=='text')
        vson = json.loads((SKILL/'assets/imports/review-flow-smartdraw.vson').read_text(encoding='utf-8'))
        for text, broken in [('A — B & C', False), ('A &#8212; B &amp; C', True)]:
            label.update(text=text, originalText=text)
            vson['Shape']['Label'] = text
            # JSON's Unicode escapes must decode before inspecting labels.
            errors = checker.check_excalidraw(json.loads(json.dumps(scene, ensure_ascii=True)))
            self.assertEqual(bool(errors), broken)
            self.assertEqual(bool(checker.check_vson(vson)), broken)

    def test_intentional_literal_entities_do_not_bypass_structure(self):
        root = self.drawio('Example: &#8212;')
        self.assertEqual(checker.check_drawio(root, allow_literal_entities=True), [])
        root.find(".//mxCell[@id='client']").set('parent', 'missing')
        self.assertTrue(any('missing parent' in e for e in checker.check_drawio(root, allow_literal_entities=True)))
        self.assertEqual(checker.label_encoding_errors('R&D &unknownEntity;', 'label'), [])

    def test_cli_fails_without_changing_source(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'example.drawio'
            data = ET.tostring(self.drawio('Example: &#8212;'))
            path.write_bytes(data)
            command = [sys.executable, str(SKILL/'scripts/check_diagram.py'), str(path)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stdout+result.stderr)
            self.assertIn('literal entity text', result.stdout)
            allowed = subprocess.run(command+['--allow-literal-entities'], capture_output=True, text=True)
            self.assertEqual(allowed.returncode, 0, allowed.stdout+allowed.stderr)
            self.assertEqual(path.read_bytes(), data)


if __name__ == '__main__':
    unittest.main()
