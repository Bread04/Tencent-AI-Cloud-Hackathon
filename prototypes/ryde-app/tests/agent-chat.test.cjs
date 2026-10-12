const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const events={};global.addEventListener=(name,fn)=>{events[name]=fn;};
const chat=require('../../shared/agent-chat.js');
const {activity,messages}=chat;
const pipeline=require('./python-results.cjs');
const {create}=require('../rider-case-store.js');
const context={rider_id:'R-7823',trip_id:'TRIP-2026-09945',report_id:'DEMO-CHAT-TEST'};
const log=[
 {agent:'Application',kind:'agent_dispatched',summary:'Saved dispatch',timestamp:'2026-10-12T00:00:00Z'},
 {agent:'Rider Evidence Agent',kind:'evidence_requested',summary:'<img src=x onerror=alert(1)>',references:['<script>ref</script>']},
 {agent:'Rider Evidence Agent',kind:'evidence_returned',summary:'Returned'},
 {agent:'Rider Policy Agent',kind:'policy_retrieved',summary:'Stored policy result'},
 {agent:'Rider Advocate',kind:'submission_prepared',summary:'Submission'}
];
function report(category='No-show / cancellation'){return {id:context.report_id,createdAt:'2026-10-12T00:00:00Z',demo:true,reporterRole:'Rider',trip:{reference:context.trip_id},category,summary:'Please review',statement:'I waited. Please review.',evidence:[],confirmation:'Confirmed'};}
function memory(){const entries=new Map();return {entries,getItem:key=>entries.get(key)||null,setItem:(key,value)=>entries.set(key,value),removeItem:key=>entries.delete(key)};}
function deferred(){let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});return {promise,resolve,reject};}
function backend(){let allowed=false,reads=0;return {get reads(){return reads;},async unlock(_,code){allowed=code==='server-secret';if(!allowed)throw Object.assign(new Error('Denied'),{status:403});},async read(){reads++;if(!allowed)throw Object.assign(new Error('Locked'),{status:403});return {context,communication_log:log,expires_in:1800};},async lock(){allowed=false;}};}
class Element {
 constructor(tag){this.tagName=tag;this.childNodes=[];this.attributes={};this.value='';}
 append(...children){this.childNodes.push(...children);}
 replaceChildren(...children){this.childNodes=[...children];this.text='';}
 setAttribute(name,value){this.attributes[name]=value;}
 set innerHTML(_){throw new Error('Chat must not insert HTML');}
 set textContent(value){this.text=String(value);this.childNodes=[];}
 get textContent(){return (this.text||'')+this.childNodes.map(child=>child.textContent).join('');}
 get firstChild(){return this.childNodes[0];}
 focus(){this.focused=true;}
 click(){this.clicked=true;}
 remove(){}
}
global.document={createElement:tag=>new Element(tag)};
function descendants(root,predicate){return root.childNodes.flatMap(child=>[...(predicate(child)?[child]:[]),...descendants(child,predicate)]);}
function byClass(root,name){return descendants(root,element=>element.className===name);}
async function submit(container,code='server-secret'){
 descendants(container,element=>element.tagName==='input')[0].value=code;
 await descendants(container,element=>element.tagName==='form')[0].onsubmit({preventDefault(){}});
}

test('backend client sends secrets only in POST body and fetches protected data after server validation',async()=>{
 const requests=[];const client=chat.createClient(async(url,options)=>{requests.push({url,options});return {ok:true,status:options.method==='POST'?204:200,json:async()=>({communication_log:log})};});
 await client.unlock('opaque-handle','server-secret');await client.read('opaque-handle');await client.lock('opaque-handle');
 assert.deepEqual(requests.map(r=>r.options.method),['POST','GET','POST']);
 assert.deepEqual(JSON.parse(requests[0].options.body),{code:'server-secret'});
 for(const request of requests){assert(!request.url.includes('server-secret'));assert.equal(request.options.credentials,'same-origin');assert.equal(request.options.cache,'no-store');}
 const failed=chat.createClient(async()=>({ok:false,status:403,json(){throw new Error('Must not parse protected denial');}}));
 await assert.rejects(()=>failed.read('handle'),error=>error.status===403);
 const offline=chat.createClient(async()=>{throw new Error('Offline');});await assert.rejects(()=>offline.read('handle'),/unavailable/);
});

test('registration sends only original public events and minimal IDs; saved case has no activity copies',async()=>{
 const source=report(),result=pipeline.run({riderId:context.rider_id,report:source});const original=JSON.parse(JSON.stringify(result.communication_log));
 let uploaded;await chat.prepare(result,{register:async payload=>{uploaded=JSON.parse(JSON.stringify(payload));return {handle:'opaque-handle'};}});
 assert.deepEqual(Object.keys(uploaded),['context','communication_log']);assert.deepEqual(uploaded.context,context);assert.deepEqual(uploaded.communication_log,original);
 assert.deepEqual(result.communication_log,[]);assert.deepEqual(result.evidence.log,[]);assert.equal(result.transcript_handle,'opaque-handle');assert.deepEqual(result.original_report,source);
 const storage=memory(),store=create(storage);store.save(context.rider_id,context.trip_id,source,result);
 const saved=store.read(context.rider_id,context.trip_id,source);assert.equal(saved.transcript_handle,'opaque-handle');assert.deepEqual(saved.communication_log,[]);assert.deepEqual(saved.evidence.log,[]);
 assert(![...storage.entries.values()][0].includes(original[0].summary));
});

test('backend failure redacts logs while preserving case and original report for recovery',async()=>{
 const source=report(),result=pipeline.run({riderId:context.rider_id,report:source});
 await assert.rejects(()=>chat.prepare(result,{register:async()=>{throw new Error('Backend unavailable');}}),/unavailable/);
 assert.deepEqual(result.communication_log,[]);assert.deepEqual(result.evidence.log,[]);assert.deepEqual(result.original_report,source);assert(result.submission);
 const store=create(memory());store.save(context.rider_id,context.trip_id,source,result);assert(store.read(context.rider_id,context.trip_id,source).submission);
});

test('case-bound filtering preserves text, citations, timestamps and original order',()=>{
 const snapshot=JSON.stringify(log);assert.deepEqual(messages(log).map(item=>item.summary),log.map(item=>item.summary));
 assert.deepEqual(messages(log,'Rider Evidence').map(item=>item.summary),[log[1].summary,log[2].summary]);assert.equal(JSON.stringify(log),snapshot);
 assert.equal(activity(log[1]).route,'Reads Rider-visible records');assert.equal(activity(log[2]).route,'Returns to local case store');assert.equal(activity(log[4]).route,'Submission → local case store');
 assert.equal(activity(log[1]).references[0],'<script>ref</script>');
 const old={agent:'Application',kind:'handoff_recorded',summary:'Evidence Agent → local case store → Policy Agent: original report'};
 assert.equal(activity(old).route,'Application coordination · via local case store');assert.equal(activity(old).summary,old.summary);assert.equal(activity(old).timestamp,'');
 const unknown=activity({agent:'Unrecognised <agent>',kind:'new_kind',summary:'Recorded'});assert.equal(unknown.sender,'Recorded activity (Unrecognised <agent>)');assert.equal(unknown.route,'Recorded activity · local case store');
});

test('actual cases contain only their recorded actors and unsupported categories only Application',()=>{
 const result=pipeline.run({riderId:context.rider_id,report:report()});assert.deepEqual([...new Set(messages(result.communication_log).map(item=>item.actor))],['Application','Rider Evidence','Rider Policy','Rider Advocate']);
 const unsupported=pipeline.run({riderId:context.rider_id,report:report('Safety / conduct')});assert.deepEqual([...new Set(messages(unsupported.communication_log).map(item=>item.actor))],['Application']);
});

test('panel starts locked without API reads, rejects denial, renders safely, filters and revokes on Lock',async()=>{
 const container=new Element('section'),service=backend(),changes=[];
 const panel=chat.mount(container,'opaque-handle',{context,backend:service,onAccessChange:value=>changes.push(value)});
 try{
  assert.equal(service.reads,0);assert.equal(byClass(container,'agent-chat-messages').length,0);assert(!container.textContent.includes(log[1].summary));
  for(const value of ['', 'wrong']){await submit(container,value);assert.equal(byClass(container,'agent-chat-messages').length,0);assert.equal(byClass(container,'agent-chat-error')[0].attributes.role,'alert');}
  await submit(container);assert.equal(byClass(container,'agent-chat-message').length,log.length);assert.equal(byClass(container,'agent-chat-summary')[1].textContent,log[1].summary);assert.equal(byClass(container,'agent-chat-citations')[0].textContent,log[1].references[0]);assert(container.textContent.includes('Timestamp not recorded'));
  const select=descendants(container,e=>e.tagName==='select')[0];select.value='Rider Policy';select.onchange();assert.deepEqual(byClass(container,'agent-chat-summary').map(e=>e.textContent),['Stored policy result']);select.value='';select.onchange();assert.equal(byClass(container,'agent-chat-message').length,log.length);
  assert.equal(service.reads,1);await byClass(container,'agent-chat-lock')[0].onclick();assert.equal(byClass(container,'agent-chat-messages').length,0);assert(!container.textContent.includes(log[1].summary));assert.equal(changes.at(-1),false);await assert.rejects(()=>service.read(),/Locked/);
 }finally{panel.dispose();}
});

test('late retrieval after Lock or replacement cannot repopulate transcript',async()=>{
 for(const action of ['lock','replace']){
  const container=new Element('section'),response=deferred(),service=backend();service.read=()=>response.promise;
  const panel=chat.mount(container,'old-handle',{context,backend:service});const pending=submit(container);await Promise.resolve();
  let replacement;if(action==='lock')await panel.lock();else replacement=chat.mount(container,'new-handle',{context,backend:backend()});
  response.resolve({context,communication_log:log,expires_in:1800});await pending;
  assert.equal(byClass(container,'agent-chat-message').length,0);assert(!container.textContent.includes(log[1].summary));panel.dispose();replacement?.dispose();
 }
});

test('late unlock after restoration is discarded without revoking a newer cookie and requires fresh code entry',async()=>{
 const container=new Element('section'),response=deferred();let locks=0,reads=0;
 const panel=chat.mount(container,'handle',{backend:{unlock:()=>response.promise,read:async()=>{reads++;return {communication_log:log};},lock:async()=>{locks++;}}});
 const pending=submit(container);events.pagehide();events.pageshow({persisted:true});response.resolve();await pending;
 assert.equal(reads,0);assert.equal(locks,0);assert.equal(byClass(container,'agent-chat-message').length,0);panel.dispose();
});

test('case export requires a fresh authorized read and denial or expiry clears messages',async()=>{
 const container=new Element('section'),service=backend(),panel=chat.mount(container,'handle',{context,backend:service});
 await assert.rejects(()=>panel.readForExport(),/Unlock/);assert.equal(service.reads,0);
 await submit(container);assert.deepEqual(await panel.readForExport(),log);assert.equal(service.reads,2);
 await service.lock();await assert.rejects(()=>panel.readForExport(),/Locked/);assert.equal(byClass(container,'agent-chat-message').length,0);panel.dispose();
 const expiring=backend();const read=expiring.read;expiring.read=async()=>({...await read(),expires_in:0.01});
 const expiryPanel=chat.mount(container,'handle',{context,backend:expiring});await submit(container);await new Promise(resolve=>setTimeout(resolve,30));assert.equal(byClass(container,'agent-chat-message').length,0);assert(container.textContent.includes('expired'));expiryPanel.dispose();
});

function panelHarness(storage=memory()){
 const store=create(storage);let runs=0,uploads=0;
 const root={RiderCaseStore:store,RiderApi:{prepareCase:async options=>{runs++;return pipeline.run(options);}},AgentChat:{...chat,prepare:result=>chat.prepare(result,{register:async()=>{uploads++;return {handle:'registered-handle'};}})}};
 vm.runInNewContext(fs.readFileSync(require.resolve('../rider-case-panel.js'),'utf8'),{window:root,document:global.document,Blob,URL,setTimeout});
 return {root,store,storage,get runs(){return runs;},get uploads(){return uploads;}};
}
test('opening an older stored case uploads its existing events once without rerunning agents',async()=>{
 const h=panelHarness(),source=report(),result=pipeline.run({riderId:context.rider_id,report:source}),container=new Element('div');
 h.storage.setItem(`waypoint:rider-case:v1:${context.rider_id}:${context.trip_id}`,JSON.stringify(result));
 await h.root.RiderCasePanel.load(container,{riderId:context.rider_id,tripId:context.trip_id,report:source});
 assert.equal(h.runs,0);assert.equal(h.uploads,1);const saved=h.store.read(context.rider_id,context.trip_id,source);assert.equal(saved.transcript_handle,'registered-handle');assert.deepEqual(saved.communication_log,[]);assert.deepEqual(saved.evidence.log,[]);
 assert.equal(byClass(container,'agent-chat-messages').length,0);
 await h.root.RiderCasePanel.load(container,{riderId:context.rider_id,tripId:context.trip_id,report:source});assert.equal(h.uploads,1);assert.equal(h.runs,0);h.root.RiderCasePanel.dispose(container);
});

test('storage denial and backend outage keep public case content with explicit recovery and disabled export',async()=>{
 const h=panelHarness({setItem(){throw new Error('Storage denied');}}),source=report(),container=new Element('div');
 h.root.AgentChat.prepare=result=>chat.prepare(result,{register:async()=>{throw new Error('Backend unavailable. Retry after starting the server.');}});
 await h.root.RiderCasePanel.prepare(container,{riderId:context.rider_id,tripId:context.trip_id,report:source});
 assert(container.textContent.includes('Your side, clearly presented.'));assert(container.textContent.includes(source.statement));assert(container.textContent.includes('Storage denied'));assert(container.textContent.includes('Backend unavailable'));assert(container.textContent.includes('Prepare Communication Log again'));assert.equal(descendants(container,e=>e.tagName==='button'&&e.textContent==='Download Rider case JSON')[0].disabled,true);h.root.RiderCasePanel.dispose(container);
});

test('trip switching or report reset during registration cannot restore replaced case content',async()=>{
 const h=panelHarness(),pending=deferred(),container=new Element('div');h.root.AgentChat.prepare=result=>chat.prepare(result,{register:()=>pending.promise});
 const preparation=h.root.RiderCasePanel.prepare(container,{riderId:context.rider_id,tripId:context.trip_id,report:report()});h.root.RiderCasePanel.dispose(container);pending.resolve({handle:'old-handle'});await preparation;
 assert.equal(container.childNodes.length,0);assert.equal(h.storage.entries.size,0);
});

test('deadline aborts both a hanging fetch and hanging JSON without stranding public case preparation',async()=>{
 for(const phase of ['fetch','json']){
  let expire,signal;const client=chat.createClient(async(_,options)=>{signal=options.signal;return phase==='fetch'?new Promise(()=>{}):{ok:true,status:200,json:()=>new Promise(()=>{})};},{setTimer:fn=>{expire=fn;return 1;},clearTimer(){}});
  const source=report(),result=pipeline.run({riderId:context.rider_id,report:source});
  const pending=chat.prepare(result,client);await new Promise(resolve=>setImmediate(resolve));expire();
  await assert.rejects(()=>pending,/timed out/);assert.equal(signal.aborted,true);assert.deepEqual(result.communication_log,[]);assert.deepEqual(result.original_report,source);assert(result.submission);
 }
});

test('same-document registrations issue sequentially after the owner cookie response',async()=>{
 const first=deferred(),requests=[];let cookie='';
 const client=chat.createClient(async()=>{requests.push(cookie);if(requests.length===1){await first.promise;cookie='owner';}return {ok:true,status:201,json:async()=>({handle:'handle-'+requests.length})};});
 const a=client.register({}),b=client.register({});await new Promise(resolve=>setImmediate(resolve));assert.deepEqual(requests,['']);first.resolve();await Promise.all([a,b]);assert.deepEqual(requests,['','owner']);
});

test('Web Locks serializes first registrations across tabs until the cookie response completes',async()=>{
 let tail=Promise.resolve(),cookie='';const requests=[],first=deferred();
 const locks={request(name,action){assert.equal(name,'ryde-chat-cookie');const result=tail.then(action);tail=result.catch(()=>{});return result;}};
 const make=()=>{const window={navigator:{locks},fetch:async()=>{requests.push(cookie);if(requests.length===1){await first.promise;cookie='owner';}return {ok:true,status:201,json:async()=>({handle:'h'})};}};vm.runInNewContext(fs.readFileSync(require.resolve('../../shared/agent-chat.js'),'utf8'),{window,AbortController,setTimeout,clearTimeout});return window.AgentChat.client;};
 const a=make().register({}),b=make().register({});await new Promise(resolve=>setImmediate(resolve));assert.deepEqual(requests,['']);first.resolve();await Promise.all([a,b]);assert.deepEqual(requests,['','owner']);
});

test('prototype property names remain unknown recorded actors',()=>{
 for(const agent of ['constructor','__proto__','toString'])assert.equal(activity({agent}).sender,`Recorded activity (${agent})`);
});

test('user denial and Lock focus the replacement code input while expiry does not',async()=>{
 const container=new Element('section'),service=backend(),panel=chat.mount(container,'handle',{backend:service});
 await submit(container,'wrong');assert.equal(descendants(container,e=>e.tagName==='input')[0].focused,true);
 await submit(container);await panel.lock();assert.equal(descendants(container,e=>e.tagName==='input')[0].focused,true);
 panel.clear('Expired');assert.equal(descendants(container,e=>e.tagName==='input')[0].focused,undefined);panel.dispose();
});

test('a stale unlock cannot revoke a replacement panel that successfully unlocked',async()=>{
 const container=new Element('section'),old=deferred();let revokes=0;
 chat.mount(container,'old',{backend:{unlock:()=>old.promise,lock:async()=>{revokes++;}}});const pending=submit(container);
 const replacement=chat.mount(container,'new',{backend:backend()});await submit(container);old.resolve();await pending;
 assert.equal(revokes,0);assert.equal(byClass(container,'agent-chat-message').length,log.length);replacement.dispose();
});

test('failed legacy migration preserves old storage and retry uses original events and timestamps',async()=>{
 const h=panelHarness(),source=report(),original=pipeline.run({riderId:context.rider_id,report:source}),container=new Element('div');
 const key=`waypoint:rider-case:v1:${context.rider_id}:${context.trip_id}`,raw=JSON.stringify(original);h.storage.setItem(key,raw);let attempts=0,uploaded;
 h.root.AgentChat.prepare=result=>chat.prepare(result,{register:async payload=>{attempts++;uploaded=JSON.parse(JSON.stringify(payload));if(attempts===1)throw new Error('Offline');return {handle:'migrated'};}});
 await h.root.RiderCasePanel.load(container,{riderId:context.rider_id,tripId:context.trip_id,report:source});assert.equal(h.storage.getItem(key),raw);assert.equal(h.runs,0);
 await descendants(container,e=>e.tagName==='button'&&e.textContent==='Prepare Communication Log again')[0].onclick();
 assert.deepEqual(uploaded.communication_log,original.communication_log);assert.equal(h.runs,0);assert.equal(h.store.read(context.rider_id,context.trip_id,source).transcript_handle,'migrated');h.root.RiderCasePanel.dispose(container);
});

test('successful legacy migration saves its original scoped handle even after panel disposal',async()=>{
 const h=panelHarness(),source=report(),original=pipeline.run({riderId:context.rider_id,report:source}),container=new Element('div'),pending=deferred();
 h.storage.setItem(`waypoint:rider-case:v1:${context.rider_id}:${context.trip_id}`,JSON.stringify(original));h.root.AgentChat.prepare=result=>chat.prepare(result,{register:()=>pending.promise});
 const loading=h.root.RiderCasePanel.load(container,{riderId:context.rider_id,tripId:context.trip_id,report:source});h.root.RiderCasePanel.dispose(container);pending.resolve({handle:'migrated-away'});await loading;
 assert.equal(container.childNodes.length,0);assert.equal(h.store.read(context.rider_id,context.trip_id,source).transcript_handle,'migrated-away');
});

test('recovery retries the required report save before claiming the case and report are saved',async()=>{
 const h=panelHarness(),container=new Element('div');let reportSaves=0,allow=false;
 h.root.RiderReportStore={save(){reportSaves++;if(!allow)throw new Error('Report storage denied');}};
 h.root.AgentChat.prepare=result=>chat.prepare(result,{register:async()=>{if(!allow)throw new Error('Offline');return {handle:'recovered'};}});
 await h.root.RiderCasePanel.prepare(container,{riderId:context.rider_id,tripId:context.trip_id,report:report(),saveReport:true});assert(container.textContent.includes('Report storage denied'));
 allow=true;await descendants(container,e=>e.tagName==='button'&&e.textContent==='Prepare Communication Log again')[0].onclick();
 assert.equal(reportSaves,2);assert(container.textContent.includes('Saved with this report'));h.root.RiderCasePanel.dispose(container);
});

test('rendered export downloads a fresh authorized log with the original report and case; denial creates no Blob',async()=>{
 const h=panelHarness(),source=report(),result=pipeline.run({riderId:context.rider_id,report:source}),container=new Element('div'),service=backend();
 chat.redact(result);result.transcript_handle='handle';h.root.AgentChat.mount=(element,handle,options)=>chat.mount(element,handle,{...options,backend:service});
 const blobs=[],originalCreate=URL.createObjectURL,originalRevoke=URL.revokeObjectURL;global.document.body=new Element('body');URL.createObjectURL=blob=>{blobs.push(blob);return 'blob:demo';};URL.revokeObjectURL=()=>{};
 try{h.root.RiderCasePanel.show(container,result);await submit(container);const fresh=[{agent:'Application',kind:'recorded',summary:'Fresh export'}];service.read=async()=>({context,communication_log:fresh,expires_in:1800});const download=descendants(container,e=>e.tagName==='button'&&e.textContent==='Download Rider case JSON')[0];await download.onclick();assert.equal(blobs.length,1);assert.deepEqual(JSON.parse(await blobs[0].text()),{...result,communication_log:fresh});assert.deepEqual(JSON.parse(await blobs[0].text()).original_report,source);
 service.read=async()=>{throw Object.assign(new Error('Denied'),{status:403});};await download.onclick();assert.equal(blobs.length,1);assert.equal(download.disabled,true);assert.equal(byClass(container,'agent-chat-message').length,0);
 }finally{h.root.RiderCasePanel.dispose(container);URL.createObjectURL=originalCreate;URL.revokeObjectURL=originalRevoke;}
});

test('actual report-created and reset events cannot save or render a late registration',async()=>{
 const h=panelHarness(),listeners={},result=new Element('div'),pending=deferred();h.root.addEventListener=(name,fn)=>{listeners[name]=fn;};h.root.RiderApi.resolveRider=()=>context.rider_id;h.root.RiderReportStore={save(){}};h.root.AgentChat.prepare=record=>chat.prepare(record,{register:()=>pending.promise});
 const document={...global.document,getElementById:id=>id==='result'?result:null};vm.runInNewContext(fs.readFileSync(require.resolve('../report-case.js'),'utf8'),{window:h.root,document,location:{search:''},URLSearchParams,RiderCasePanel:h.root.RiderCasePanel,RiderApi:h.root.RiderApi});
 listeners['waypoint:report-created']({detail:report()});listeners['waypoint:report-reset']();pending.resolve({handle:'late'});await new Promise(resolve=>setImmediate(resolve));assert.equal(result.childNodes[0].childNodes.length,0);assert.equal(h.storage.entries.size,0);
});

test('shared bounded cross-tab invalidation clears Rider transcripts and invokes Case subscribers',async()=>{
 const channels=[];class Channel {constructor(name){assert.equal(name,'ryde-chat-invalidation');channels.push(this);}postMessage(data){assert.equal(data,'locked');for(const peer of channels)if(peer!==this)peer.onmessage?.({data});}}
 const make=()=>{const handlers={};const window={BroadcastChannel:Channel,addEventListener:(name,fn)=>{handlers[name]=fn;},document:global.document};vm.runInNewContext(fs.readFileSync(require.resolve('../../shared/agent-chat.js'),'utf8'),{window,document:global.document,AbortController,setTimeout,clearTimeout});return {api:window.AgentChat,handlers};};
 const rider=make(),casePage=make(),container=new Element('section');const panel=rider.api.mount(container,'handle',{backend:backend()});await submit(container);let caseClears=0;casePage.api.onInvalidation(()=>caseClears++);casePage.api.invalidate();assert.equal(caseClears,1);assert.equal(byClass(container,'agent-chat-message').length,0);
 await submit(container);rider.handlers.focus();assert.equal(byClass(container,'agent-chat-message').length,0);panel.dispose();
});

test('Python case API failure preserves report before requesting and retries without browser agent fallback',async()=>{
 const h=panelHarness(),source=report(),container=new Element('div'),order=[];let attempts=0;
 h.root.RiderReportStore={save(rider,trip,value){assert.equal(rider,context.rider_id);assert.equal(trip,context.trip_id);assert.deepEqual(value,source);order.push('saved');}};
 h.root.RiderApi.prepareCase=async()=>{order.push('requested');attempts++;throw new Error('Start the FastAPI server and retry.');};
 await h.root.RiderCasePanel.prepare(container,{riderId:context.rider_id,tripId:context.trip_id,report:source,saveReport:true});
 assert.deepEqual(order,['saved','requested']);assert.equal(h.runs,0);assert.equal(h.uploads,0);assert.equal(h.storage.entries.size,0);
 assert(container.textContent.includes('Start the FastAPI server'));assert(!container.textContent.includes('Your side, clearly presented.'));
 await descendants(container,e=>e.tagName==='button'&&e.textContent==='Retry Rider case')[0].onclick();
 assert.equal(attempts,2);assert.deepEqual(order,['saved','requested','saved','requested']);assert.equal(source.statement,report().statement);
 h.root.RiderCasePanel.dispose(container);
});

test('server-created case handle persists without upload and late case API response cannot revive disposed panel',async()=>{
 const h=panelHarness(),source=report(),container=new Element('div'),fixture=pipeline.run({riderId:context.rider_id,report:source});
 chat.redact(fixture);fixture.transcript_handle='python-server-handle';h.root.RiderApi.prepareCase=async()=>JSON.parse(JSON.stringify(fixture));
 await h.root.RiderCasePanel.prepare(container,{riderId:context.rider_id,tripId:context.trip_id,report:source});
 assert.equal(h.uploads,0);assert.equal(h.store.read(context.rider_id,context.trip_id,source).transcript_handle,'python-server-handle');assert(container.textContent.includes('Your side, clearly presented.'));
 h.store.remove(context.rider_id,context.trip_id);const pending=deferred();h.root.RiderApi.prepareCase=()=>pending.promise;
 const preparation=h.root.RiderCasePanel.prepare(container,{riderId:context.rider_id,tripId:context.trip_id,report:source});h.root.RiderCasePanel.dispose(container);
 pending.resolve(fixture);await preparation;assert.equal(container.childNodes.length,0);assert.equal(h.storage.entries.size,0);assert.equal(h.uploads,0);
});
