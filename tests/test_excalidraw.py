"""Broken scenes must fail before the user discovers detached relationships."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/diagram-ledger'
spec = importlib.util.spec_from_file_location('excalidraw_checker', SKILL/'scripts/check_diagram.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class ExcalidrawChecks(unittest.TestCase):
    def setUp(self):
        self.scene = json.loads((SKILL/'assets/review-flow.excalidraw').read_text(encoding='utf-8'))
        self.nodes = {element['id']: element for element in self.scene['elements']}

    def test_native_example_and_unicode(self):
        self.assertEqual(checker.check_excalidraw(self.scene), [])
        self.nodes['draft-label'].update(text='Café 東京', originalText='Café 東京')
        self.assertEqual(checker.check_excalidraw(self.scene), [])

    def test_missing_deleted_and_duplicate_ids(self):
        for mode in ('missing', 'deleted', 'duplicate'):
            with self.subTest(mode=mode):
                scene = copy.deepcopy(self.scene)
                draft = next(e for e in scene['elements'] if e['id'] == 'draft')
                if mode == 'missing':
                    scene['elements'].remove(draft)
                elif mode == 'deleted':
                    draft['isDeleted'] = True
                else:
                    scene['elements'].append(copy.deepcopy(draft))
                self.assertTrue(checker.check_excalidraw(scene))

    def test_detached_label_and_arrow(self):
        for ident in ('draft-label', 'submit'):
            with self.subTest(ident=ident):
                scene = copy.deepcopy(self.scene)
                draft = next(e for e in scene['elements'] if e['id'] == 'draft')
                draft['boundElements'] = [r for r in draft['boundElements'] if r['id'] != ident]
                self.assertTrue(any('reciprocal' in e for e in checker.check_excalidraw(scene)))
        self.nodes['draft-label']['containerId'] = 'published'
        self.assertTrue(checker.check_excalidraw(self.scene))

    def test_native_fixed_point_bindings(self):
        arrow = self.nodes['submit']
        arrow['startBinding'] = dict(elementId='draft', mode='orbit', fixedPoint=[1, 0.5])
        arrow['endBinding'] = dict(elementId='review', mode='orbit', fixedPoint=[0, 0.5])
        self.assertEqual(checker.check_excalidraw(self.scene), [])
        for point in (None, [0], [True, 0], [0, float('nan')], [2, 0]):
            arrow['endBinding']['fixedPoint'] = point
            self.assertTrue(checker.check_excalidraw(self.scene))

    def test_invalid_geometry_and_points(self):
        for value in (float('nan'), float('inf'), '100', True, [], None, 10**400):
            with self.subTest(value=str(value)[:30]):
                scene = copy.deepcopy(self.scene)
                scene['elements'][0]['width'] = value
                self.assertTrue(checker.check_excalidraw(scene))
        for points in ([], [[0, 0]], [[0, 0], [0, 0]], [[2, 0], [130, 0]],
                       [[0, 0], [float('nan'), 2]], [[0, 0], 'bad'], [[0, 0], [999, 0]]):
            self.nodes['submit']['points'] = points
            self.assertTrue(checker.check_excalidraw(self.scene))

    def test_malformed_references_do_not_crash(self):
        for field, value in (('boundElements', [None, {'id': []}]),
                             ('boundElements', 'bad'), ('groupIds', {}),
                             ('startBinding', {'elementId': []}),
                             ('startBinding', []), ('endBinding', {'elementId': 'review', 'focus': {}, 'gap': -1})):
            with self.subTest(field=field, value=value):
                scene = copy.deepcopy(self.scene)
                arrow = next(e for e in scene['elements'] if e['id'] == 'submit')
                arrow[field] = value
                self.assertTrue(checker.check_excalidraw(scene))

    def test_unsupported_features_and_empty_scenes(self):
        for scene in (None, [], {}, {'type': 'excalidraw', 'version': 2, 'appState': {}, 'files': {}, 'elements': []}):
            self.assertTrue(checker.check_excalidraw(scene))
        self.nodes['draft']['type'] = 'image'
        self.assertTrue(any('unsupported' in e for e in checker.check_excalidraw(self.scene)))

    def test_cli_checks_json_and_returns_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'scene.excalidraw'
            for contents, code in ((json.dumps(self.scene), 0), ('{broken', 1), ('[]', 1)):
                path.write_text(contents, encoding='utf-8')
                result = subprocess.run([sys.executable, str(SKILL/'scripts/check_diagram.py'), str(path)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, code, result.stdout + result.stderr)
                self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
