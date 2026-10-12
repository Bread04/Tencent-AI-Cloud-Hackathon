const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'../../..');
class Element {
 constructor(){this.children=[];this.style={};this.options=[];this.value='0';this.dataset={};}
 append(...children){this.children.push(...children);}
 replaceChildren(...children){this.text='';this.children=children;}
 set textContent(value){this.text=String(value);this.children=[];}
 get textContent(){return (this.text||'')+this.children.map(item=>item?.textContent??String(item)).join('');}
 setAttribute(){} addEventListener(){}
}
function render(id){
 const elements=new Map(),get=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
 const document={body:{dataset:{threshold:'0.7'}},getElementById:get,createElement:()=>new Element(),createElementNS:()=>new Element(),querySelectorAll:()=>[],addEventListener(){}};
 const source=fs.readFileSync(path.join(root,'src/api/static/console.js'),'utf8').replace(/\}\)\(\);\s*$/,'globalThis.renderForTest={renderSummary,renderRuling};})();');
 const context={document,location:{search:''},URLSearchParams,matchMedia:()=>({matches:true}),setTimeout,clearTimeout};
 vm.runInNewContext(source,context);
 const body=JSON.parse(fs.readFileSync(path.join(root,'src/api/static/recorded',id+'.json'),'utf8'));
 context.renderForTest.renderSummary(body.case,body.log);context.renderForTest.renderRuling(body.case);
 return {summary:get('summaryCard').textContent,ruling:get('ruling').textContent};
}
test('actual console renderer keeps an above-threshold route proposal pending and requires review in both panels',()=>{
 const view=render('DISP-010');
 for(const text of Object.values(view)){
  assert(text.includes('Decision pending human review'));
  assert(text.includes('A review trigger requires a person to review this proposal'));
  assert(!text.includes('no review needed'));assert(!text.includes("Rider's claim rejected"));
 }
});
test('actual console renderer presents a partial route refund with its code calculation',()=>{
 const view=render('DISP-008');
 assert(view.summary.includes("Rider's claim partially upheld"));assert(view.summary.includes('SGD 5.39'));
 assert(view.ruling.includes('ADR 0004'));assert(view.ruling.includes('EV-ROUTE-1'));assert(view.ruling.includes('EV-FARE-1'));
});
