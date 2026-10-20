#!/usr/bin/env python3
"""Compare diagram revisions against a hash-bound change contract. Python 3.9+."""
import argparse
import copy
import hashlib
import html
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

VERSION = 1
GEOMETRY = {'x','y','x1','y1','x2','y2','cx','cy','r','rx','ry','width','height','d','points','transform','dx','dy','viewBox','textLength','lengthAdjust'}
STYLE = {'style','class','fill','fill-opacity','stroke','stroke-width','stroke-opacity','stroke-dasharray','opacity','font-family','font-size','font-weight','font-style','text-anchor','dominant-baseline','marker-start','marker-mid','marker-end','visibility','display','filter','clip-path','mask'}
RELATION = {'data-from','data-to','data-within','data-outside'}
FIELDS = {'label','geometry','style','membership','source','target','content','order'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def tag(el):
    return el.tag.rsplit('}',1)[-1]


def canonical(el):
    return [tag(el), dict(sorted(el.attrib.items())), (el.text or '').strip(),
            [[canonical(c), (c.tail or '').strip()] for c in el]]


def load_xml(data):
    if re.search(br'<!\s*(DOCTYPE|ENTITY)',data,re.I):
        raise ValueError('DTD and entities are not supported')
    root=ET.fromstring(data)
    ids=[el.get('id') for el in root.iter() if el.get('id')]
    if len(ids)!=len(set(ids)):
        # draw.io IDs are page-local, checked separately below.
        if tag(root)!='mxfile':
            raise ValueError('Duplicate XML IDs')
    return root


def svg_snapshot(root):
    records={}
    selected={}
    for el in root.iter():
        kinds=[k for k in ('node','edge','container') if el.get('data-'+k) is not None]
        if len(kinds)>1:
            raise ValueError('One SVG element cannot have multiple entity roles')
        if kinds:
            kind=kinds[0]; identity=el.get('data-'+kind)
            if not identity or any(c.isspace() for c in identity):
                raise ValueError('SVG annotation IDs must be nonempty and contain no whitespace')
            if identity in selected:
                raise ValueError('Duplicate annotation ID: '+identity)
            selected[identity]=(kind,el)
    if not any(k=='node' for k,_ in selected.values()):
        raise ValueError('SVG comparison needs data-node annotations; use a source diff and manual review for unannotated SVG')
    parent={c:p for p in root.iter() for c in p}
    chosen={el for _,el in selected.values()}
    def ancestors(el):
        result=[]
        while el in parent:
            el=parent[el]
            if el in chosen:
                raise ValueError('Nested annotated entities are unsupported; use data-within on sibling groups')
            context=0
            if el in parent:
                for sibling in parent[el]:
                    if sibling is el: break
                    if sibling not in chosen: context+=1
            result.append([tag(el),el.get('id'),context])
        return list(reversed(result))
    for identity,(kind,el) in selected.items():
        stripped=copy.deepcopy(el)
        geom=[];style=[];labels=[]
        for index,part in enumerate(stripped.iter()):
            geom.append([index,tag(part),{k:part.attrib.pop(k) for k in sorted(GEOMETRY & part.attrib.keys())}])
            style.append([index,tag(part),{k:part.attrib.pop(k) for k in sorted(STYLE & part.attrib.keys())}])
            if part.text and part.text.strip(): labels.append([index,'text',part.text.strip()])
            if part.tail and part.tail.strip(): labels.append([index,'tail',part.tail.strip()])
            part.text=None;part.tail=None
            for key in RELATION: part.attrib.pop(key,None)
        records[kind+':'+identity]={
            'label':' '.join(item[2] for item in labels),'geometry':geom,'style':style,
            'membership':{'within':sorted(el.get('data-within','').split()),'outside':sorted(el.get('data-outside','').split()),'ancestors':ancestors(el),'untracked_siblings_before':sum(1 for sibling in list(parent.get(el,[]))[:list(parent.get(el,[])).index(el)] if sibling not in chosen) if el in parent else 0},
            'source':el.get('data-from'),'target':el.get('data-to'),'content':canonical(stripped)}
        if kind=='edge':
            for field in ('data-from','data-to'):
                endpoint=el.get(field)
                if endpoint not in selected or selected[endpoint][0]!='node':
                    raise ValueError(f'Edge {identity} has missing/non-node {field}: {endpoint}')
        for field in ('data-within','data-outside'):
            for boundary in el.get(field,'').split():
                if boundary not in selected or selected[boundary][0]!='container':
                    raise ValueError(f'Unknown container {boundary} on {identity}')
    remainder=copy.deepcopy(root)
    for p in list(remainder.iter()):
        for child in list(p):
            if any(child.get('data-'+k) is not None for k in ('node','edge','container')):
                p.remove(child)
    records['document:root']={'content':canonical(remainder),'order':[kind+':'+identity for identity,(kind,_) in selected.items()]}
    return records, 'Annotated SVG entities; exact source geometry/style and declared relationships. Remaining XML is protected as document content. Does not prove visual layout or infer relationships from arrow pixels.'


def drawio_snapshot(root):
    if tag(root)=='mxGraphModel':
        pages=[('page',root)]
    else:
        pages=[]
        page_ids=set()
        for page in root.findall('diagram'):
            identity=page.get('id')
            if not identity or identity in page_ids: raise ValueError('draw.io pages need unique stable IDs')
            page_ids.add(identity)
            model=page.find('mxGraphModel')
            if model is None: raise ValueError('Compressed draw.io is unsupported; save uncompressed XML first')
            pages.append((identity,model))
    if not pages: raise ValueError('No draw.io pages')
    records={}
    for page_id,model in pages:
        graph=model.find('root')
        if graph is None: raise ValueError('Missing graph root')
        if any(tag(c)!='mxCell' for c in graph): raise ValueError('draw.io wrapper objects are unsupported')
        cells=list(graph);ids=[c.get('id') for c in cells]
        if None in ids or '' in ids or len(ids)!=len(set(ids)): raise ValueError('Missing or duplicate cell ID')
        by_id=dict(zip(ids,cells))
        for cell in cells:
            identity=cell.get('id'); kind='edge' if cell.get('edge')=='1' else 'node' if cell.get('vertex')=='1' else 'layer'
            for field in ('parent','source','target'):
                if cell.get(field) is not None and cell.get(field) not in by_id:
                    raise ValueError(f'{identity}: dangling {field}')
            if kind=='edge' and (cell.get('source') is None or cell.get('target') is None):
                raise ValueError('Edges require explicit source and target IDs')
            visited=set();cursor=identity
            while cursor is not None:
                if cursor in visited: raise ValueError('Parent cycle: '+identity)
                visited.add(cursor);cursor=by_id[cursor].get('parent')
            stripped=copy.deepcopy(cell)
            for key in ('value','style','parent','source','target'): stripped.attrib.pop(key,None)
            geometry=[]
            for child in list(stripped):
                if tag(child)=='mxGeometry': geometry.append(canonical(child));stripped.remove(child)
            # Preserve style ordering: duplicate keys and style names may carry meaning.
            records[f'{kind}:{page_id}/{identity}']={
                'label':cell.get('value',''),'geometry':geometry,'style':cell.get('style',''),
                'membership':cell.get('parent'),'source':cell.get('source'),'target':cell.get('target'),
                'content':canonical(stripped)}
    remainder=copy.deepcopy(root)
    for graph in remainder.iter('root'):
        for child in list(graph): graph.remove(child)
    records['document:root']={'content':canonical(remainder),'order':list(records)}
    return records,'Uncompressed draw.io cells on every page; page-qualified IDs, labels, parents, endpoints, geometry and style. Page/model metadata is protected. No visual or architecture-truth guarantee.'


def snapshot(path):
    data=Path(path).read_bytes();root=load_xml(data)
    if tag(root)=='svg': records,coverage=svg_snapshot(root);fmt='svg'
    elif tag(root) in ('mxfile','mxGraphModel'): records,coverage=drawio_snapshot(root);fmt='drawio'
    else: raise ValueError('Supported inputs: standalone annotated SVG and uncompressed draw.io. HTML/Mermaid require source diff and native visual review.')
    return {'sha256':sha(data),'format':fmt,'entities':records,'coverage':coverage}


def compare(before, after, contract):
    if before['format']!=after['format']: raise ValueError('Compare the same format; conversions require a separate semantic review')
    if not isinstance(contract,dict) or set(contract)-{'version','baseline_sha256','allow','require','intent'}:
        raise ValueError('Unknown contract fields')
    if contract.get('version')!=VERSION or contract.get('baseline_sha256')!=before['sha256']:
        raise ValueError('Contract version or baseline hash does not match')
    if not isinstance(contract.get('allow'),dict) or not isinstance(contract.get('require'),list):
        raise ValueError('Contract needs allow object and require array')
    old=copy.deepcopy(before['entities']);new=copy.deepcopy(after['entities']);changes=[]
    # New/deleted entities do not count as reordering surviving entities.
    for side in (old,new):
        if 'order' in side['document:root']:
            side['document:root']['order']=[k for k in side['document:root']['order'] if k in old and k in new]
    all_ids=old.keys() | new.keys()
    for identity,fields in contract['allow'].items():
        if identity not in all_ids or not isinstance(fields,list) or not fields or any(not isinstance(f,str) for f in fields):
            raise ValueError('Invalid allowance: '+identity)
        if set(fields)-FIELDS-{'added','removed'}: raise ValueError('Unknown allowed field: '+identity)
        if 'added' in fields and identity in old: raise ValueError('added allowance targets existing entity: '+identity)
        if 'removed' in fields and identity not in old: raise ValueError('removed allowance targets missing entity: '+identity)
    for identity in sorted(all_ids):
        if identity not in old: fields=[('added',None,new[identity])]
        elif identity not in new: fields=[('removed',old[identity],None)]
        else: fields=[(f,old[identity].get(f),new[identity].get(f)) for f in sorted(old[identity].keys() | new[identity].keys()) if old[identity].get(f)!=new[identity].get(f)]
        for field,a,b in fields:
            changes.append({'entity':identity,'field':field,'before':a,'after':b,'allowed':field in contract['allow'].get(identity,[])})
    requirements=[]
    for rule in contract['require']:
        if not isinstance(rule,dict) or set(rule)-{'entity','field','equals','exists'} or 'entity' not in rule:
            raise ValueError('Invalid requirement')
        identity=rule['entity']
        if not isinstance(identity,str): raise ValueError('Requirement entity must be a string')
        if set(rule)=={'entity','exists'} and type(rule['exists']) is bool:
            passed=(identity in new)==rule['exists'];actual=identity in new
        elif set(rule)=={'entity','field','equals'} and rule['field'] in FIELDS:
            actual=new.get(identity,{}).get(rule['field']);passed=identity in new and actual==rule['equals']
        else: raise ValueError('Requirement must specify exists boolean OR field and equals')
        requirements.append({'rule':rule,'actual':actual,'passed':passed})
    used={(c['entity'],c['field']) for c in changes}
    unused=[{'entity':identity,'field':field} for identity,fields in contract['allow'].items() for field in fields if (identity,field) not in used]
    return {'version':VERSION,'status':'pass' if all(c['allowed'] for c in changes) and all(r['passed'] for r in requirements) and not unused else 'fail',
            'intent':contract.get('intent',''),'before_sha256':before['sha256'],'after_sha256':after['sha256'],
            'contract_sha256':sha(json.dumps(contract,sort_keys=True,separators=(',',':')).encode()),
            'format':before['format'],'coverage':before['coverage'],'changes':changes,'requirements':requirements,'unused_allowances':unused,
            'unchanged_entities':sorted(k for k in old.keys() & new.keys() if old[k]==new[k]),
            'counts':{'before':len(old)-1,'after':len(new)-1,'changes':len(changes),'unexpected':sum(not c['allowed'] for c in changes),'unused_allowances':len(unused)}}


def write_report(out, report, before, after, contract):
    out=Path(out)
    if out.exists(): raise ValueError('Report directory already exists; use a new path to preserve evidence')
    before_data=Path(before).read_bytes();after_data=Path(after).read_bytes()
    if sha(before_data)!=report['before_sha256'] or sha(after_data)!=report['after_sha256']:
        raise ValueError('Input changed during comparison')
    out.mkdir(parents=True)
    extension='.svg' if report['format']=='svg' else '.drawio'
    (out/('before'+extension)).write_bytes(before_data)
    (out/('after'+extension)).write_bytes(after_data)
    (out/'contract.json').write_text(json.dumps(contract,indent=2)+'\n', encoding='utf-8')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n', encoding='utf-8')
    esc=lambda value:html.escape(str(value))
    rows=''.join('<tr><td>'+esc(c['entity'])+'</td><td>'+esc(c['field'])+'</td><td>'+('Allowed' if c['allowed'] else 'UNEXPECTED')+'</td><td><details><summary>Inspect values</summary><pre>'+esc(json.dumps({'before':c['before'],'after':c['after']},indent=2))+'</pre></details></td></tr>' for c in report['changes'])
    requirements=''.join('<li>'+('PASS ' if r['passed'] else 'FAIL ')+esc(json.dumps(r['rule']))+'</li>' for r in report['requirements']) or '<li>No required outcomes specified; this report checks preservation only.</li>'
    markup='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Diagram Ledger · Revision report</title><style>body{font:16px/1.6 system-ui,sans-serif;color:#172a32;background:#f4f5f0;margin:0;padding:40px}main{max-width:1100px;margin:auto}h1{font-size:40px;line-height:1.15}small{color:#41545b}table{width:100%;border-collapse:collapse;background:white}td,th{text-align:left;padding:12px;border-bottom:1px solid #d7ded9;vertical-align:top}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}code{overflow-wrap:anywhere}a{color:#146052}.status{font-size:22px;font-weight:700}section{margin-top:32px}</style><main><small>DIAGRAM LEDGER / REVISION RECEIPT</small>'''
    markup+=f'<h1>{esc(report["intent"] or "Diagram revision")}</h1><p class="status">{report["status"].upper()} · {report["counts"]["changes"]} changes · {report["counts"]["unexpected"]} unexpected</p><p>{esc(report["coverage"])}</p><p><a href="before{extension}">Original source</a> · <a href="after{extension}">Revised source</a> · <a href="report.json">Machine-readable report</a> · <a href="contract.json">Contract</a></p>'
    markup+='<section><h2>Changes</h2><table><thead><tr><th>Entity</th><th>Field</th><th>Decision</th><th>Evidence</th></tr></thead><tbody>'+rows+'</tbody></table></section><section><h2>Required outcomes</h2><ul>'+requirements+'</ul></section>'
    markup+='<section><h2>Unused permissions</h2><p>'+esc(json.dumps(report['unused_allowances']) if report['unused_allowances'] else 'None. Every allowed field corresponds to an actual change.')+'</p><p>Remove unused allowances to narrow the contract; do not make unnecessary diagram changes to consume them.</p></section>'
    markup+='<section><h2>Preserved entities</h2><p>'+esc(', '.join(report['unchanged_entities']))+'</p></section>'
    markup+='<section><h2>Source fingerprints</h2><p>Before: <code>'+report['before_sha256']+'</code><br>After: <code>'+report['after_sha256']+'</code><br>Contract (canonical JSON): <code>'+report['contract_sha256']+'</code></p><p>A pass means this contract was satisfied. It does not establish that the contract matches the user request. Review the contract and render both sources before accepting the change.</p></section></main></html>'
    (out/'index.html').write_text(markup, encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    plan=sub.add_parser('plan',help='Capture a baseline and create a preservation-only contract; edit it before revising')
    plan.add_argument('source',type=Path);plan.add_argument('--out',required=True,type=Path)
    check=sub.add_parser('check',help='Compare two sources; nonzero exit on unexpected changes or unmet requirements')
    check.add_argument('before',type=Path);check.add_argument('after',type=Path);check.add_argument('--contract',required=True,type=Path);check.add_argument('--out',required=True,type=Path)
    check.add_argument('--require-outcomes',action='store_true',help='Reject preservation-only contracts with no required outcomes')
    args=parser.parse_args()
    try:
        if args.command=='plan':
            state=snapshot(args.source)
            if args.out.exists(): raise ValueError('Plan directory already exists')
            args.out.mkdir(parents=True)
            suffix='.svg' if state['format']=='svg' else '.drawio'
            (args.out/('baseline'+suffix)).write_bytes(args.source.read_bytes())
            (args.out/'snapshot.json').write_text(json.dumps(state,indent=2)+'\n', encoding='utf-8')
            (args.out/'contract.json').write_text(json.dumps({'version':VERSION,'baseline_sha256':state['sha256'],'intent':'','allow':{},'require':[]},indent=2)+'\n', encoding='utf-8')
            print('BASELINE_CAPTURED: edit contract.json to authorize only requested changes before editing the diagram')
        else:
            contract=json.loads(args.contract.read_text(encoding='utf-8'))
            if args.require_outcomes and isinstance(contract,dict) and not contract.get('require'):
                raise ValueError('--require-outcomes needs a nonempty require list describing the requested result')
            report=compare(snapshot(args.before),snapshot(args.after),contract)
            write_report(args.out,report,args.before,args.after,contract)
            print('REVISION_'+report['status'].upper()+': '+str(args.out/'index.html'))
            return 0 if report['status']=='pass' else 1
    except (OSError,ValueError,ET.ParseError,TypeError) as exc:
        print('Revision check stopped: '+str(exc),file=sys.stderr);return 2
    return 0


if __name__=='__main__':
    sys.exit(main())
