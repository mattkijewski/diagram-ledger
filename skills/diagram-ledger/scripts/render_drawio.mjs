#!/usr/bin/env node
/** Render uncompressed draw.io locally, then audit native text bounds and routes. */
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {createHash, randomBytes} from 'node:crypto';
import {createRequire} from 'node:module';
import {auditLayout} from './layout_geometry.mjs';
const hash=data=>createHash('sha256').update(data).digest('hex');
const config=JSON.parse(await fs.readFile(new URL('./drawio-runtime.json',import.meta.url),'utf8'));
const args=process.argv.slice(2), input=args.shift(), options={};
for(let i=0;i<args.length;i+=2){if(!['--out','--modules','--browser','--viewer'].includes(args[i]) || !args[i+1])throw new Error('Usage: node render_drawio.mjs input.drawio --out NEW-directory [--browser chrome] [--modules node_modules] [--viewer pinned-viewer.js]'); options[args[i].slice(2)]=args[i+1];}
if(!input || !options.out || !/\.drawio$/i.test(input))throw new Error('Provide a .drawio input and a new --out directory.');
if(options.browser && !['chrome','chromium'].includes(options.browser))throw new Error('--browser must be chrome or chromium.');
const absolute=path.resolve(input),out=path.resolve(options.out),source=await fs.readFile(absolute);
if(source.length>10*1024*1024)throw new Error('Source exceeds the 10 MiB limit.');
const viewer=options.viewer || process.env.DIAGRAM_LEDGER_DRAWIO_VIEWER || path.join(os.homedir(),'.cache','diagram-ledger',config.filename);
let runtime;
try{runtime=await fs.readFile(viewer);}catch{throw new Error('Pinned draw.io runtime unavailable. Run setup_drawio.py --install once. No downloads were attempted.');}
if(hash(runtime)!==config.sha256)throw new Error('draw.io viewer checksum mismatch. Run setup_drawio.py --install to restore the pinned runtime.');
const require=createRequire(options.modules ? path.join(path.resolve(options.modules),'_diagram_ledger.cjs'):import.meta.url);
let chromium;try{({chromium}=require('playwright'));}catch{throw new Error('Playwright unavailable. Pass --modules to an existing installation; see drawio-layout.md for setup.');}
// A fresh output folder prevents an older passing audit from being mistaken for this run.
await fs.mkdir(path.dirname(out),{recursive:true});await fs.mkdir(out);
const report={input:absolute,sourceSha256:hash(source),renderer:{name:'draw.io viewer',version:config.version,sha256:config.sha256},status:'error',pages:[],blockedRequests:[],errors:[],limits:'Native text bounding boxes and straight/polyline centerlines; rounded bends are approximated by their segments. Container bodies are excluded but their headings are checked. Opaque backgrounds exempt only an edge’s own label. Curves, hidden/collapsed content and unsupported shapes need native review. Crossings between lines, exact nonrectangular boundaries, arrowhead extents, semantics and display-size readability still require image inspection.'};
let browser;
try{
 browser=await chromium.launch({headless:true,...(options.browser==='chrome'?{channel:'chrome'}:{})});
 const context=await browser.newContext({viewport:{width:1600,height:1000},deviceScaleFactor:1});
 await context.route('**/*',route=>{report.blockedRequests.push(route.request().url());return route.abort();});
 await context.routeWebSocket('**/*',socket=>{report.blockedRequests.push(socket.url());socket.close();});
 const page=await context.newPage();page.setDefaultTimeout(30000);page.on('pageerror',e=>report.errors.push(e.message));
 const nonce=randomBytes(24).toString('hex');
 await page.setContent(`<html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'nonce-${nonce}'; style-src 'unsafe-inline'; img-src data:; font-src 'none'; connect-src 'none'; base-uri 'none'"></head><body style="margin:0;background:white"><div id="graph" style="position:relative"></div></body></html>`);
 // The viewer auto-loads optional MathJax unless present; math inputs are rejected below.
 await page.evaluate(()=>{window.MathJax={};window.cspBlocks=[];document.addEventListener('securitypolicyviolation',e=>window.cspBlocks.push(e.blockedURI));});
 await page.evaluate(({code,nonce})=>{const script=document.createElement('script');script.nonce=nonce;script.textContent=code;document.head.appendChild(script);},{code:runtime.toString('utf8'),nonce});
 const metadata=await page.evaluate(xml=>{
  const doc=new DOMParser().parseFromString(xml,'application/xml');
  if(doc.querySelector('parsererror') || doc.doctype || doc.documentElement.tagName!=='mxfile')throw new Error('Expected valid uncompressed mxfile XML without a DTD.');
  const pages=[...doc.documentElement.children];
  if(!pages.length || pages.length>30 || pages.some(p=>p.tagName!=='diagram' || p.children.length!==1 || p.firstElementChild.tagName!=='mxGraphModel'))throw new Error('Expected 1–30 uncompressed diagram pages. Export compressed files as uncompressed XML first.');
  if(doc.querySelectorAll('mxCell').length>3000)throw new Error('Diagram exceeds the 3000-cell render limit.');
  for(const p of pages){if(p.firstElementChild.getAttribute('math')==='1')throw new Error('Math typesetting is unsupported by the offline layout renderer.');const r=p.querySelector('mxGraphModel > root');if(!r || [...r.children].some(c=>c.tagName!=='mxCell'))throw new Error('Object wrappers are unsupported; use direct mxCell elements.');const ids=[...r.children].map(c=>c.getAttribute('id'));if(ids.some(i=>!i)||new Set(ids).size!==ids.length)throw new Error('Missing or duplicate cell IDs.');}
  window.sourceDocument=doc;return pages.map((p,i)=>({index:i,id:p.getAttribute('id'),name:p.getAttribute('name')}));
 },source.toString('utf8'));
 for(const meta of metadata){
  const measurement=await page.evaluate(async index=>{
   if(typeof window.graph?.destroy === 'function')graph.destroy();const container=document.getElementById('graph');container.innerHTML='';container.style.width='';container.style.height='';
   window.graph=new Graph(container);graph.setEnabled(false);
   const doc=window.sourceDocument,model=doc.documentElement.children[index].firstElementChild;
   const pageDocument=mxUtils.parseXml(new XMLSerializer().serializeToString(model));
   new mxCodec(pageDocument).decode(pageDocument.documentElement,graph.getModel());await document.fonts.ready;graph.refresh();graph.view.validate();
   const rect=b=>b?{x:b.x,y:b.y,width:b.width,height:b.height}:null;
   const all=Object.values(graph.model.cells),visible=[],unsupported=[];
   for(const c of all){if(!c.vertex && !c.edge)continue;const s=graph.view.getState(c);if(!s){unsupported.push({cell:c.id,problem:'Hidden or collapsed cell was not measured.'});continue;}
    const kind=s.style.shape;
    if(graph.convertValueToString(c) && !s.text?.boundingBox)unsupported.push({cell:c.id,problem:'Label has no measurable rendered text bounds.'});
    if(![s.x,s.y,s.width,s.height].every(Number.isFinite))unsupported.push({cell:c.id,problem:'Non-finite rendered geometry.'});
    if(c.vertex && !['rectangle','ellipse','rhombus','cylinder','cylinder3','swimlane','label','text','hexagon','parallelogram',undefined].includes(kind))unsupported.push({cell:c.id,problem:'Shape outside the verified basic subset: '+kind});
    if(c.collapsed)unsupported.push({cell:c.id,problem:'Collapsed content requires expanded native review.'});
    const mask=s.text?.node?.querySelector('rect[fill]:not([fill="none"])');
    const maskStyle=mask?getComputedStyle(mask):null;
    const fill=maskStyle?.fill || 'none';
    const alpha=fill.startsWith('rgba(')?Number(fill.slice(5,-1).split(',').at(-1)):1;
    const opaqueLabel=!!maskStyle && fill!=='none' && fill!=='transparent' && alpha===1 && Number(maskStyle.fillOpacity)===1 && Number(maskStyle.opacity)===1 && Number(s.style.opacity ?? 100)===100 && Number(s.style.textOpacity ?? 100)===100;
    visible.push({id:c.id,label:graph.convertValueToString(c),parent:c.parent?.id,source:c.source?.id,target:c.target?.id,vertex:!!c.vertex,edge:!!c.edge,box:rect(s),text:rect(s.text?.boundingBox),points:s.absolutePoints?.map(p=>p?{x:p.x,y:p.y}:null),opaqueLabel,curved:s.style.curved==='1'||s.style.curved===1,container:s.style.container==='1'||s.style.container===1||kind==='swimlane'||all.some(n=>n.vertex&&n.parent===c),topLabel:s.style.verticalAlign==='top'});
   }
   const bounds=rect(graph.getGraphBounds());if(!bounds || ![bounds.x,bounds.y,bounds.width,bounds.height].every(Number.isFinite) || bounds.width<=0 || bounds.height<=0 || bounds.width>30000 || bounds.height>30000)throw new Error('Empty or excessive rendered bounds.');
   const svg=new XMLSerializer().serializeToString(graph.getSvg('#FFFFFF',1,16));
   return {states:visible,unsupported,bounds,svg};
  },meta.index);
  const findings=auditLayout(measurement.states);findings.unsupported.push(...measurement.unsupported);
  const stem=`page-${meta.index+1}`;
  await fs.writeFile(path.join(out,stem+'.svg'),measurement.svg);
  const previewScale=await page.evaluate(()=>{const b=graph.getGraphBounds(),scale=Math.min(1,1500/(b.width+32),7000/(b.height+32));graph.view.scaleAndTranslate(scale,-b.x+16,-b.y+16);const r=graph.getGraphBounds();document.getElementById('graph').style.width=Math.ceil(r.x+r.width+16)+'px';document.getElementById('graph').style.height=Math.ceil(r.y+r.height+16)+'px';return scale;});
  await page.screenshot({path:path.join(out,stem+'.png'),fullPage:true,animations:'disabled'});
  report.pages.push({...meta,...findings,bounds:measurement.bounds,previewScale,svg:stem+'.svg',preview:stem+'.png'});
 }
 report.blockedRequests.push(...await page.evaluate(()=>window.cspBlocks));
 const findings=report.pages.reduce((n,p)=>n+p.routeTextCollisions.length+p.routeNodeCollisions.length+p.textOverlaps.length+p.unsupported.length,0);
 report.status=findings || report.errors.length || report.blockedRequests.length?'fail':'pass';
}catch(error){report.errors.push(error.message);}finally{if(browser)await browser.close();await fs.writeFile(path.join(out,'audit.json'),JSON.stringify(report,null,2)+'\n');}
console.log(JSON.stringify({status:report.status,output:out,pages:report.pages.length,sourceSha256:report.sourceSha256}));
if(report.status!=='pass')process.exitCode=1;
