#!/usr/bin/env python3
"""Generate the original revision showcase in a new directory (no dependencies)."""
import argparse
import importlib.util
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('revision_examples',ROOT/'skills/diagram-ledger/scripts/revision.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)


def svg(after=False):
    nodes=[('publisher',65,195,'Publisher','Emits an event'),('inbox',345,195,'Event inbox','Durable queue'),('delivery',625,195,'Delivery worker' if after else 'Dispatcher','Sends the webhook'),('endpoint',905,195,'Subscriber','External endpoint')]
    if after:nodes.append(('quarantine',625,425,'Quarantine','Retains rejected events'))
    bits=['''<svg xmlns="http://www.w3.org/2000/svg" width="1180" height="650" viewBox="0 0 1180 650" role="img" aria-labelledby="title description"><title id="title">Webhook delivery</title><desc id="description">Publisher sends events to an inbox. A worker delivers them to an external subscriber. The revision adds a quarantine for rejected events.</desc><defs><marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="#48636b"/></marker></defs><rect width="1180" height="650" fill="#f7f8f3"/><g font-family="Arial, sans-serif" fill="#172e36"><text x="48" y="45" font-size="13" letter-spacing="2" fill="#42665f">DIAGRAM LEDGER / REVISION STUDY 01</text><text x="48" y="91" font-size="34" font-weight="700">Webhook delivery</text><text x="48" y="122" font-size="16" fill="#48636b">A precise change to an existing system map</text><g data-container="platform"><rect data-body="" x="310" y="155" width="560" height="405" rx="20" fill="#edf2eb" stroke="#b9c9c1"/><text x="334" y="181" font-size="13" font-weight="700" fill="#42665f">DELIVERY PLATFORM</text></g>''']
    for id,x,y,title,sub in nodes:
        member=' data-within="platform"' if id in ('inbox','delivery','quarantine') else ' data-outside="platform"'
        fill='#e1eee6' if id=='quarantine' else '#fff'
        bits.append(f'<g id="{id}" data-node="{id}"{member}><rect data-body="" x="{x}" y="{y}" width="210" height="90" rx="12" fill="{fill}" stroke="#789089"/><text x="{x+20}" y="{y+36}" font-size="18" font-weight="700">{title}</text><text x="{x+20}" y="{y+63}" font-size="14" fill="#48636b">{sub}</text></g>')
    for id,source,target,path,tx,ty,label in [('publish','publisher','inbox','M275 240H345',310,224,'event'),('consume','inbox','delivery','M555 240H625',590,224,'pull'),('send','delivery','endpoint','M835 240H905',870,224,'POST')]+([('reject','delivery','quarantine','M730 285V425',770,354,'rejected')] if after else []):
        bits.append(f'<g data-edge="{id}" data-from="{source}" data-to="{target}"><path data-route="" d="{path}" fill="none" stroke="#48636b" stroke-width="2" marker-end="url(#arrow)"/><text x="{tx}" y="{ty}" text-anchor="middle" font-size="13" fill="#48636b">{label}</text></g>')
    bits.append('<path d="M48 590H1132" stroke="#c7d2cb"/><text x="48" y="622" font-size="14" fill="#48636b">Solid arrow · event movement</text><text x="1132" y="622" text-anchor="end" font-size="14" fill="#48636b">Illustrative architecture · no delivery guarantee implied</text></g></svg>')
    return ''.join(bits)


def drawio(after=False):
    root=ET.Element('mxfile',host='app.diagrams.net');page=ET.SubElement(root,'diagram',id='main',name='Webhook delivery');model=ET.SubElement(page,'mxGraphModel',page='1',pageWidth='1180',pageHeight='650',background='#f7f8f3');graph=ET.SubElement(model,'root')
    ET.SubElement(graph,'mxCell',id='0');ET.SubElement(graph,'mxCell',id='1',parent='0')
    def box(id,label,x,y,w,h,parent='1',style=''):
        cell=ET.SubElement(graph,'mxCell',id=id,value=label,vertex='1',parent=parent,style=style or 'rounded=1;whiteSpace=wrap;html=0;fillColor=#ffffff;strokeColor=#789089;fontColor=#172e36;fontSize=16;fontFamily=Arial;spacing=14;')
        ET.SubElement(cell,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),**{'as':'geometry'})
    box('title','Webhook delivery',48,36,1084,55,style='text;html=0;align=left;verticalAlign=middle;fontSize=34;fontStyle=1;fontColor=#172e36;fontFamily=Arial;')
    box('subtitle','A precise change to an existing system map',48,96,1084,30,style='text;html=0;align=left;fontSize=16;fontColor=#48636b;fontFamily=Arial;')
    box('platform','DELIVERY PLATFORM',310,155,560,405,style='rounded=1;whiteSpace=wrap;html=0;fillColor=#edf2eb;strokeColor=#b9c9c1;verticalAlign=top;align=left;spacingTop=14;spacingLeft=24;fontSize=13;fontStyle=1;fontColor=#42665f;')
    for id,x,y,label,parent in [('publisher',65,195,'Publisher\nEmits an event','1'),('inbox',35,40,'Event inbox\nDurable queue','platform'),('delivery',315,40,('Delivery worker' if after else 'Dispatcher')+'\nSends the webhook','platform'),('endpoint',905,195,'Subscriber\nExternal endpoint','1')]+([('quarantine',315,270,'Quarantine\nRetains rejected events','platform')] if after else []):box(id,label,x,y,210,90,parent)
    for id,source,target,label in [('publish','publisher','inbox','event'),('consume','inbox','delivery','pull'),('send','delivery','endpoint','POST')]+([('reject','delivery','quarantine','rejected')] if after else []):
        vertical=id=='reject';style='edgeStyle=orthogonalEdgeStyle;rounded=0;html=0;endArrow=block;endFill=1;strokeColor=#48636b;fontColor=#48636b;fontSize=13;labelBackgroundColor=#f7f8f3;'+('exitX=0.5;exitY=1;entryX=0.5;entryY=0;' if vertical else 'exitX=1;exitY=0.5;entryX=0;entryY=0.5;')
        cell=ET.SubElement(graph,'mxCell',id=id,value=label,edge='1',parent='1',source=source,target=target,style=style);ET.SubElement(cell,'mxGeometry',relative='1',**{'as':'geometry'})
    box('footer','Solid arrow: event movement. Illustrative architecture; no delivery guarantee implied.',48,590,1084,40,style='text;html=0;align=left;fontSize=14;fontColor=#48636b;fontFamily=Arial;')
    ET.indent(root);return ET.tostring(root,encoding='unicode')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    if args.out.exists():parser.error('Use a new output directory')
    args.out.mkdir(parents=True)
    for fmt,generate in [('svg',svg),('drawio',drawio)]:
        folder=args.out/fmt;folder.mkdir();before=folder/('before.'+fmt);after=folder/('after.'+fmt)
        before.write_text(generate(), encoding='utf-8');after.write_text(generate(True), encoding='utf-8');a=r.snapshot(before);b=r.snapshot(after)
        prefix='main/' if fmt=='drawio' else '';node='node:'+prefix+'delivery';new='node:'+prefix+'quarantine';edge='edge:'+prefix+'reject'
        contract={'version':1,'baseline_sha256':a['sha256'],'intent':'Rename Dispatcher and retain rejected events in a quarantine','allow':{node:['label'],new:['added'],edge:['added']},'require':[{'entity':node,'field':'label','equals':b['entities'][node]['label']},{'entity':new,'field':'membership','equals':b['entities'][new]['membership']},{'entity':edge,'field':'source','equals':'delivery'},{'entity':edge,'field':'target','equals':'quarantine'},{'entity':edge,'field':'label','equals':'rejected'}]}
        (folder/'contract.json').write_text(json.dumps(contract,indent=2)+'\n', encoding='utf-8');report=r.compare(a,b,contract)
        if report['status']!='pass':raise RuntimeError(report)
        r.write_report(folder/'receipt',report,before,after,contract)
    print('REVISION_EXAMPLES_GENERATED')

if __name__=='__main__':main()
