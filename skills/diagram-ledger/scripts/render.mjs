#!/usr/bin/env node
/** Local, network-blocked browser preview and measured SVG text audit.
 * Optional dependency: Playwright and an installed Chromium browser.
 * No dependency downloads. Not a sanitizer or an exact draw.io renderer.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';

const args = process.argv.slice(2);
const input = args.shift();
const options = {};
for (let i = 0; i < args.length; i += 2) {
  if (!['--out', '--modules', '--browser', '--width', '--strict'].includes(args[i]) || !args[i + 1]) {
    throw new Error('Usage: node render.mjs input.svg|html --out directory [--modules node_modules] [--browser chrome|chromium] [--width 1200]');
  }
  options[args[i].slice(2)] = args[i + 1];
}
if (!input || !options.out || !/\.(svg|html?)$/i.test(input)) {
  throw new Error('Provide an SVG/HTML input and --out directory. draw.io needs its native renderer.');
}
const absolute = path.resolve(input);
await fs.access(absolute);
const out = path.resolve(options.out);
await fs.mkdir(out, { recursive: true });
const require = createRequire(options.modules ? path.join(path.resolve(options.modules), '_diagram_craft.cjs') : import.meta.url);
let chromium;
try { ({ chromium } = require('playwright')); }
catch { throw new Error('Playwright is not installed. Use an existing project installation or pass --modules /path/to/node_modules. No packages were downloaded.'); }
const width = Number(options.width || 1200);
if (!Number.isFinite(width) || width < 320 || width > 5000) throw new Error('Width must be between 320 and 5000.');
const browser = await chromium.launch({ headless: true, ...(options.browser === 'chrome' ? { channel: 'chrome' } : {}) });
try {
  const context = await browser.newContext({ viewport: { width, height: 900 }, deviceScaleFactor: 1, javaScriptEnabled: false });
  const blocked = [];
  await context.route(/^https?:/, route => { blocked.push(route.request().url()); return route.abort(); });
  const page = await context.newPage();
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  if (/\.svg$/i.test(absolute)) {
    // Chromium's screenshot path can stall on a top-level SVG document.
    // An HTML host preserves the SVG markup and native sizing without that bug.
    const source=(await fs.readFile(absolute,'utf8')).replace(/^\s*<\?xml[^>]*\?>/i,'');
    await page.setContent('<!DOCTYPE html><html><head><meta charset="utf-8"></head><body style="margin:0">'+source+'</body></html>',{waitUntil:'load'});
  } else {
    await page.goto(pathToFileURL(absolute).href, { waitUntil: 'load', timeout: 30000 });
  }
  await page.evaluate(() => document.fonts.ready);
  const audit = await page.evaluate(() => {
    const rect = e => { const r = e.getBoundingClientRect(); return { x: r.x, y: r.y, width: r.width, height: r.height, right: r.right, bottom: r.bottom }; };
    const intersects = (a, b, margin = 1) => Math.min(a.right, b.right) - Math.max(a.x, b.x) > margin && Math.min(a.bottom, b.bottom) - Math.max(a.y, b.y) > margin;
    const visible = e => { const s = getComputedStyle(e); return s.display !== 'none' && s.visibility !== 'hidden' && Number(s.opacity) !== 0; };
    const color = value => { const m = value.match(/[\d.]+/g); return m && m.length >= 3 ? m.slice(0, 3).map(Number) : null; };
    const luminance = rgb => rgb.map(n => n / 255).map(n => n <= .04045 ? n / 12.92 : ((n + .055) / 1.055) ** 2.4).reduce((s,n,i) => s+n*[.2126,.7152,.0722][i],0);
    const contrast = (a,b) => { const x=luminance(a),y=luminance(b); return (Math.max(x,y)+.05)/(Math.min(x,y)+.05); };
    return [...document.querySelectorAll('svg')].map((svg, index) => {
      const canvas = rect(svg);
      const texts = [...svg.querySelectorAll('text')].filter(e => !e.closest('defs, marker, symbol') && visible(e)).map(e => {
        const style = getComputedStyle(e), box = rect(e);
        const matrix = e.getScreenCTM();
        const scale = matrix ? Math.sqrt(matrix.a ** 2 + matrix.b ** 2) : 1;
        return { id: e.id || null, text: e.textContent.trim(), box, fontSize: Number.parseFloat(style.fontSize) * scale, fill: style.fill, element: e };
      }).filter(t => t.text && t.box.width && t.box.height);
      const overlaps = [];
      for (let a=0; a<texts.length; a++) for(let b=a+1;b<texts.length;b++) {
        if(intersects(texts[a].box,texts[b].box)) overlaps.push([texts[a].text,texts[b].text]);
      }
      const outside = texts.filter(t=>t.box.x<canvas.x-1 || t.box.y<canvas.y-1 || t.box.right>canvas.right+1 || t.box.bottom>canvas.bottom+1).map(t=>t.text);
      const small = texts.filter(t=>t.fontSize<12).map(t=>({text:t.text,displayPx:Math.round(t.fontSize*100)/100}));
      const annotated = [];
      const nodes = new Map([...svg.querySelectorAll('[data-node]')].map(e=>[e.getAttribute('data-node'),e]));
      const containers = new Map([...svg.querySelectorAll('[data-container]')].map(e=>[e.getAttribute('data-container'),e]));
      const containerIssues = [];
      for(const [name,node] of nodes) {
        const b=rect(node.querySelector('[data-body]')||node);
        for(const relation of ['within','outside']) for(const id of (node.getAttribute('data-'+relation)||'').split(/\s+/).filter(Boolean)) {
          const container=containers.get(id);
          if(!container) { containerIssues.push({node:name,container:id,problem:'referenced container missing'});continue; }
          const c=rect(container.querySelector('[data-body]')||container);
          if(relation==='within' && !(b.x>=c.x+12 && b.y>=c.y+12 && b.right<=c.right-12 && b.bottom<=c.bottom-12)) containerIssues.push({node:name,container:id,problem:'node not fully inside container with 12 px clearance'});
          if(relation==='outside' && intersects(b,c,0)) containerIssues.push({node:name,container:id,problem:'external node intersects container'});
        }
      }
      for (const group of svg.querySelectorAll('[data-node]')) {
        const body = group.querySelector('[data-body]');
        if (!body) continue;
        const b=rect(body), surface=color(getComputedStyle(body).fill);
        for(const label of texts.filter(t=>group.contains(t.element))) {
          if(label.box.x<b.x+3 || label.box.right>b.right-3 || label.box.y<b.y+3 || label.box.bottom>b.bottom-3) annotated.push({node:group.getAttribute('data-node'),problem:'label exceeds node padding',text:label.text});
          const ink=color(label.fill);
          if(ink && surface && contrast(ink,surface)<4.5) annotated.push({node:group.getAttribute('data-node'),problem:'text contrast below 4.5:1',text:label.text,ratio:contrast(ink,surface)});
        }
      }
      const edges = [];
      const distanceToBox = (p,b) => Math.hypot(Math.max(b.x-p.x,0,p.x-b.right), Math.max(b.y-p.y,0,p.y-b.bottom));
      const inside = (p,b,pad=2) => p.x>b.x+pad && p.x<b.right-pad && p.y>b.y+pad && p.y<b.bottom-pad;
      for(const edge of svg.querySelectorAll('[data-edge][data-from][data-to]')) {
        const curve = edge.matches('path,polyline,line') ? edge : edge.querySelector('[data-route]');
        const source = nodes.get(edge.getAttribute('data-from')), target = nodes.get(edge.getAttribute('data-to'));
        const id=edge.getAttribute('data-edge');
        if(!curve || !source || !target) { edges.push({edge:id,problem:'missing route or referenced node'});continue; }
        const body = e=>e.querySelector('[data-body]') || e;
        const from=rect(body(source)),to=rect(body(target));
        const length=curve.getTotalLength(), matrix=curve.getScreenCTM();
        if(length<16) edges.push({edge:id,problem:'route too short for a clear arrowhead; separate nodes'});
        const point = t=>{const p=curve.getPointAtLength(t);const q=new DOMPoint(p.x,p.y).matrixTransform(matrix);return {x:q.x,y:q.y};};
        const start=point(0),end=point(length),before=point(Math.max(0,length-6));
        if(distanceToBox(start,from)>10) edges.push({edge:id,problem:'route starts more than 10 px from source'});
        if(distanceToBox(end,to)>10) edges.push({edge:id,problem:'route ends more than 10 px from target'});
        const direction={x:end.x-before.x,y:end.y-before.y};
        const toward={x:(to.x+to.right)/2-end.x,y:(to.y+to.bottom)/2-end.y};
        if(direction.x*toward.x+direction.y*toward.y < -1) edges.push({edge:id,problem:'final segment points away from target'});
        for(const [name,node] of nodes) {
          if(node===source || node===target) continue;
          const b=rect(body(node));
          let hit=false;
          for(let t=0;t<=length;t+=Math.max(1,length/500)) if(inside(point(t),b)) {hit=true;break;}
          if(hit) edges.push({edge:id,problem:'route crosses unrelated node',node:name});
        }
      }
      const nodeOverlaps=[];
      const foreignLabels=[];
      const nodeEntries=[...nodes];
      for(const [name,node] of nodeEntries) {
        const b=rect(node.querySelector('[data-body]')||node);
        for(const label of texts) if(!node.contains(label.element)&&intersects(b,label.box,2)) foreignLabels.push({node:name,text:label.text});
      }
      for(let a=0;a<nodeEntries.length;a++) for(let b=a+1;b<nodeEntries.length;b++) {
        const [an,ae]=nodeEntries[a],[bn,be]=nodeEntries[b];
        if(!ae.contains(be)&&!be.contains(ae)&&intersects(rect(ae.querySelector('[data-body]')||ae),rect(be.querySelector('[data-body]')||be))) nodeOverlaps.push([an,bn]);
      }
      const routeTextCollisions=[];
      const paths=[...svg.querySelectorAll('path,line,polyline')].filter(e=>!e.closest('defs,marker,symbol') && visible(e) && (getComputedStyle(e).markerEnd!=='none' || getComputedStyle(e).markerStart!=='none' || e.hasAttribute('data-route') || e.hasAttribute('data-edge')));
      const masks=[...svg.querySelectorAll('rect')].filter(e=>{const s=getComputedStyle(e);return visible(e)&&s.fill!=='none'&&Number(s.fillOpacity||1)>.95&&Number(s.opacity||1)>.95;});
      for(const curve of paths) {
        const length=curve.getTotalLength(),matrix=curve.getScreenCTM();
        const box=rect(curve);
        for(const label of texts) {
          if(label.box.right<box.x-2 || label.box.x>box.right+2 || label.box.bottom<box.y-2 || label.box.y>box.bottom+2) continue;
          const covered=masks.some(mask=>{
            if(!(curve.compareDocumentPosition(mask)&Node.DOCUMENT_POSITION_FOLLOWING)) return false;
            const b=rect(mask),t=label.box;
            return b.x<=t.x && b.y<=t.y && b.right>=t.right && b.bottom>=t.bottom;
          });
          if(covered) continue;
          let hit=false;
          for(let t=0;t<=length;t+=Math.max(1,length/1000)) {
            const p=curve.getPointAtLength(t),q=new DOMPoint(p.x,p.y).matrixTransform(matrix);
            if(inside(q,label.box,1)) {hit=true;break;}
          }
          if(hit) routeTextCollisions.push({route:curve.closest('[data-edge]')?.getAttribute('data-edge')||curve.id||curve.getAttribute('d')||'line',text:label.text});
        }
      }
      return { index, canvas, accessibleName: svg.getAttribute('aria-labelledby'), textCount:texts.length,
        textOverlaps:overlaps, textOutsideCanvas:outside, smallText:small, annotatedNodeIssues:annotated, annotatedEdgeIssues:edges, nodeOverlaps, routeTextCollisions, foreignLabels, containerIssues,
        texts:texts.map(({element,...t})=>t) };
    });
  });
  await page.screenshot({ path: path.join(out,'preview.png'), fullPage: true, animations: 'disabled' });
  const exports = await page.evaluate(() => [...document.querySelectorAll('svg')].map(svg => {
    const clone=svg.cloneNode(true);
    const original=[svg,...svg.querySelectorAll('*')], copies=[clone,...clone.querySelectorAll('*')];
    const properties=['fill','fill-opacity','stroke','stroke-width','stroke-opacity','stroke-dasharray','stroke-linecap','stroke-linejoin','font-family','font-size','font-weight','font-style','text-anchor','dominant-baseline','opacity','visibility','marker-start','marker-mid','marker-end'];
    original.forEach((e,i)=>{ const s=getComputedStyle(e); properties.forEach(p=>{ const value=s.getPropertyValue(p).replace(/url\(["']?[^#)]*#([^"')]+)["']?\)/g,'url(#$1)'); if(value) copies[i].style.setProperty(p,value); }); });
    clone.setAttribute('xmlns','http://www.w3.org/2000/svg');
    const box=svg.viewBox.baseVal;
    if(box.width && box.height) { clone.setAttribute('width',String(box.width)); clone.setAttribute('height',String(box.height)); clone.style.removeProperty('width');clone.style.removeProperty('height'); }
    return new XMLSerializer().serializeToString(clone);
  }));
  for(let i=0;i<exports.length;i++) await fs.writeFile(path.join(out,`diagram-${i+1}.svg`),exports[i]);
  const report={input:absolute,viewportWidth:width,networkRequestsBlocked:blocked,pageErrors,svgs:audit,
    limits:'Measured text bounds plus annotated-node padding/contrast and sampled annotated connector routes. Sampling can miss very small intersections. Review screenshots for edge/label crossings, semantics, nonrectangular fit, and unannotated geometry. External resources blocked; page scripts disabled.'};
  await fs.writeFile(path.join(out,'audit.json'),JSON.stringify(report,null,2));
  console.log(JSON.stringify({output:out,svgCount:audit.length,textOverlapPairs:audit.reduce((n,a)=>n+a.textOverlaps.length,0),outsideLabels:audit.reduce((n,a)=>n+a.textOutsideCanvas.length,0),smallLabels:audit.reduce((n,a)=>n+a.smallText.length,0),blockedRequests:blocked.length}));
  const findings=audit.reduce((n,a)=>n+a.textOverlaps.length+a.textOutsideCanvas.length+a.smallText.length+a.annotatedNodeIssues.length+a.annotatedEdgeIssues.length+a.nodeOverlaps.length+a.routeTextCollisions.length+a.foreignLabels.length+a.containerIssues.length,0);
  if(!audit.length || pageErrors.length || (options.strict==='yes' && (findings || blocked.length))) process.exitCode=1;
} finally { await browser.close(); }
