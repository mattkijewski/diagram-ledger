#!/usr/bin/env python3
"""Verify complete references, source examples, archives and optional installed copies."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SKILL=ROOT/'skills/diagram-ledger'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--installed',action='store_true')
parser.add_argument('--dist',type=Path,default=ROOT/'dist',help='Archive directory (use dist/preview for local betas)')
args=parser.parse_args()
files=sorted(p for p in SKILL.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and p.name!='.DS_Store')
text=(SKILL/'SKILL.md').read_text(encoding='utf-8')
assert re.match(r'---\nname: diagram-ledger\ndescription: [^\n]+\n',text), 'Missing skill discovery fields'
for file in files:
    if file.suffix=='.md':
        for target in re.findall(r'\]\(([^)]+)\)',file.read_text(encoding='utf-8')):
            if '://' not in target and not target.startswith('#'):
                assert (file.parent/target.split('#')[0]).is_file(), f'Missing reference {file}: {target}'
spec=importlib.util.spec_from_file_location('release_checker',SKILL/'scripts/check_diagram.py')
checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
for file in (SKILL/'assets').rglob('*'):
    if file.suffix in ('.svg','.drawio','.excalidraw','.vson'):
        assert not checker.check(file),(file,checker.check(file))
# Recompute every shipped receipt from its retained inputs and contract.
spec=importlib.util.spec_from_file_location('release_revision',SKILL/'scripts/revision.py')
revision=importlib.util.module_from_spec(spec);spec.loader.exec_module(revision)
for report_file in (SKILL/'assets/revision').rglob('report.json'):
    folder=report_file.parent;recorded=json.loads(report_file.read_text(encoding='utf-8'));fmt=recorded['format']
    actual=revision.compare(revision.snapshot(folder/('before.'+fmt)),revision.snapshot(folder/('after.'+fmt)),json.loads((folder/'contract.json').read_text(encoding='utf-8')))
    assert actual==recorded and actual['status']=='pass',f'Stale or failing receipt: {report_file}'
if args.installed:
    for app in ('claude','cursor'):
        installed_root=ROOT/f'.{app}/skills/diagram-ledger'
        installed_files={p.relative_to(installed_root).as_posix() for p in installed_root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
        assert installed_files=={p.relative_to(SKILL).as_posix() for p in files},f'Unexpected installed files: {app}'
        assert not (ROOT/f'.{app}/skills/diagram-craft').exists(),f'Old name still active: {app}'
        for file in files:
            target=ROOT/f'.{app}/skills/diagram-ledger'/file.relative_to(SKILL)
            assert target.is_file() and target.read_bytes()==file.read_bytes(),f'Stale or missing installed file: {target}'
manifest=json.loads((args.dist/'manifest.json').read_text(encoding='utf-8'))
for item in manifest:
    path=args.dist/item['file']
    assert hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256'],f'Archive hash mismatch: {path}'
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist())==item['entries']
        assert not any('/benchmarks/' in name or '__pycache__' in name for name in archive.namelist())
        base='diagram-ledger/' if item['file']=='diagram-ledger-skill.zip' else 'diagram-ledger-package/skills/diagram-ledger/'
        for file in files:
            assert archive.read(base+file.relative_to(SKILL).as_posix())==file.read_bytes(),f'Stale packaged file: {file}'
print(f'DIAGRAM_LEDGER_RELEASE_VERIFIED: {len(files)} skill files, {len(manifest)} archives')
