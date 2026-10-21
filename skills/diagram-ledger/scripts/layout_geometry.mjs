/** Geometry for rendered diagram states. Coordinates are native canvas pixels. */
export function segmentIntersectsBox(a, b, box, inset = 1) {
  if (!a || !b || !box) return false;
  const left = box.x + inset, right = box.x + box.width - inset;
  const top = box.y + inset, bottom = box.y + box.height - inset;
  if (left >= right || top >= bottom) return false;
  // Slab clipping handles horizontal, vertical and diagonal segments, without sampling.
  let lo = 0, hi = 1;
  for (const [start, delta, min, max] of [[a.x,b.x-a.x,left,right],[a.y,b.y-a.y,top,bottom]]) {
    if (Math.abs(delta) < 1e-9) { if (start <= min || start >= max) return false; }
    else {
      const u = (min-start)/delta, v = (max-start)/delta;
      lo = Math.max(lo, Math.min(u,v)); hi = Math.min(hi, Math.max(u,v));
      if (lo >= hi) return false;
    }
  }
  return hi > lo;
}
const contains = (a,b) => b.x>=a.x && b.y>=a.y && b.x+b.width<=a.x+a.width && b.y+b.height<=a.y+a.height;
const overlaps = (a,b) => Math.min(a.x+a.width,b.x+b.width)-Math.max(a.x,b.x)>1 && Math.min(a.y+a.height,b.y+b.height)-Math.max(a.y,b.y)>1;
export function auditLayout(states) {
  const vertices=states.filter(s=>s.vertex), edges=states.filter(s=>s.edge), labels=states.filter(s=>s.text && s.label);
  // Explicit containers plus top-aligned backgrounds enclosing another complete node.
  const containers=new Set(vertices.filter(s=>s.container || (s.topLabel && vertices.some(n=>n.id!==s.id && contains(s.box,n.box)))).map(s=>s.id));
  const byId=new Map(states.map(s=>[s.id,s]));
  function ancestor(a,b) { const seen=new Set(); while(b && !seen.has(b.id)){seen.add(b.id);if(b.parent===a)return true;b=byId.get(b.parent);}return false; }
  const routeTextCollisions=[],routeNodeCollisions=[],textOverlaps=[],unsupported=[];
  for(const edge of edges) {
    if(edge.curved) {unsupported.push({cell:edge.id,problem:'Curved connector requires native visual review; polyline audit cannot certify it.'});continue;}
    const routes=edge.routes || [edge.points];
    if(!routes.length || routes.some(points=>!points || points.length<2 || points.some(p=>!p || !Number.isFinite(p.x) || !Number.isFinite(p.y)))) {unsupported.push({cell:edge.id,problem:'Connector has no measurable rendered path.'});continue;}
    const crosses=box=>routes.some(points=>points.some((p,i)=>i>0 && segmentIntersectsBox(points[i-1],p,box)));
    for(const label of labels) {
      // The renderer confirms an opaque native background for this edge's own label.
      if((label.id===edge.id && label.opaqueLabel) || label.maskedByEdges?.includes(edge.id))continue;
      if(crosses(label.text))routeTextCollisions.push({edge:edge.id,label:label.id,text:label.label});
    }
    for(const node of vertices) {
      if(node.id===edge.source || node.id===edge.target || containers.has(node.id) || ancestor(node.id,byId.get(edge.source)) || ancestor(node.id,byId.get(edge.target)))continue;
      if(crosses(node.box))routeNodeCollisions.push({edge:edge.id,node:node.id});
    }
  }
  for(let i=0;i<labels.length;i++)for(let j=i+1;j<labels.length;j++)if(overlaps(labels[i].text,labels[j].text))textOverlaps.push({first:labels[i].id,second:labels[j].id});
  return {routeTextCollisions,routeNodeCollisions,textOverlaps,unsupported,containers:[...containers],edgeCount:edges.length,labelCount:labels.length};
}
