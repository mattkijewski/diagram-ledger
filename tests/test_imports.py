import copy
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
spec = importlib.util.spec_from_file_location('import_checker', SKILL/'scripts/check_diagram.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class ImportChecks(unittest.TestCase):
    def setUp(self):
        self.source = SKILL/'assets/imports/review-flow-smartdraw.vson'
        self.scene = json.loads(self.source.read_text(encoding='utf-8'))

    def test_examples_encode_the_same_graph(self):
        self.assertEqual(checker.check(self.source), [])
        lucid = SKILL/'assets/imports/review-flow-lucidchart.drawio'
        self.assertEqual(checker.check(lucid), [])
        labels, edges = {}, []

        def visit(node):
            labels[node['ID']] = node['Label']
            for branch in node.get('ShapeConnector', []):
                previous = node['ID']
                for child in branch['Shapes']:
                    edges.append((previous, child['ID'], child.get('LineLabel', '')))
                    visit(child)
                    previous = child['ID']
        visit(self.scene['Shape'])
        edges += [(r['StartID'], r['EndID'], r['Label']) for r in self.scene['Returns']]
        vson_graph = {(labels[a], labels[b], label) for a, b, label in edges}
        cells = {c.get('id'): c for c in ET.parse(lucid).findall('.//mxCell')}
        lucid_graph = {(cells[c.get('source')].get('value'), cells[c.get('target')].get('value'), c.get('value'))
                       for c in cells.values() if c.get('edge') == '1'}
        self.assertEqual(vson_graph, lucid_graph)
        self.assertEqual(vson_graph, {('Draft', 'Review', 'Submit'), ('Review', 'Published', 'Approved'),
                                     ('Review', 'Revise', 'Needs edits'), ('Revise', 'Draft', 'Return to draft')})

    def test_missing_and_duplicate_ids(self):
        self.scene['Returns'][0]['EndID'] = 999
        self.assertTrue(checker.check_vson(self.scene))
        self.scene['Returns'][0]['EndID'] = 1
        self.scene['Shape']['ShapeConnector'][0]['Shapes'][0]['ID'] = 1
        self.assertTrue(any('Duplicate' in e for e in checker.check_vson(self.scene)))

    def test_both_connector_spellings_and_ambiguity(self):
        node = self.scene['Shape']
        node['ShapeList'] = node.pop('ShapeConnector')
        self.assertEqual(checker.check_vson(self.scene), [])
        node['ShapeConnector'] = []
        self.assertTrue(checker.check_vson(self.scene))

    def test_branch_and_property_mistakes_fail(self):
        for field, value in (('Direction', 'East'), ('Shapes', []), ('Shapes', None),
                             ('ShapeConnectorType', 'Unknown'), ('EndArrow', '1')):
            scene = copy.deepcopy(self.scene)
            scene['Shape']['ShapeConnector'][0][field] = value
            self.assertTrue(checker.check_vson(scene), field)
        self.scene['Shape']['ShapeConnectors'] = []
        self.assertTrue(any('unsupported field' in e for e in checker.check_vson(self.scene)))

    def test_bad_values_and_unsupported_documents(self):
        for value in (None, [], {}, {'Version': '1.0', 'Template': 'Floorplan'}):
            self.assertTrue(checker.check_vson(value))
        for field, value in (('ID', True), ('ID', []), ('Label', None),
                             ('MinWidth', float('nan')), ('MinHeight', -1),
                             ('ShapeConnector', [None]), ('ShapeConnector', {})):
            scene = copy.deepcopy(self.scene)
            scene['Shape'][field] = value
            self.assertTrue(checker.check_vson(scene))
        for value in (None, [None], [{'StartID': [], 'EndID': True}]):
            scene = copy.deepcopy(self.scene)
            scene['Returns'] = value
            self.assertTrue(checker.check_vson(scene))

    def test_cli_failure_status(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'scene.vson'
            for content, status in ((json.dumps(self.scene), 0), ('{broken', 1), ('[]', 1)):
                path.write_text(content, encoding='utf-8')
                result = subprocess.run([sys.executable, str(SKILL/'scripts/check_diagram.py'), str(path)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, status, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
