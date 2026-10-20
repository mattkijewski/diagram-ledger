import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills' / 'diagram-ledger'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


checker = module('checker', SKILL / 'scripts' / 'check_diagram.py')
installer = module('installer', ROOT / 'install.py')


class DiagramChecks(unittest.TestCase):
    def mutated(self, filename, before, after):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / filename
            content = (SKILL / 'assets' / filename).read_text(encoding='utf-8')
            self.assertIn(before, content)
            destination.write_text(content.replace(before, after), encoding='utf-8')
            return checker.check(destination)

    def test_working_examples(self):
        for filename in ('service-map.drawio', 'review-flow.svg'):
            with self.subTest(filename=filename):
                self.assertEqual(checker.check(SKILL / 'assets' / filename), [])

    def test_missing_endpoint(self):
        errors = self.mutated('service-map.drawio', 'target="orders-store"', 'target="missing"')
        self.assertTrue(any('target must reference' in error for error in errors))

    def test_duplicate_id(self):
        errors = self.mutated('service-map.drawio', 'id="client"', 'id="orders-api"')
        self.assertTrue(any('duplicate cell id' in error for error in errors))

    def test_parent_cycle(self):
        errors = self.mutated('service-map.drawio', 'vertex="1" parent="backend"', 'vertex="1" parent="orders-api"')
        self.assertTrue(any('parent cycle' in error for error in errors))

    def test_nonfinite_dimensions(self):
        errors = self.mutated('service-map.drawio', 'width="208"', 'width="NaN"')
        self.assertTrue(any('finite and positive' in error for error in errors))

    def test_svg_accessible_description(self):
        errors = self.mutated('review-flow.svg', 'review-title review-desc', 'review-title')
        self.assertTrue(any('nonempty desc' in error for error in errors))

    def test_missing_svg_marker(self):
        errors = self.mutated('review-flow.svg', 'url(#review-arrow)', 'url(#absent)')
        self.assertTrue(any('Missing referenced SVG id' in error for error in errors))

    def test_svg_external_and_active_content(self):
        for payload in ('<script>alert(1)</script>', '<image href="https://example.org/image.png"/>',
                        '<style>@import "https://example.org/font.css";</style>'):
            with self.subTest(payload=payload):
                self.assertTrue(self.mutated('review-flow.svg', '</svg>', payload + '</svg>'))

    def test_unicode_and_xml_escaping(self):
        self.assertEqual(self.mutated('service-map.drawio', 'Web client', 'Café &amp; 東京'), [])
        self.assertEqual(self.mutated('review-flow.svg', 'Submit draft', 'Café &amp; 東京'), [])

    def test_unsupported_and_malformed_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            for name, content in (
                ('compressed.drawio', '<mxfile><diagram>compressed-data</diagram></mxfile>'),
                ('broken.svg', '<svg'),
                ('flow.mmd', 'flowchart LR\nA-->B'),
                ('empty.drawio', '<mxfile/>'),
                ('entity.svg', '<!DOCTYPE svg><svg/>'),
            ):
                path = Path(directory) / name
                path.write_text(content, encoding='utf-8')
                self.assertTrue(checker.check(path), name)


class InstallChecks(unittest.TestCase):
    def test_update_preserves_modified_copy_outside_discovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            destination=root/'.claude/skills/diagram-ledger'
            installer.install(SKILL,[destination])
            (destination/'custom-note.txt').write_text('keep my changes', encoding='utf-8')
            installer.install(SKILL,[destination],update=True)
            backups=list((root/'.claude/skill-backups').glob('diagram-ledger-*'))
            self.assertEqual(len(backups),1)
            self.assertEqual((backups[0]/'custom-note.txt').read_text(encoding='utf-8'),'keep my changes')
            self.assertFalse((destination/'custom-note.txt').exists())
            self.assertEqual(list((root/'.claude/skills').iterdir()),[destination])

    def test_copy_and_dry_run(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'project with spaces'
            destinations = [root / '.claude/skills/diagram-ledger', root / '.cursor/skills/diagram-ledger']
            installer.install(SKILL, destinations, dry_run=True)
            self.assertFalse(root.exists())
            installer.install(SKILL, destinations)
            for destination in destinations:
                self.assertEqual((destination / 'SKILL.md').read_bytes(), (SKILL / 'SKILL.md').read_bytes())
                self.assertTrue((destination / 'scripts/check_diagram.py').is_file())
                self.assertFalse(list(destination.rglob('__pycache__')))

    def test_preflight_preserves_existing_install(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first, second = root / 'new', root / 'existing'
            second.mkdir()
            sentinel = second / 'custom.txt'
            sentinel.write_text('my changes', encoding='utf-8')
            with self.assertRaises(ValueError):
                installer.install(SKILL, [first, second])
            self.assertFalse(first.exists())
            self.assertEqual(sentinel.read_text(encoding='utf-8'), 'my changes')

    def test_copy_failure_removes_partial_installs(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / 'new'
            with patch.object(installer.shutil, 'copytree', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    installer.install(SKILL, [destination])
            self.assertFalse(destination.exists())


if __name__ == '__main__':
    unittest.main()
