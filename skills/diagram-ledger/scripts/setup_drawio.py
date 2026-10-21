#!/usr/bin/env python3
"""Check the optional local draw.io runtime; download only with --install."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import urllib.request

CONFIG = json.loads(Path(__file__).with_name('drawio-runtime.json').read_text(encoding='utf-8'))


def verified(path):
    return path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == CONFIG['sha256']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', action='store_true', help='Download the pinned official viewer (network access required)')
    parser.add_argument('--viewer', type=Path, help='Custom cache file; also pass this path to render_drawio.mjs')
    args = parser.parse_args()
    target = args.viewer or Path(os.environ.get('DIAGRAM_LEDGER_DRAWIO_VIEWER', str(Path.home()/'.cache/diagram-ledger'/CONFIG['filename'])))
    if verified(target):
        print(f'DRAWIO_RUNTIME_READY: {target}')
        return
    if not args.install:
        parser.exit(2, f'Pinned draw.io runtime missing or checksum differs: {target}\nRun this script with --install to download it. No download attempted.\n')
    # Limit download size and verify before replacing any existing cache file.
    with urllib.request.urlopen(CONFIG['url'], timeout=60) as response:
        data = response.read(20 * 1024 * 1024 + 1)
    if len(data) > 20 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != CONFIG['sha256']:
        raise SystemExit('Runtime verification failed; existing cache left unchanged.')
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as file:
        temporary = Path(file.name)
        file.write(data)
    try:
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    print(f'DRAWIO_RUNTIME_READY: {target}')


if __name__ == '__main__':
    main()
