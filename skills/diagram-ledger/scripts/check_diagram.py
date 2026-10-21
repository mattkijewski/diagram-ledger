#!/usr/bin/env python3
"""Structural checks for SVG, draw.io, basic Excalidraw and beta VSON flowcharts.

Not a renderer, importer, security sanitizer, or semantic correctness proof.
Python 3.9+, standard library only. No writes or network requests.
"""
import argparse
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from html import unescape
from html.parser import HTMLParser
from pathlib import Path


class InlineSVG(HTMLParser):
    """Locate exact SVG substrings without treating HTML as XML."""
    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.offsets = [0]
        for line in source.splitlines(keepends=True):
            self.offsets.append(self.offsets[-1] + len(line))
        self.depth = 0
        self.start = None
        self.svgs = []
        self.unsafe = []

    def source_offset(self):
        row, col = self.getpos()
        return self.offsets[row - 1] + col

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'iframe', 'object', 'embed', 'base'):
            self.unsafe.append(f'Unsupported HTML element: {tag}')
        for key, value in attrs:
            if key.lower().startswith('on') or key.lower() == 'srcdoc':
                self.unsafe.append(f'Unsupported active HTML attribute: {key}')
            if key.lower() in ('src', 'href') and value and not value.startswith('#'):
                self.unsafe.append(f'External HTML resource/link is outside the static subset: {key}')
        if tag == 'svg':
            if self.depth == 0:
                self.start = self.source_offset()
            self.depth += 1

    def handle_endtag(self, tag):
        if tag == 'svg' and self.depth:
            self.depth -= 1
            if self.depth == 0:
                end = self.source.find('>', self.source_offset()) + 1
                self.svgs.append(self.source[self.start:end])

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)


def local(tag):
    return tag.rsplit('}', 1)[-1]


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError, OverflowError):
        return None


class LabelText(HTMLParser):
    """Read one HTML-label layer without recursively decoding visible text."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def label_encoding_errors(text, location, allow_literal_entities=False, html_label=False):
    if allow_literal_entities or not isinstance(text, str):
        return []
    if html_label:
        parser = LabelText()
        parser.feed(text)
        parser.close()
        text = ''.join(parser.parts)
    entities = re.findall(r'&(?:#[0-9]+|#[xX][0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]+);', text)
    entities = sorted({entity for entity in entities if unescape(entity) != entity})
    if not entities:
        return []
    return [f'{location}: literal entity text {", ".join(entities)} may be over-escaped. '
            'Use actual Unicode in labels and serialize once. If these codes are intentional, '
            'review the label and use --allow-literal-entities.']


def check_svg(root, allow_literal_entities=False):
    errors = []
    if root.tag != '{http://www.w3.org/2000/svg}svg':
        errors.append('SVG root must declare the SVG namespace.')
    values = re.split(r'[\s,]+', root.get('viewBox', '').strip())
    box = [number(v) for v in values]
    if len(box) != 4 or any(v is None for v in box) or box[2] <= 0 or box[3] <= 0:
        errors.append('viewBox must contain four finite numbers with positive width/height.')
    for key in ('width', 'height'):
        value = root.get(key, '')
        match = re.fullmatch(r'([\d.+eE-]+)(?:px|pt|mm|cm|in)?', value)
        size = number(match.group(1)) if match else None
        if size is None or size <= 0:
            errors.append(f'Set an explicit positive {key} (not a percentage).')
    ids = {}
    refs = []
    forbidden = {'script', 'foreignObject', 'iframe', 'object', 'embed', 'animate', 'animateMotion', 'animateTransform', 'set'}
    for element in root.iter():
        tag = local(element.tag)
        ident = element.get('id')
        if tag in ('text', 'title', 'desc'):
            errors.extend(label_encoding_errors(''.join(element.itertext()),
                          f'SVG {tag} {ident or "(unnamed)"}', allow_literal_entities))
        if ident:
            if ident in ids:
                errors.append(f'Duplicate SVG id: {ident}')
            ids[ident] = element
        if tag in forbidden:
            errors.append(f'Unsupported active/nonportable SVG element: {tag}')
        for key, value in element.attrib.items():
            attr = local(key).lower()
            if attr.startswith('on'):
                errors.append(f'Event attribute is not supported: {attr}')
            if attr == 'href':
                if value.startswith('#'):
                    refs.append(value[1:])
                else:
                    errors.append('Only local fragment hrefs are supported.')
        texts = list(element.attrib.values())
        if tag == 'style':
            texts.append(''.join(element.itertext()))
        for text in texts:
            if re.search(r'@import\b', text, re.I):
                errors.append('CSS imports are not supported.')
            for target in re.findall(r'url\(\s*([^)]*?)\s*\)', text, re.I):
                target = target.strip().strip('\"\'')
                if target.startswith('#'):
                    refs.append(target[1:])
                else:
                    errors.append(f'Non-local resource URL: {target}')
    refs += root.get('aria-labelledby', '').split()
    for ref in refs:
        if ref not in ids:
            errors.append(f'Missing referenced SVG id: {ref}')
    labels = [ids[ref] for ref in root.get('aria-labelledby', '').split() if ref in ids]
    if root.get('role') != 'img':
        errors.append('SVG root needs role="img".')
    for tag in ('title', 'desc'):
        if not any(local(e.tag) == tag and ''.join(e.itertext()).strip() for e in labels):
            errors.append(f'aria-labelledby must reference a nonempty {tag}.')
    return errors


def check_drawio(root, allow_literal_entities=False):
    errors = []
    if root.tag != 'mxfile':
        return ['Expected an mxfile root.']
    pages = root.findall('diagram')
    if not pages:
        errors.append('Document has no diagram pages.')
    for page_index, page in enumerate(pages, 1):
        prefix = f'Page {page_index}: '
        graph = page.find('mxGraphModel/root')
        if graph is None:
            errors.append(prefix + 'expected uncompressed mxGraphModel/root; compressed input is unsupported.')
            continue
        if any(child.tag != 'mxCell' for child in graph):
            errors.append(prefix + 'object wrappers are unsupported; use direct mxCell elements.')
        cells = {}
        for cell in graph.findall('mxCell'):
            ident = cell.get('id')
            if not ident:
                errors.append(prefix + 'cell is missing an id.')
                continue
            if ident in cells:
                errors.append(prefix + f'duplicate cell id: {ident}')
            cells[ident] = cell
        if '0' not in cells or cells['0'].get('parent') is not None:
            errors.append(prefix + 'root cell 0 must exist without a parent.')
        if '1' not in cells or cells['1'].get('parent') != '0':
            errors.append(prefix + 'default layer 1 must have parent 0.')
        for ident, cell in cells.items():
            style = dict(part.split('=', 1) for part in cell.get('style', '').split(';') if '=' in part)
            errors.extend(label_encoding_errors(cell.get('value', ''), prefix + ident,
                          allow_literal_entities, html_label=style.get('html') == '1'))
            parent = cell.get('parent')
            if ident != '0' and parent not in cells:
                errors.append(prefix + f'{ident}: missing parent {parent!r}.')
            seen = {ident}
            while parent in cells:
                if parent in seen:
                    errors.append(prefix + f'{ident}: parent cycle.')
                    break
                seen.add(parent)
                parent = cells[parent].get('parent')
            vertex = cell.get('vertex') == '1'
            edge = cell.get('edge') == '1'
            if vertex and edge:
                errors.append(prefix + f'{ident}: cannot be both a vertex and an edge.')
            geometry = cell.find('mxGeometry')
            if vertex or edge:
                if geometry is None or geometry.get('as') != 'geometry':
                    errors.append(prefix + f'{ident}: missing mxGeometry as="geometry".')
            if vertex and geometry is not None:
                for dim in ('width', 'height'):
                    value = number(geometry.get(dim))
                    if value is None or value <= 0:
                        errors.append(prefix + f'{ident}: {dim} must be finite and positive.')
                for axis in ('x', 'y'):
                    if number(geometry.get(axis, '0')) is None:
                        errors.append(prefix + f'{ident}: {axis} must be finite.')
            if edge:
                for end in ('source', 'target'):
                    target = cell.get(end)
                    if target not in cells or cells[target].get('vertex') != '1':
                        errors.append(prefix + f'{ident}: {end} must reference an existing vertex.')
                if geometry is not None and geometry.get('relative') != '1':
                    errors.append(prefix + f'{ident}: edge geometry must be relative="1".')
    return errors


def check_excalidraw(scene, allow_literal_entities=False):
    """Our shape/text/simple-connector subset, not the entire native schema."""
    if not isinstance(scene, dict) or scene.get('type') != 'excalidraw' or scene.get('version') != 2:
        return ['Expected an Excalidraw scene with type="excalidraw" and version=2.']
    if not isinstance(scene.get('appState'), dict) or not isinstance(scene.get('files'), dict):
        return ['Excalidraw appState and files must be objects.']
    elements = scene.get('elements')
    if not isinstance(elements, list) or not elements:
        return ['Excalidraw elements must be a nonempty array.']
    errors, by_id = [], {}
    shapes = ('rectangle', 'ellipse', 'diamond')
    supported = shapes + ('text', 'arrow', 'line')

    def finite(value):
        return type(value) in (int, float) and number(value) is not None

    for element in elements:
        if not isinstance(element, dict):
            errors.append('Every Excalidraw element must be an object.')
            continue
        ident = element.get('id')
        if not isinstance(ident, str) or not ident:
            errors.append('Every Excalidraw element needs a nonempty string id.')
            continue
        if ident in by_id:
            errors.append(f'Duplicate Excalidraw id: {ident}')
        by_id[ident] = element
    active = {key: value for key, value in by_id.items() if value.get('isDeleted') is not True}

    def target(ident):
        return active.get(ident) if isinstance(ident, str) else None

    def bound_refs(element):
        refs = element.get('boundElements')
        return refs if isinstance(refs, list) else []

    def reciprocal(owner, child):
        return any(isinstance(ref, dict) and ref.get('id') == child['id']
                   and ref.get('type') == child.get('type') for ref in bound_refs(owner))

    for ident, element in active.items():
        kind = element.get('type')
        prefix = f'{ident}: '
        if kind not in supported:
            errors.append(prefix + f'unsupported Excalidraw type {kind!r}; use native verification.')
            continue
        for field in ('x', 'y', 'width', 'height', 'angle'):
            value = element.get(field)
            if not finite(value):
                errors.append(prefix + f'{field} must be a finite JSON number.')
            elif field in ('width', 'height') and (value < 0 or (kind not in ('arrow', 'line') and value == 0)):
                errors.append(prefix + f'{field} has invalid dimensions.')
        refs = element.get('boundElements')
        if refs is not None and not isinstance(refs, list):
            errors.append(prefix + 'boundElements must be an array or null.')
        seen_refs = set()
        for ref in bound_refs(element):
            child = target(ref.get('id')) if isinstance(ref, dict) else None
            if child is None or ref.get('type') not in ('text', 'arrow') or child.get('type') != ref.get('type'):
                errors.append(prefix + 'boundElements must reference existing text or arrows.')
                continue
            if child['id'] in seen_refs:
                errors.append(prefix + 'duplicate boundElements reference.')
            seen_refs.add(child['id'])
            if child['type'] == 'text':
                linked = child.get('containerId') == ident
            else:
                linked = any(isinstance(child.get(end), dict) and child[end].get('elementId') == ident
                             for end in ('startBinding', 'endBinding'))
            if not linked:
                errors.append(prefix + 'boundElements reference is not reciprocal.')
        groups = element.get('groupIds')
        if not isinstance(groups, list) or any(not isinstance(group, str) or not group for group in groups):
            errors.append(prefix + 'groupIds must be an array of nonempty strings.')
        if element.get('frameId') is not None:
            errors.append(prefix + 'frames are outside this checker subset; use native verification.')
        if kind == 'text':
            errors.extend(label_encoding_errors(element.get('text'), prefix + 'text', allow_literal_entities))
            for field in ('text', 'originalText'):
                if not isinstance(element.get(field), str):
                    errors.append(prefix + f'{field} must be a string.')
            for field in ('fontSize', 'lineHeight'):
                if not finite(element.get(field)) or element[field] <= 0:
                    errors.append(prefix + f'{field} must be finite and positive.')
            container = element.get('containerId')
            if container is not None:
                owner = target(container)
                if owner is None or owner.get('type') not in shapes + ('arrow',):
                    errors.append(prefix + 'containerId must reference an existing shape or arrow.')
                elif not reciprocal(owner, element):
                    errors.append(prefix + 'text container binding is not reciprocal.')
        if kind in ('arrow', 'line'):
            points = element.get('points')
            valid = (isinstance(points, list) and len(points) >= 2 and
                     all(isinstance(point, list) and len(point) == 2 and all(finite(v) for v in point)
                         for point in points))
            if not valid:
                errors.append(prefix + 'points must contain at least two finite coordinate pairs.')
            elif points[0] != [0, 0] or all(point == points[0] for point in points):
                errors.append(prefix + 'points must start at [0, 0] and describe a nonzero route.')
            else:
                for axis, dimension in enumerate(('width', 'height')):
                    extent = max(p[axis] for p in points) - min(p[axis] for p in points)
                    value = element.get(dimension)
                    if finite(value) and not math.isclose(value, extent, abs_tol=0.01):
                        errors.append(prefix + f'{dimension} does not match the points extent.')
            if element.get('elbowed'):
                errors.append(prefix + 'elbowed arrows require native verification outside this subset.')
            for end in ('startBinding', 'endBinding'):
                binding = element.get(end)
                if binding is None:
                    continue  # Free arrows/lines are valid, but do not assert relationships.
                owner = target(binding.get('elementId')) if isinstance(binding, dict) else None
                if owner is None or owner.get('type') not in shapes:
                    errors.append(prefix + f'{end} must reference an existing shape.')
                    continue
                if not reciprocal(owner, element):
                    errors.append(prefix + f'{end} is not reciprocal.')
                if 'mode' in binding:
                    point = binding.get('fixedPoint')
                    if binding['mode'] not in ('inside', 'orbit', 'skip'):
                        errors.append(prefix + f'{end}.mode is not a supported native binding mode.')
                    if not (isinstance(point, list) and len(point) == 2 and
                            all(finite(v) and 0 <= v <= 1 for v in point)):
                        errors.append(prefix + f'{end}.fixedPoint must contain two ratios between 0 and 1.')
                else:
                    # Older scenes use focus/gap; the native importer upgrades them.
                    if not finite(binding.get('focus')) or not -1 <= binding['focus'] <= 1:
                        errors.append(prefix + f'{end}.focus must be between -1 and 1.')
                    if not finite(binding.get('gap')) or binding['gap'] < 0:
                        errors.append(prefix + f'{end}.gap must be nonnegative.')
    if not active:
        errors.append('Excalidraw scene has no active elements.')
    return errors


def check_vson(document, allow_literal_entities=False):
    """Beta structural checks for our basic SmartDraw flowchart subset."""
    if not isinstance(document, dict) or document.get('Version') != '1.0':
        return ['Expected a VSON object with Version="1.0".']
    if document.get('Template') != 'Flowchart':
        return ['Only the basic VSON Flowchart template is checked; use native verification for other templates.']
    errors, ids = [], set()
    directions = ('Top', 'Bottom', 'Left', 'Right')
    shape_keys = {'ID', 'Label', 'ShapeType', 'ShapeConnector', 'ShapeList',
                  'FillColor', 'TextColor', 'TextSize', 'TextFont', 'TextBold', 'TextItalic',
                  'TextMargin', 'MinWidth', 'MinHeight', 'LineLabel', 'LineColor', 'LineThick'}
    connector_keys = {'ShapeConnectorType', 'Direction', 'Shapes', 'StartArrow', 'EndArrow'}
    return_keys = {'StartID', 'EndID', 'StartDirection', 'EndDirection', 'Label',
                   'StartArrow', 'EndArrow', 'LineColor', 'LineThick'}

    def fields(obj, allowed, location):
        for key in obj:
            if key not in allowed:
                errors.append(f'{location}: unsupported field {key!r} in the basic VSON subset.')
        for key in ('MinWidth', 'MinHeight', 'TextSize', 'LineThick'):
            if key in obj and (type(obj[key]) not in (int, float) or number(obj[key]) is None or obj[key] <= 0):
                errors.append(f'{location}: {key} must be a positive finite number.')
        for key in ('Label', 'LineLabel'):
            errors.extend(label_encoding_errors(obj.get(key), f'{location} {key}', allow_literal_entities))
            if key in obj and not isinstance(obj[key], str):
                errors.append(f'{location}: {key} must be text.')
        for key in ('StartArrow', 'EndArrow'):
            if key in obj and (type(obj[key]) is not int or not 0 <= obj[key] <= 38):
                errors.append(f'{location}: {key} must be an integer arrow style from 0 to 38.')

    def shape(obj, depth=0):
        if depth > 60 or len(ids) >= 2000:
            errors.append('VSON exceeds the checker depth/shape limit.')
            return
        if not isinstance(obj, dict):
            errors.append('VSON Shape must be an object.')
            return
        ident = obj.get('ID')
        if type(ident) is not int or ident <= 0:
            errors.append('VSON shape ID must be a positive integer.')
        elif ident in ids:
            errors.append(f'Duplicate VSON shape ID: {ident}')
        else:
            ids.add(ident)
        fields(obj, shape_keys, f'Shape {ident}')
        if not isinstance(obj.get('Label'), str) or not obj['Label'].strip():
            errors.append(f'Shape {ident}: a nonempty Label is required in this subset.')
        if obj.get('ShapeType', 'Rect') not in ('Rect', 'RRect', 'Oval', 'Circle', 'Square', 'Diamond'):
            errors.append(f'Shape {ident}: custom shape types require native verification.')
        if 'ShapeConnector' in obj and 'ShapeList' in obj:
            errors.append(f'Shape {ident}: use one connector spelling, not both.')
        connectors = obj.get('ShapeConnector', obj.get('ShapeList', []))
        if not isinstance(connectors, list):
            errors.append(f'Shape {ident}: connectors must be an array.')
            return
        for connector in connectors:
            if not isinstance(connector, dict):
                errors.append(f'Shape {ident}: each connector must be an object.')
                continue
            fields(connector, connector_keys, f'Shape {ident} connector')
            if connector.get('ShapeConnectorType') != 'Flowchart':
                errors.append(f'Shape {ident}: connector must use Flowchart.')
            if connector.get('Direction') not in directions:
                errors.append(f'Shape {ident}: invalid connector Direction.')
            children = connector.get('Shapes')
            if not isinstance(children, list) or not children:
                errors.append(f'Shape {ident}: connector Shapes must be a nonempty array.')
                continue
            for child in children:
                shape(child, depth + 1)

    fields(document, {'Version', 'Template', 'Shape', 'Returns'}, 'Document')
    shape(document.get('Shape'))
    returns = document.get('Returns', [])
    if not isinstance(returns, list):
        errors.append('VSON Returns must be an array.')
        return errors
    for edge in returns:
        if not isinstance(edge, dict):
            errors.append('Every VSON Return must be an object.')
            continue
        fields(edge, return_keys, 'Return')
        for key in ('StartID', 'EndID'):
            if type(edge.get(key)) is not int or edge[key] not in ids:
                errors.append(f'Return {key} must reference an existing shape ID.')
        for key in ('StartDirection', 'EndDirection'):
            if key in edge and edge[key] not in directions:
                errors.append(f'Return {key} is invalid.')
    return errors


def check(path, allow_literal_entities=False):
    path = Path(path)
    if path.suffix.lower() not in ('.svg', '.drawio', '.html', '.htm', '.excalidraw', '.vson'):
        return ['Supported file extensions: .svg, .html, .drawio, .excalidraw, .vson; Mermaid requires a Mermaid renderer.']
    try:
        if path.stat().st_size > 10 * 1024 * 1024:
            return ['File exceeds the 10 MiB checker limit.']
        content = path.read_text(encoding='utf-8-sig')
        if path.suffix.lower() == '.excalidraw':
            return check_excalidraw(json.loads(content), allow_literal_entities)
        if path.suffix.lower() == '.vson':
            return check_vson(json.loads(content), allow_literal_entities)
        is_html = path.suffix.lower() in ('.html', '.htm')
        declarations = re.sub(r'<!DOCTYPE\s+html\s*>', '', content, flags=re.I) if is_html else content
        if re.search(r'<!\s*(DOCTYPE|ENTITY)', declarations, re.I):
            return ['DTD/entity declarations are outside the supported static subset.']
        if is_html:
            parser = InlineSVG(content)
            parser.feed(content)
            errors = parser.unsafe[:]
            if not parser.svgs or parser.depth:
                errors.append('Expected at least one complete inline SVG.')
            for index, source in enumerate(parser.svgs, 1):
                try:
                    svg = ET.fromstring(source)
                    if svg.tag == 'svg':
                        svg.tag = '{http://www.w3.org/2000/svg}svg'
                    errors.extend(f'SVG {index}: {error}' for error in check_svg(svg, allow_literal_entities))
                except ET.ParseError as exc:
                    errors.append(f'SVG {index}: invalid XML: {exc}')
            if re.search(r'@import\b|url\(\s*[\"\']?(?:https?:|//)', content, re.I):
                errors.append('External CSS resources are outside the static subset.')
            return errors
        root = ET.fromstring(content)
    except (OSError, UnicodeError, ET.ParseError, ValueError, RecursionError) as exc:
        return [f'Cannot read diagram: {exc}']
    return check_svg(root, allow_literal_entities) if path.suffix.lower() == '.svg' else check_drawio(root, allow_literal_entities)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='+', type=Path)
    parser.add_argument('--allow-literal-entities', action='store_true',
                        help='Allow intentionally displayed entity codes after reviewing the labels')
    args = parser.parse_args()
    failed = False
    for path in args.files:
        errors = check(path, allow_literal_entities=args.allow_literal_entities)
        if errors:
            failed = True
            print(f'FAIL {path}')
            for error in errors:
                print(f'  - {error}')
        else:
            print(f'PASS {path}: structural checks only; rendering and semantic review still required.')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
