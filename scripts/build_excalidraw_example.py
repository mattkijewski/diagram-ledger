#!/usr/bin/env python3
"""Rebuild the original, deterministic Excalidraw teaching scene."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build_scene():
    elements = []

    def base(ident, kind, x, y, width, height, **extra):
        element = dict(
            id=ident, type=kind, x=x, y=y, width=width, height=height,
            angle=0, strokeColor='#243b3b', backgroundColor='transparent',
            fillStyle='solid', strokeWidth=2, strokeStyle='solid', roughness=1,
            opacity=100, groupIds=[], frameId=None, roundness=None,
            seed=1000 + len(elements), version=1, versionNonce=2000 + len(elements),
            isDeleted=False, boundElements=[], updated=1, link=None, locked=False,
        )
        element.update(extra)
        elements.append(element)
        return element

    def text(ident, label, x, y, width, size=22, container=None, align='left'):
        lines = label.count('\n') + 1
        element = base(
            ident, 'text', x, y, width, size * 1.25 * lines,
            text=label, originalText=label, fontSize=size, fontFamily=2,
            textAlign=align, verticalAlign='middle' if container else 'top',
            containerId=container['id'] if container else None,
            lineHeight=1.25, autoResize=True,
        )
        if container:
            container['boundElements'].append(dict(id=ident, type='text'))
        return element

    def node(ident, label, x, y, fill):
        shape = base(ident, 'rectangle', x, y, 200, 100,
                     backgroundColor=fill, roundness={'type': 3})
        text(ident + '-label', label, x + 15, y + 36.25, 170,
             container=shape, align='center')
        return shape

    def arrow(ident, start, end, x, y, points):
        element = base(
            ident, 'arrow', x, y,
            max(p[0] for p in points) - min(p[0] for p in points),
            max(p[1] for p in points) - min(p[1] for p in points),
            points=points, startArrowhead=None, endArrowhead='arrow',
            startBinding=dict(elementId=start['id'], focus=0, gap=10),
            endBinding=dict(elementId=end['id'], focus=0, gap=10),
            lastCommittedPoint=None, elbowed=False,
        )
        for owner in (start, end):
            owner['boundElements'].append(dict(id=ident, type='arrow'))
        return element

    text('title', 'From draft to publication', 80, 65, 820, size=36)
    text('subtitle', 'A review loop with an explicit approval step', 80, 120, 850, size=20)
    draft = node('draft', 'Draft', 80, 220, '#f1f3f5')
    review = node('review', 'Review', 430, 220, '#fff3bf')
    published = node('published', 'Published', 780, 220, '#d3f9d8')
    revise = node('revise', 'Revise', 430, 450, '#e7f5ff')
    arrow('submit', draft, review, 290, 270, [[0, 0], [130, 0]])
    arrow('approve', review, published, 640, 270, [[0, 0], [130, 0]])
    arrow('request-edits', review, revise, 530, 330, [[0, 0], [0, 110]])
    arrow('resubmit', revise, draft, 420, 500, [[0, 0], [-240, 0], [-240, -170]])
    text('submit-note', 'Submit', 308, 228, 100, size=18)
    text('approve-note', 'Approved', 658, 228, 110, size=18)
    text('edits-note', 'Needs edits', 550, 375, 150, size=18)
    text('resubmit-note', 'Return to draft', 200, 460, 180, size=18)
    text('footer', 'Illustrative workflow • Move a node to check that its arrows and label follow.',
         80, 610, 940, size=18)
    return dict(type='excalidraw', version=2, source='diagram-ledger',
                elements=elements, appState=dict(viewBackgroundColor='#ffffff', gridSize=None),
                files={})


if __name__ == '__main__':
    path = ROOT / 'skills/diagram-ledger/assets/review-flow.excalidraw'
    path.write_text(json.dumps(build_scene(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(path)
