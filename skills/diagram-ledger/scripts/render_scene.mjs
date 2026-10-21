#!/usr/bin/env node
/** Native Excalidraw/Mermaid export and rendered geometry audit. No downloads. */
import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {createHash,randomBytes} from 'node:crypto';
import {auditLayout} from './layout_geometry.mjs';
import {measureScene} from './measure_scene.mjs';
const args=process.argv.slice(2),input=args.shift(),options={};
for(let i=0;i<args.length;i+=2){if(!['--out','--modules','--browser'].includes(args[i])||!args[i+1])throw new Error('Usage: render_scene.mjs input.excalidraw|mmd --out NEW-directory [--modules node_modules] [--browser chrome]');options[args[i].slice(2)]=args[i+1];}
const format=/\.excalidraw$/i.test(input||'')?'excalidraw':/\.mmd$/i.test(input||'')?'mermaid':null;
if(!format||!options.out)throw new Error('Expected .excalidraw or .mmd and --out.');
const source=await fs.readFile(input),out=path.resolve(options.out);
if(source.length>10*1024*1024)throw new Error('Source exceeds 10 MiB.');
await fs.mkdir(path.dirname(out),{recursive:true});await fs.mkdir(out);
const report={input:path.resolve(input),format,sourceSha256:createHash('sha256').update(source).digest('hex'),status:'error',blockedRequests:[],errors:[],limits:'Native SVG text rectangles and sampled native route strokes (1.5 px spacing); may miss tiny intersections. Shape bounds are approximate. Readability, line-to-line crossings, arrowheads and semantics still need image review. Other application imports are not certified.'};
let browser;
try{
 const require=createRequire(options.modules?path.join(path.resolve(options.modules),'_ledger.cjs'):import.meta.url);
 const {chromium}=require('playwright');
 const entry=require.resolve(format==='excalidraw'?'@excalidraw/excalidraw':'mermaid');
 let packageRoot=path.dirname(entry);
 while(true){try{const json=JSON.parse(await fs.readFile(path.join(packageRoot,'package.json'),'utf8'));if(json.name===(format==='excalidraw'?'@excalidraw/excalidraw':'mermaid')){report.renderer={name:json.name,version:json.version};break;}}catch{}const parent=path.dirname(packageRoot);if(parent===packageRoot)throw new Error('Renderer package metadata missing.');packageRoot=parent;}
 const expected=format==='excalidraw'?'0.18.0':'12.2.0';if(report.renderer.version!==expected)throw new Error(`Verified ${format} renderer version is ${expected}; found ${report.renderer.version}.`);
 let code;
 if(format==='excalidraw'){
  const {build}=require('esbuild');
  const result=await build({stdin:{contents:'import {exportToSvg} from "@excalidraw/excalidraw";window.nativeScene={exportToSvg};',resolveDir:path.dirname(packageRoot)},nodePaths:options.modules?[path.resolve(options.modules)]:[],bundle:true,write:false,platform:'browser',format:'iife',define:{'process.env.NODE_ENV':'"production"'},loader:{'.woff2':'dataurl','.css':'empty'}});
  code=result.outputFiles[0].text;
 }else code=await fs.readFile(path.join(packageRoot,'dist/mermaid.js'),'utf8');
 browser=await chromium.launch({headless:true,...(options.browser==='chrome'?{channel:'chrome'}:{})});
 const context=await browser.newContext({viewport:{width:1600,height:1000}});
 const fonts=path.join(packageRoot,'dist/prod/fonts');
 await context.route('**/*',async route=>{
  const url=new URL(route.request().url());
  const localFont=url.origin==='https://diagram-ledger.invalid'&&url.pathname.startsWith('/fonts/')?url.pathname.slice(7):url.origin==='https://esm.sh'&&url.pathname.startsWith('/@excalidraw/excalidraw@0.18.0/dist/prod/fonts/')?url.pathname.split('/dist/prod/fonts/')[1]:null;
  if(format==='excalidraw'&&localFont){
   const file=path.resolve(fonts,decodeURIComponent(localFont));
   if(file.startsWith(fonts+path.sep)&&file.endsWith('.woff2')){try{return await route.fulfill({body:await fs.readFile(file),contentType:'font/woff2',headers:{'access-control-allow-origin':'*'}});}catch{}}
  }
  report.blockedRequests.push(route.request().url());return route.abort();
 });
 await context.routeWebSocket('**/*',socket=>{report.blockedRequests.push(socket.url());socket.close();});
 const page=await context.newPage();page.on('pageerror',e=>report.errors.push(e.message));
 // The pinned Excalidraw font subsetter uses Emscripten-generated functions.
 // Only its nonce-bearing bundle can run; source markup scripts stay blocked.
 const nonce=randomBytes(24).toString('hex');
 await page.setContent(`<html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'nonce-${nonce}' ${format==='excalidraw'?"'unsafe-eval'":"'wasm-unsafe-eval'"}; style-src 'unsafe-inline'; img-src data:; font-src data: https://diagram-ledger.invalid https://esm.sh; connect-src https://diagram-ledger.invalid https://esm.sh; base-uri 'none'"></head><body style="margin:0;background:white"><main id="scene"></main></body></html>`);
 await page.evaluate(()=>{window.EXCALIDRAW_ASSET_PATH='https://diagram-ledger.invalid/';window.cspBlocks=[];document.addEventListener('securitypolicyviolation',e=>window.cspBlocks.push(e.blockedURI));});
 await page.evaluate(({code,nonce})=>{const s=document.createElement('script');s.nonce=nonce;s.textContent=code;document.head.appendChild(s);},{code,nonce});
 const elements=format==='excalidraw'?JSON.parse(source.toString('utf8')).elements:[];
 if(format==='excalidraw'&&(!Array.isArray(elements)||elements.length>3000))throw new Error('Expected an Excalidraw scene with at most 3000 elements.');
 const type=await page.evaluate(async({format,text})=>{
  const host=document.querySelector('#scene');
  if(format==='excalidraw'){
   const scene=JSON.parse(text);
   const svg=await nativeScene.exportToSvg({elements:scene.elements.filter(e=>!e.isDeleted),appState:{...scene.appState,exportEmbedScene:false,exportBackground:true},files:scene.files||{},exportPadding:24});host.appendChild(svg);return 'scene';
  }
  if(/%%\s*\{|^\s*---/m.test(text))throw new Error('Mermaid configuration directives/frontmatter require review; use source syntax without embedded runtime configuration.');
  mermaid.initialize({startOnLoad:false,securityLevel:'strict',theme:'neutral',themeCSS:'.edgeLabel .background { opacity: 1 !important; }',htmlLabels:false,flowchart:{htmlLabels:false},secure:['securityLevel','startOnLoad','maxTextSize','suppressErrorRendering']});
  const type=mermaid.detectType(text);
  if(!['flowchart','flowchart-v2','sequence','state','stateDiagram','stateDiagram-v2','er'].includes(type))throw new Error('Mermaid family outside verified layout scope: '+type);
  const rendered=await mermaid.render('ledger-scene',text);host.innerHTML=rendered.svg;return type;
 },{format,text:source.toString('utf8')});
 await page.evaluate(async()=>{await document.fonts.ready;const svg=document.querySelector('#scene > svg');const b=svg.viewBox.baseVal;if(!b.width||!b.height||b.width>30000||b.height>30000)throw new Error('Invalid or excessive native canvas.');svg.style.maxWidth='none';svg.setAttribute('width',b.width);svg.setAttribute('height',b.height);});
 const measured=await page.evaluate(measureScene,{format,elements});
 const findings=auditLayout(measured.states);findings.unsupported.push(...measured.unsupported);
 report.diagramType=type;report.findings=findings;
 if(format==='mermaid')report.renderSettings={theme:'neutral',edgeLabelBackgroundOpacity:1,securityLevel:'strict'};
 await fs.writeFile(path.join(out,'diagram.svg'),await page.locator('#scene > svg').evaluate(e=>new XMLSerializer().serializeToString(e)));
 report.previewScale=await page.evaluate(()=>{const svg=document.querySelector('#scene > svg'),b=svg.viewBox.baseVal,s=Math.min(1,1500/b.width,7000/b.height);svg.setAttribute('width',b.width*s);svg.setAttribute('height',b.height*s);return s;});
 await page.screenshot({path:path.join(out,'preview.png'),fullPage:true,animations:'disabled'});
 report.blockedRequests.push(...await page.evaluate(()=>window.cspBlocks));
 report.status=report.errors.length||report.blockedRequests.length||findings.routeTextCollisions.length||findings.routeNodeCollisions.length||findings.textOverlaps.length||findings.unsupported.length?'fail':'pass';
}catch(e){report.errors.push(e.message);}finally{if(browser)await browser.close();await fs.writeFile(path.join(out,'audit.json'),JSON.stringify(report,null,2)+'\n');}
console.log(JSON.stringify({status:report.status,format,output:out}));if(report.status!=='pass')process.exitCode=1;
