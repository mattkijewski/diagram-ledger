/** Runs in a browser against a native Excalidraw or Mermaid SVG export. */
export function measureScene({format, elements=[]}) {
  const svg=document.querySelector('#scene > svg');
  if(!svg)throw new Error('Native renderer produced no SVG.');
  const rect=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height};};
  const union=boxes=>{const x=Math.min(...boxes.map(b=>b.x)),y=Math.min(...boxes.map(b=>b.y));return {x,y,width:Math.max(...boxes.map(b=>b.x+b.width))-x,height:Math.max(...boxes.map(b=>b.y+b.height))-y};};
  const visible=e=>{const c=getComputedStyle(e);return c.display!=='none'&&c.visibility!=='hidden'&&Number(c.opacity)>0;};
  const states=[],unsupported=[];
  function sample(curve) {
    const matrix=curve.getScreenCTM();
    const data=curve.tagName==='path'?curve.getAttribute('d'):null;
    // Each native rough stroke is a separate subpath; never bridge its pen lifts.
    if(data && /m/.test(data.slice(1)))throw new Error('Relative compound path requires native review.');
    const pieces=data?data.split(/(?=M)/).filter(s=>s.trim()):[null];
    return pieces.map(d=>{
      const part=d?document.createElementNS('http://www.w3.org/2000/svg','path'):curve;
      if(d)part.setAttribute('d',d);
      const length=part.getTotalLength();
      if(!Number.isFinite(length)||length>40000)throw new Error('Excessive or invalid rendered route.');
      const count=Math.max(1,Math.ceil(length/1.5));
      return Array.from({length:count+1},(_,i)=>{const p=part.getPointAtLength(length*i/count),q=new DOMPoint(p.x,p.y).matrixTransform(matrix);return {x:q.x,y:q.y};});
    });
  }
  function textBox(group) {
    const labels=[...group.querySelectorAll('text,foreignObject')].filter(visible).map(rect).filter(b=>b.width&&b.height);
    return labels.length?union(labels):null;
  }
  if(format==='excalidraw') {
    const active=elements.filter(e=>!e.isDeleted),groups=[...svg.children].filter(e=>e.tagName==='g');
    if(active.length!==groups.length)throw new Error('Native SVG element mapping differs from the supported subset; no layout pass can be issued.');
    for(let i=0;i<active.length;i++){
      const e=active[i],g=groups[i],state={id:e.id,label:e.type==='text'?e.text:'',vertex:['rectangle','diamond','ellipse'].includes(e.type),edge:['arrow','line'].includes(e.type),box:rect(g),text:e.type==='text'?textBox(g):null,source:e.startBinding?.elementId,target:e.endBinding?.elementId,parent:e.containerId};
      g.setAttribute('data-source-id',e.id);
      if(e.type==='text'){
        const normalized=s=>s.replace(/\s/g,'');
        if(!state.text || normalized(g.textContent)!==normalized(e.text))unsupported.push({cell:e.id,problem:'Native label mapping could not be verified.'});
      } else if(!g.querySelector('path,ellipse,rect,polygon'))unsupported.push({cell:e.id,problem:'Native shape mapping could not be verified.'});
      if(state.edge)state.routes=[...g.querySelectorAll('path,line,polyline')].filter(p=>!p.closest('mask,defs')).flatMap(sample);
      if(!['rectangle','diamond','ellipse','text','arrow','line'].includes(e.type)||e.frameId||e.link)unsupported.push({cell:e.id,problem:'Element requires native review outside the basic scene subset.'});
      if(e.containerId && active.some(a=>a.id===e.containerId && ['arrow','line'].includes(a.type))) {
        // Native bound-label masks can alter the visible route; do not infer a clean mask from JSON alone.
        unsupported.push({cell:e.id,problem:'Bound connector label requires native mask review; position a free label beside its route for automatic checking.'});
      }
      states.push(state);
    }
  } else {
    // Native Mermaid node/route classes are version-specific; unsupported families are rejected by the caller.
    const nodeGroups=[...svg.querySelectorAll('g.node,g.stateGroup,g.entity,rect.actor')].filter(g=>!g.querySelector('g.node,g.stateGroup,g.entity'));
    for(const [i,g] of nodeGroups.entries()) {
      const body=g.matches('rect')?g:g.querySelector(':scope > rect,:scope > polygon,:scope > circle,:scope > ellipse,:scope > path');
      if(!body)continue;
      states.push({id:g.id||`node-${i}`,vertex:true,box:rect(body),label:'',text:null});
    }
    const routes=[...svg.querySelectorAll('path,line,polyline')].filter(e=>!e.closest('defs,marker,mask')&&visible(e)&&e.getTotalLength()>0&&(e.matches('.flowchart-link,.transition,.relationshipLine,.messageLine0,.messageLine1')||getComputedStyle(e).markerEnd!=='none'||getComputedStyle(e).markerStart!=='none'));
    function nearest(point) {
      const nodes=states.filter(s=>s.vertex).map(s=>({id:s.id,d:Math.hypot(Math.max(s.box.x-point.x,0,point.x-s.box.x-s.box.width),Math.max(s.box.y-point.y,0,point.y-s.box.y-s.box.height))})).filter(s=>s.d<16).sort((a,b)=>a.d-b.d);
      return nodes[0]?.id;
    }
    for(const [i,p] of routes.entries()){
      const lines=sample(p),flat=lines.flat(),id=p.getAttribute('data-id')||p.id||`route-${i}`;
      states.push({id,edge:true,source:nearest(flat[0]),target:nearest(flat.at(-1)),routes:lines,label:''});
    }
    const labels=[...svg.querySelectorAll('text,foreignObject')].filter(e=>!e.closest('defs,marker,mask')&&visible(e)&&e.textContent.trim());
    for(const [i,label] of labels.entries()) {
      const edgeLabel=label.closest('.edgeLabel'),linked=edgeLabel?.querySelector('[data-id]')?.getAttribute('data-id');
      const background=edgeLabel?.querySelector('rect.background');
      const c=background?getComputedStyle(background):null;
      const opaque=c&&c.fill!=='none'&&c.fill!=='transparent'&&!c.fill.startsWith('rgba(')&&Number(c.fillOpacity)===1&&Number(c.opacity)===1;
      const bg=background?rect(background):null,tb=rect(label);
      const covers=bg&&bg.x<=tb.x&&bg.y<=tb.y&&bg.x+bg.width>=tb.x+tb.width&&bg.y+bg.height>=tb.y+tb.height;
      const masks=opaque&&covers&&linked?[linked]:[];
      if(label.classList.contains('sequenceNumber')){
        const badge=label.previousElementSibling,message=badge?.previousElementSibling;
        const reference=badge?.getAttribute('marker-start')?.match(/#([^)]*)/);
        const circle=reference?document.getElementById(reference[1])?.querySelector('circle'):null;
        const paint=circle?getComputedStyle(circle):null;
        if(badge?.tagName==='line'&&badge.getTotalLength()===0&&message?.getAttribute('data-et')==='message'&&paint&&paint.fill!=='none'&&!paint.fill.startsWith('rgba(')&&Number(paint.fillOpacity)===1)masks.push(message.getAttribute('data-id'));
      }
      states.push({id:`label-${i}`,label:label.textContent.trim(),text:rect(label),maskedByEdges:masks});
    }
    if(!labels.length)unsupported.push({problem:'No measurable native labels.'});
  }
  return {states,unsupported};
}
