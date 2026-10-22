/* Key-term glossary for the Markets page: dotted-underlines market terms; tap one for a plain-English definition.
   Same pattern as the case-prep glossary. Definitions live in this file. */
(function(){
if(window.__wajoGloss)return;window.__wajoGloss=true;
var TERMS=[
["IPO","Initial public offering: when a private company sells shares to the public for the first time, which is how it gets listed on a stock exchange."],
["Ticker","The short symbol that identifies a stock, like AAPL for Apple."],
["Offer price","The price set the night before an IPO starts trading: what buyers in the IPO paid per share."],
["Price range","The window a company and its bankers float before an IPO prices; the final offer price usually lands inside it."],
["Shares offered","How many shares are being sold in the IPO itself."],
["Raised","Offer price times shares offered: the money the company pulls in from its IPO."],
["Expected raise","The money an upcoming deal is thought to be worth, estimated from its price range or offer size."],
["Return","How the stock has done since listing: the change from the offer price to the latest price, in percent."],
["Market cap","Share price times all shares outstanding: the whole company's sticker price."],
["Volume","How many shares changed hands today."],
["Day range","The lowest and highest prices the stock touched today."],
["Anticipated","Big private companies reported to be preparing to go public. From press reports, not confirmed by the companies."]
];
var N_EACH=2;
var css=document.createElement('style');
css.textContent=['.gl{border-bottom:1.5px dotted currentColor;cursor:pointer}',
'.gl.on{background:rgba(13,107,97,.14)}',
'#gl-pop{position:fixed;z-index:99999;max-width:340px;width:max-content;background:#13202a;color:#e5ecef;border-radius:10px;padding:12px 14px;box-shadow:0 10px 30px rgba(0,0,0,.4);font:13.5px/1.5 -apple-system,system-ui,sans-serif;display:none}',
'#gl-pop b{display:block;font-size:11.5px;letter-spacing:.06em;text-transform:uppercase;color:#4cc2b1;margin-bottom:4px}'].join('');
document.head.appendChild(css);
var pop=document.createElement('div');pop.id='gl-pop';document.body.appendChild(pop);
var cur=null;
function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
function show(el){
 if(cur)cur.classList.remove('on');
 cur=el;el.classList.add('on');
 var d=el.__def;
 pop.innerHTML='<b>'+esc(d[0])+'</b>'+esc(d[1]);
 pop.style.display='block';
 pop.style.top='';pop.style.bottom='';
 var r=el.getBoundingClientRect();
 var pw=Math.min(340,window.innerWidth-24);
 var left=Math.max(12,Math.min(r.left+r.width/2-pw/2,window.innerWidth-pw-12));
 pop.style.left=left+'px';
 pop.style.setProperty('--ax',(r.left+r.width/2-left)+'px');
 if(r.top>190){pop.style.bottom=(window.innerHeight-r.top+8)+'px';}
 else{pop.style.top=(r.bottom+8)+'px';}
}
function hide(){if(cur)cur.classList.remove('on');cur=null;pop.style.display='none';}
document.addEventListener('click',function(e){
 var g=e.target&&e.target.closest?e.target.closest('.gl'):null;
 if(g){e.preventDefault();e.stopPropagation();show(g);}else hide();
},true);
document.addEventListener('keydown',function(e){if(e.key==='Escape')hide();});
function SKIP(n){
 var p=n.parentNode;
 if(!p||!p.closest)return true;
 return !!p.closest('script,style,.gl,#gl-pop,button,select,input,textarea,.tts-bar,#chat-panel,#chat-fab,.chat-msg,.cb-wrap');
}
function tryNode(node,counts){
 var txt=node.nodeValue;
 if(!txt||txt.length<3)return false;
 for(var k=0;k<TERMS.length;k++){
  var t=TERMS[k];
  if((counts[t[0]]||0)>=N_EACH)continue;
  var re=new RegExp('\\b'+t[0].replace(/[.*+?^${}()|[\]\\]/g,'\\$&').replace(/\s+/g,'\\s+')+'\\b','i');
  var mm=re.exec(txt);
  if(!mm)continue;
  counts[t[0]]=(counts[t[0]]||0)+1;
  var i=mm.index,j=mm.index+mm[0].length;
  var frag=document.createDocumentFragment();
  frag.appendChild(document.createTextNode(txt.slice(0,i)));
  var sp=document.createElement('span');sp.className='gl';sp.textContent=txt.slice(i,j);sp.__def=t;
  frag.appendChild(sp);
  frag.appendChild(document.createTextNode(txt.slice(j)));
  node.parentNode.replaceChild(frag,node);
  return true;
 }
 return false;
}
function scan(){
 var counts={};
 var root=document.body;
 var guard=0,progress=true;
 while(progress&&guard++<800){
  progress=false;
  var w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,{acceptNode:function(n){
   return (SKIP(n)||!n.nodeValue.trim())?NodeFilter.FILTER_REJECT:NodeFilter.FILTER_ACCEPT;}});
  var n;
  while(n=w.nextNode()){
   if(tryNode(n,counts)){progress=true;break;}
  }
 }
}
window.glScan=scan;
if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',scan);}else{scan();}
})();
