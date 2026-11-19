// Аудит тёмной темы: видимый текст, у которого ближайший непрозрачный фон светлый (яркость > 0.35).
// Полупрозрачные фоны (альфа < 0.5, как кнопки шапки) не считаются. Возвращает список находок.
(()=>{
  // rgb()/rgba() и color(srgb …) — так Chrome отдаёт цвета из color-mix()
  const par=c=>{
    let m=c.match(/rgba?\(([^)]+)\)/);
    if(m){const p=m[1].split(/[ ,/]+/).filter(Boolean).map(Number);return {r:p[0],g:p[1],b:p[2],a:p.length>3?p[3]:1}}
    m=c.match(/color\(srgb ([^)]+)\)/);
    if(m){const p=m[1].split(/[ /]+/).filter(Boolean).map(Number);return {r:p[0]*255,g:p[1]*255,b:p[2]*255,a:p.length>3?p[3]:1}}
    return null};
  const lum=({r,g,b})=>{const f=v=>{v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4)};return 0.2126*f(r)+0.7152*f(g)+0.0722*f(b)};
  const bgOf=el=>{for(let e=el;e&&e.nodeType===1;e=e.parentElement){const c=par(getComputedStyle(e).backgroundColor);if(c&&c.a>=0.5)return c}return par(getComputedStyle(document.body).backgroundColor)};
  const vis=e=>{if(!e.isConnected)return false;const cs=getComputedStyle(e);if(cs.visibility==='hidden'||cs.display==='none'||+cs.opacity===0)return false;const r=e.getBoundingClientRect();return r.width>1&&r.height>1&&e.offsetParent!==null||cs.position==='fixed'};
  const out=[];const seen=new Set();
  const all=[...document.querySelectorAll('body *')];
  for(const e of all){
    if(['SCRIPT','STYLE','svg','path','OPTION'].includes(e.tagName))continue;
    let txt='';
    if(e.tagName==='INPUT'||e.tagName==='TEXTAREA'){if(['checkbox','radio','range','file','hidden','color'].includes(e.type))continue;txt=e.value||e.placeholder||' '}
    else if(e.tagName==='SELECT')txt=e.options[e.selectedIndex]?e.options[e.selectedIndex].text:' ';
    else for(const n of e.childNodes)if(n.nodeType===3&&n.textContent.trim())txt+=n.textContent.trim();
    if(!txt||!vis(e))continue;
    const bg=bgOf(e),L=lum(bg);
    if(L>0.35){
      const id=(e.id?'#'+e.id:'')+'.'+[...e.classList].join('.')+'<'+(e.parentElement&&(e.parentElement.id||[...e.parentElement.classList].join('.')))+'> '+e.tagName;
      const k=id+'|'+txt.slice(0,20);if(seen.has(k))continue;seen.add(k);
      out.push({el:id,txt:txt.slice(0,40),bg:`rgb(${bg.r},${bg.g},${bg.b})`,L:+L.toFixed(2)});
    }
  }
  return out;
})()
