const {test}=require('node:test');
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const data=require('../data.js');
class Element{
 constructor(tag='div'){this.tagName=tag;this.childNodes=[];this.attributes={};this.dataset={};this.value='';this.hidden=false;}
 append(...children){this.childNodes.push(...children);}replaceChildren(...children){this.childNodes=children;this.text='';}
 set textContent(value){this.text=String(value);this.childNodes=[];}get textContent(){return (this.text||'')+this.childNodes.map(item=>item.textContent).join('');}
 setAttribute(name,value){this.attributes[name]=value;}set innerHTML(_){throw new Error('No HTML injection');}
}
function deferred(){let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});return {promise,resolve,reject};}
function policyHarness(){
 const handlers={},requests=[],window={addEventListener:(name,fn)=>handlers[name]=fn,RiderApi:{previewPolicy:report=>{const pending=deferred();requests.push({report,pending});return pending.promise;}}};
 vm.runInNewContext(fs.readFileSync(require.resolve('../report-policy-preview.js'),'utf8'),{window,document:{createElement:tag=>new Element(tag)}});
 return {window,handlers,requests,api:window.RiderPolicyPreview};
}
const policyResult=title=>({matches:[{reference:'R-04',title,category:'Route',excerpt:'Draft guidance',relevance_signals:['Issue category']}]});
test('policy preview discards replaced, changed, reset and disposed responses',async()=>{
 const h=policyHarness(),container=new Element(),a={reporterRole:'Rider',summary:'First'},b={reporterRole:'Rider',summary:'Current'};
 const first=h.api.render(container,a),second=h.api.render(container,b);
 h.requests[1].pending.resolve(policyResult('Current response'));await second;
 h.requests[0].pending.resolve(policyResult('Stale response'));await first;
 assert(container.textContent.includes('Current response'));assert(!container.textContent.includes('Stale response'));
 for(const action of ['change','reset','pagehide','dispose']){
  let current={reporterRole:'Rider',summary:'Before'};const pending=h.api.render(container,current,()=>current);
  if(action==='change')current={...current,summary:'After'};else if(action==='dispose')h.api.dispose(container);else h.handlers[action==='reset'?'waypoint:report-reset':'pagehide']();
  h.requests.at(-1).pending.resolve(policyResult('Should stay hidden'));await pending;
  assert(!container.textContent.includes('Should stay hidden'));
 }
});
test('policy preview displays errors with retry and Driver references remain informational',async()=>{
 const h=policyHarness(),container=new Element(),report={reporterRole:'Rider',summary:'Keep me'};
 const pending=h.api.render(container,report);h.requests[0].pending.reject(new Error('Backend unavailable'));await pending;
 assert(container.textContent.includes('Backend unavailable'));const retry=container.childNodes.find(item=>item.tagName==='button');assert(retry);
 const next=retry.onclick();h.requests.at(-1).pending.resolve(policyResult('Retried'));await next;assert(container.textContent.includes('Retried'));
 const before=h.requests.length;await h.api.render(container,{reporterRole:'Driver'});assert.equal(h.requests.length,before);assert(container.textContent.includes('Driver policy references are available'));
});
function appHarness(){
 const elements=new Map(),get=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
 const handlers={},requests=[],mounts=[];
 const document={getElementById:get,createElement:tag=>new Element(tag),querySelectorAll:()=>[]};
 const RiderCasePanel={load(){},dispose(){}},RiderReportStore={read:()=>null};
 const RiderApi={collectEvidence:options=>{const pending=deferred();requests.push({options,pending});return pending.promise;}};
 const AgentChat={mount:(element,handle,options)=>{const panel={disposed:false,dispose(){this.disposed=true;},readForExport:async()=>{throw new Error('Locked');}};mounts.push({handle,options,panel});return panel;}};
 const window={RydeDemo:data,addEventListener:(name,fn)=>handlers[name]=fn};
 vm.runInNewContext(fs.readFileSync(require.resolve('../app.js'),'utf8'),{window,document,location:{search:'',hash:''},history:{replaceState(){}},URLSearchParams,Intl,Date,Option:class extends Element{constructor(text,value){super('option');this.textContent=text;this.value=value;}},RiderCasePanel,RiderReportStore,RiderApi,AgentChat,Blob,URL,setTimeout});
 return {get,handlers,requests,mounts};
}
test('evidence page cannot render a late response after Rider selection or page disposal',async()=>{
 for(const action of ['select','dispose']){
  const h=appHarness(),pending=h.get('collectEvidence').onclick();
  assert.equal(h.requests.length,1);
  if(action==='select'){h.get('riderSelect').value='R-DEMO-02';h.get('riderSelect').onchange();}else h.handlers.pagehide();
  h.requests[0].pending.resolve({rider_id:'R-7823',trip_id:'TRIP-2026-09945',items:[{status:'available'}]});await pending;
  assert.equal(h.get('evidenceResults').hidden,true);assert.equal(h.get('evidenceList').childNodes.length,0);assert.equal(h.mounts.length,0);
  assert.equal(h.get('collectEvidence').disabled,false);
 }
});
test('standalone evidence uses a locked server handle and exposes offline errors with no local fallback',async()=>{
 const h=appHarness(),pending=h.get('collectEvidence').onclick();
 h.requests[0].pending.resolve({rider_id:'R-7823',trip_id:'TRIP-2026-09945',context:{rider_id:'R-7823',trip_id:'TRIP-2026-09945',report_id:'standalone-evidence'},transcript_handle:'server-handle',log:[],items:[{id:'fixture-record',source:'rider_app.booking',status:'available',timestamp:null,content:{simulated:true}}]});
 await pending;assert.equal(h.mounts[0].handle,'server-handle');assert.equal(h.get('downloadEvidence').disabled,true);
 h.mounts[0].options.onAccessChange(true);assert.equal(h.get('downloadEvidence').disabled,false);
 h.mounts[0].options.onAccessChange(false);assert.equal(h.get('downloadEvidence').disabled,true);
 const failed=h.get('collectEvidence').onclick();h.requests[1].pending.reject(new Error('Start the FastAPI server and retry.'));await failed;
 assert(h.get('appError').textContent.includes('Start the FastAPI server'));assert.equal(h.get('evidenceResults').hidden,true);assert.equal(h.mounts[0].panel.disposed,true);
});
