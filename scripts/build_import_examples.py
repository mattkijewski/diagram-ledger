#!/usr/bin/env python3
"""Generate original, matched four-node fixtures for beta destination testing."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def smartdraw_scene():
    def node(ident, label, fill, **extra):
        return dict(ID=ident, Label=label, ShapeType='RRect',
                    FillColor=fill, TextColor='#172033', TextSize=16,
                    MinWidth=180, MinHeight=80, **extra)

    def connector(direction, child):
        return dict(ShapeConnectorType='Flowchart', Direction=direction,
                    EndArrow=1, Shapes=[child])

    published = node(3, 'Published', '#D3F9D8', LineLabel='Approved')
    revise = node(4, 'Revise', '#E7F5FF', LineLabel='Needs edits')
    review = node(2, 'Review', '#FFF3BF', LineLabel='Submit',
                  ShapeConnector=[connector('Right', published), connector('Bottom', revise)])
    draft = node(1, 'Draft', '#F1F3F5', ShapeConnector=[connector('Right', review)])
    return dict(Version='1.0', Template='Flowchart', Shape=draft,
                Returns=[dict(StartID=4, EndID=1, StartDirection='Left',
                              EndDirection='Bottom', Label='Return to draft', EndArrow=1)])


def lucidchart_source():
    mxfile = ET.Element('mxfile', host='app.diagrams.net')
    page = ET.SubElement(mxfile, 'diagram', id='review-flow', name='Review flow')
    graph = ET.SubElement(page, 'mxGraphModel', page='1', pageWidth='1100', pageHeight='700')
    root = ET.SubElement(graph, 'root')
    ET.SubElement(root, 'mxCell', id='0')
    ET.SubElement(root, 'mxCell', id='1', parent='0')
    for ident, label, x, y, fill in (
        ('draft', 'Draft', 80, 120, '#F1F3F5'), ('review', 'Review', 430, 120, '#FFF3BF'),
        ('published', 'Published', 780, 120, '#D3F9D8'), ('revise', 'Revise', 430, 350, '#E7F5FF'),
    ):
        style = f'rounded=1;whiteSpace=wrap;html=0;fontFamily=Arial;fontSize=22;fillColor={fill};strokeColor=#243B3B;fontColor=#172033;'
        cell = ET.SubElement(root, 'mxCell', id=ident, value=label, vertex='1', parent='1', style=style)
        ET.SubElement(cell, 'mxGeometry', x=str(x), y=str(y), width='200', height='100', **{'as': 'geometry'})
    for ident, source, target, label, ports in (
        ('submit', 'draft', 'review', 'Submit', 'exitX=1;exitY=0.5;entryX=0;entryY=0.5;'),
        ('approve', 'review', 'published', 'Approved', 'exitX=1;exitY=0.5;entryX=0;entryY=0.5;'),
        ('edits', 'review', 'revise', 'Needs edits', 'exitX=0.5;exitY=1;entryX=0.5;entryY=0;'),
        ('return', 'revise', 'draft', 'Return to draft', 'exitX=0;exitY=0.5;entryX=0.5;entryY=1;'),
    ):
        style = 'edgeStyle=orthogonalEdgeStyle;html=0;endArrow=block;endFill=1;fontSize=16;labelBackgroundColor=#FFFFFF;' + ports
        cell = ET.SubElement(root, 'mxCell', id=ident, value=label, edge='1', parent='1',
                             source=source, target=target, style=style)
        geometry = ET.SubElement(cell, 'mxGeometry', relative='1', **{'as': 'geometry'})
        if ident == 'return':
            points = ET.SubElement(geometry, 'Array', **{'as': 'points'})
            ET.SubElement(points, 'mxPoint', x='180', y='400')
    ET.indent(mxfile, space='  ')
    return ET.tostring(mxfile, encoding='unicode') + '\n'


if __name__ == '__main__':
    destination = ROOT/'skills/diagram-ledger/assets/imports'
    destination.mkdir(exist_ok=True)
    for name, content in (
        ('review-flow-smartdraw.vson', json.dumps(smartdraw_scene(), indent=2) + '\n'),
        ('review-flow-lucidchart.drawio', lucidchart_source()),
    ):
        with (destination/name).open('w', encoding='utf-8', newline='\n') as output:
            output.write(content)
        print(destination/name)
