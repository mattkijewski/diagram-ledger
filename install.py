#!/usr/bin/env python3
"""Copy Diagram Ledger into Claude Code and/or Cursor skill directories.

Python 3.9+, no dependencies. Updates require --update and preserve backups.
"""
import argparse
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def install(source, destinations, dry_run=False, update=False):
    if not (source / 'SKILL.md').is_file():
        raise ValueError(f'Missing source skill: {source}')
    # Preflight every destination before making any copies.
    for destination in destinations:
        if destination.is_symlink():
            raise ValueError(f'Refusing to replace a symlink: {destination}')
        if destination.exists() and not update:
            raise ValueError(f'Already exists: {destination}. Back up/move this skill folder before reinstalling.')
        if destination.exists() and not (destination.is_dir() and (destination/'SKILL.md').is_file()):
            raise ValueError(f'Refusing to replace a non-skill path: {destination}')
        if source.resolve() == destination.resolve() or source.resolve() in destination.resolve().parents:
            raise ValueError('Cannot install a skill inside itself.')
    legacy_paths = []
    for destination in destinations:
        legacy = destination.with_name('diagram-craft')
        if destination.name == 'diagram-ledger' and (legacy.exists() or legacy.is_symlink()):
            if not update:
                raise ValueError(f'Previous Diagram Craft installation found: {legacy}. Use --update to migrate with a backup.')
            if legacy.is_symlink() or not legacy.is_dir() or not (legacy/'SKILL.md').is_file():
                raise ValueError(f'Refusing to migrate an unrecognized path: {legacy}')
            if not re.search(r'^name: diagram-craft\s*$', (legacy/'SKILL.md').read_text(encoding='utf-8'), re.M):
                raise ValueError(f'Refusing to migrate a different skill: {legacy}')
            legacy_paths.append(legacy)
    created = []
    staged = []
    backups = []
    try:
        for destination in destinations:
            print(f'{"Would install" if dry_run else "Installing"}: {destination}')
            if not dry_run:
                destination.parent.mkdir(parents=True, exist_ok=True)
                stage=Path(tempfile.mkdtemp(prefix='.diagram-ledger-stage-',dir=destination.parent))
                staged.append((stage,destination))
                shutil.copytree(source, stage, dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store'))
        for legacy in legacy_paths:
            print(f'{"Would back up" if dry_run else "Backing up previous name"}: {legacy}')
            if not dry_run:
                backup_root=legacy.parent.parent/'skill-backups'
                backup_root.mkdir(exist_ok=True)
                timestamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
                backup=backup_root/f'diagram-craft-{timestamp}'
                legacy.rename(backup)
                backups.append((backup,legacy))
        for stage,destination in staged:
            if destination.is_symlink() or (destination.exists() and not update):
                raise ValueError(f'Destination changed during installation: {destination}')
            if destination.exists():
                # Keep backups outside the skills directory to avoid duplicate discovery.
                backup_root=destination.parent.parent/'skill-backups'
                backup_root.mkdir(exist_ok=True)
                timestamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
                backup=backup_root/f'diagram-ledger-{timestamp}'
                destination.rename(backup)
                backups.append((backup,destination))
                print(f'Previous installation preserved: {backup}')
            stage.rename(destination)
            created.append(destination)
    except (OSError, ValueError):
        for destination in reversed(created):
            shutil.rmtree(destination)
        for backup,destination in reversed(backups):
            backup.rename(destination)
        raise
    finally:
        for stage,_ in staged:
            if stage.exists():
                shutil.rmtree(stage)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', choices=('claude', 'cursor', 'both'), default='both')
    parser.add_argument('--scope', choices=('project', 'user'), default='project')
    parser.add_argument('--project', type=Path, help='Project root; defaults to current working directory')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--update', action='store_true', help='Replace existing skill copies while preserving a dated backup outside the skills directory')
    args = parser.parse_args()
    if args.scope == 'user' and args.project is not None:
        parser.error('--project cannot be used with --scope user')
    root = Path.home() if args.scope == 'user' else (args.project or Path.cwd()).expanduser().resolve()
    targets = ('claude', 'cursor') if args.target == 'both' else (args.target,)
    destinations = [root / f'.{target}' / 'skills' / 'diagram-ledger' for target in targets]
    source = Path(__file__).resolve().parent / 'skills' / 'diagram-ledger'
    try:
        install(source, destinations, args.dry_run, args.update)
    except (OSError, ValueError) as exc:
        print(f'Installation stopped: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
