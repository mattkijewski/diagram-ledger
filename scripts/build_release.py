#!/usr/bin/env python3
"""Build deterministic skill and portable archives without benchmark/reference code."""
import hashlib
import argparse
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SKILL=ROOT/'skills/diagram-ledger'
PACKAGE_DOCS=('EVALUATION.md','NAME.md','IMPORT-TESTING.md')


def files_under(root):
    return sorted(p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and p.name!='.DS_Store')


def archive(destination, files):
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as output:
        for file,name in sorted(files,key=lambda x:x[1]):
            info=zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644 << 16
            output.writestr(info,file.read_bytes())
    with zipfile.ZipFile(destination) as result:
        if result.testzip() is not None:
            raise RuntimeError('Archive CRC verification failed')
    return {'file':destination.name,'sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),'bytes':destination.stat().st_size,'entries':len(files)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'dist',help='Output directory (use dist/preview for local betas)')
    dist=parser.parse_args().out
    dist.mkdir(parents=True,exist_ok=True)
    skill_files=files_under(SKILL)
    if (ROOT/'LICENSE').is_file():
        if not (SKILL/'LICENSE').is_file() or (SKILL/'LICENSE').read_bytes()!=(ROOT/'LICENSE').read_bytes():
            raise RuntimeError('Root and skill licenses must match before building')
    manifest=[]
    manifest.append(archive(dist/'diagram-ledger-skill.zip',[(p,'diagram-ledger/'+p.relative_to(SKILL).as_posix()) for p in skill_files]))
    # Package curated documentation only, never diagrams generated while using the skill.
    docs=[ROOT/'docs'/name for name in PACKAGE_DOCS]
    portable=skill_files+([ROOT/'LICENSE'] if (ROOT/'LICENSE').is_file() else [])+[ROOT/'README.md',ROOT/'install.py',ROOT/'.gitignore',ROOT/'.gitattributes']+files_under(ROOT/'tests')+files_under(ROOT/'scripts')+files_under(ROOT/'examples')+docs
    manifest.append(archive(dist/'diagram-ledger-portable.zip',[(p,'diagram-ledger-package/'+p.relative_to(ROOT).as_posix()) for p in portable]))
    (dist/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n', encoding='utf-8')
    print(json.dumps(manifest,indent=2))
    print('RELEASE_ARCHIVES_VERIFIED')


if __name__=='__main__':
    main()
