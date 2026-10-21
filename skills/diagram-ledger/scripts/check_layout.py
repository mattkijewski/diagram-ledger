#!/usr/bin/env python3
"""Check every selected output; pending native imports never count as a visual pass."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import check_diagram

SCRIPTS = Path(__file__).resolve().parent
FORMATS = {'.drawio': 'drawio', '.excalidraw': 'excalidraw', '.mmd': 'mermaid', '.md': 'mermaid', '.svg': 'svg', '.html': 'svg', '.htm': 'svg', '.vson': 'smartdraw'}


def check_one(source, destination, output, modules=None, browser='chrome', viewer=None):
    record = {'input': str(source.resolve()), 'destination': destination, 'status': 'error', 'sourceLayout': 'unverified', 'errors': [], 'renderers': []}
    output.mkdir()
    try:
        data = source.read_bytes()
        record['sourceSha256'] = hashlib.sha256(data).hexdigest()
        if len(data) > 10 * 1024 * 1024:
            raise ValueError('Source exceeds 10 MiB.')
        fmt = FORMATS.get(source.suffix.lower())
        if not fmt:
            raise ValueError('Unsupported extension; use drawio, excalidraw, mmd, Markdown Mermaid, svg/html or vson.')
        inferred = 'lucidchart' if fmt == 'drawio' and source.stem.lower().endswith('-lucidchart') else fmt
        destination = inferred if destination == 'auto' else destination
        record['destination'] = destination
        if destination != fmt and not (destination == 'lucidchart' and fmt == 'drawio'):
            raise ValueError(f'{destination} destination does not accept this {fmt} source.')
        structural = [] if fmt == 'mermaid' else check_diagram.check(source)
        record['structure'] = 'renderer-parser' if fmt == 'mermaid' else ('fail' if structural else 'pass')
        if structural:
            record.update(status='fail', errors=structural)
            return record
        if fmt == 'smartdraw':
            record.update(status='native-check-required', reason='VSON has no authoritative local layout; SmartDraw places its objects during import. Inspect the actual imported diagram before claiming visual verification.')
            return record
        sources = [source]
        if source.suffix.lower() == '.md':
            blocks = re.findall(r'^```mermaid[^\n]*\n(.*?)^```\s*$', data.decode('utf-8-sig'), re.M | re.S)
            if not blocks:
                raise ValueError('Markdown contains no fenced Mermaid diagrams.')
            sources = []
            for index, block in enumerate(blocks, 1):
                file = output/f'mermaid-{index}.mmd'
                file.write_text(block, encoding='utf-8')
                sources.append(file)
        for index, rendered_source in enumerate(sources, 1):
            script = 'render_drawio.mjs' if fmt == 'drawio' else 'render_scene.mjs' if fmt in ('mermaid', 'excalidraw') else 'render.mjs'
            render_output = output/f'render-{index}'
            command = ['node', str(SCRIPTS/script), str(rendered_source.resolve()), '--out', str(render_output.resolve()), '--browser', browser]
            if modules:
                command += ['--modules', str(Path(modules).resolve())]
            if fmt == 'svg':
                command += ['--strict', 'yes']
            if fmt == 'drawio' and viewer:
                command += ['--viewer', str(Path(viewer).resolve())]
            result = subprocess.run(command, capture_output=True, text=True, timeout=180)
            report_file = render_output/'audit.json'
            detail = json.loads(report_file.read_text(encoding='utf-8')) if report_file.is_file() else None
            record['renderers'].append({'source': str(rendered_source.resolve()), 'report': str(report_file.resolve()), 'exitCode': result.returncode})
            if result.returncode != 0 or detail is None or detail.get('status', 'pass') != 'pass':
                record.update(status='fail' if detail else 'unverified', sourceLayout='fail' if detail else 'unverified')
                record['errors'].append((result.stderr or result.stdout or 'Renderer failed; inspect its report.')[-4000:])
            elif not record['errors']:
                record['sourceLayout'] = 'pass'
        if record['errors']:
            return record
        # Detect concurrent changes while rendering rather than endorsing a stale source.
        if hashlib.sha256(source.read_bytes()).hexdigest() != record['sourceSha256']:
            raise ValueError('Source changed during verification; rerun against the final source.')
        record['status'] = 'native-check-required' if destination == 'lucidchart' else 'pass'
        if destination == 'lucidchart':
            record['reason'] = 'The draw.io import source passed. Lucidchart may change its layout; inspect the actual imported document before claiming destination verification.'
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        record['errors'].append(str(error))
        record['status'] = 'unverified'
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='+', type=Path)
    parser.add_argument('--out', required=True, type=Path, help='New output directory; existing paths are rejected')
    parser.add_argument('--destination', choices=['auto', 'drawio', 'excalidraw', 'mermaid', 'svg', 'lucidchart', 'smartdraw'], default='auto')
    parser.add_argument('--modules', default=os.environ.get('DIAGRAM_LEDGER_NODE_MODULES'))
    parser.add_argument('--browser', choices=['chrome', 'chromium'], default='chrome')
    parser.add_argument('--viewer', default=os.environ.get('DIAGRAM_LEDGER_DRAWIO_VIEWER'))
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.mkdir()
    results = [check_one(source, args.destination, args.out/f'output-{index}', args.modules, args.browser, args.viewer) for index, source in enumerate(args.files, 1)]
    summary = {'status': 'pass' if all(r['status'] == 'pass' for r in results) else 'not-fully-verified', 'outputs': results,
               'limits': 'A source layout pass needs image and semantic review. Native Lucidchart and SmartDraw imports require checks inside those applications. A pass in one format never verifies another.'}
    (args.out/'audit.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
    for result in results:
        print(f"{result['status'].upper()}: {result['destination']} — {result['input']}")
    print(f"BUNDLE_LAYOUT_{'PASS' if summary['status'] == 'pass' else 'INCOMPLETE'}: {args.out/'audit.json'}")
    return 0 if summary['status'] == 'pass' else 1


if __name__ == '__main__':
    sys.exit(main())
