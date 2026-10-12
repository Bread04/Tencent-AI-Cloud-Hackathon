const {test}=require('node:test');
const assert=require('node:assert/strict');
const api=require('../rider-api.js');
const chat=require('../../shared/agent-chat.js');
const scope={rider_id:'R-7823',trip_id:'TRIP-2026-09945',report_id:'DEMO'};
const report={id:'DEMO',reporterRole:'Rider',trip:{reference:scope.trip_id},statement:'Original account'};
const deferred=()=>{let resolve;const promise=new Promise(yes=>resolve=yes);return {promise,resolve};};

test('adapter posts only report metadata and scope; server owns agents, evidence and locked log',async()=>{
 const requests=[],result={context:scope,original_report:report,transcript_handle:'server-created',communication_log:[],evidence:{log:[]}};
 const client=api.createClient(async(url,options)=>{requests.push({url,options});return {ok:true,status:200,json:async()=>url.endsWith('evidence')?{context:scope,transcript_handle:'evidence-handle',log:[],items:[]}:url.endsWith('policy-preview')?{matches:[]}:result};},{transaction:action=>action()});
 assert.deepEqual(await client.prepareCase({riderId:scope.rider_id,report}),result);
 await client.collectEvidence({riderId:scope.rider_id,tripId:scope.trip_id,report});await client.previewPolicy(report);
 assert.deepEqual(requests.map(r=>r.url),['/api/rider/cases','/api/rider/evidence','/api/rider/policy-preview']);
 assert.deepEqual(JSON.parse(requests[0].options.body),{riderId:scope.rider_id,report});
 assert.deepEqual(JSON.parse(requests[1].options.body),{riderId:scope.rider_id,tripId:scope.trip_id,report});
 for(const {options} of requests){assert.equal(options.method,'POST');assert.equal(options.credentials,'same-origin');assert.equal(options.cache,'no-store');assert.equal(options.headers['Content-Type'],'application/json');}
 assert.equal(api.resolveRider(report),scope.rider_id);assert.throws(()=>api.resolveRider(report,'R-DEMO-02'),/not available/);
});

test('adapter exposes server validation errors and backend outage without browser fallback',async()=>{
 const denied=api.createClient(async()=>({ok:false,status:400,json:async()=>({error:'This trip is not available to the selected rider.'})}),{transaction:action=>action()});
 await assert.rejects(()=>denied.prepareCase({riderId:'R-DEMO-02',report}),error=>error.status===400&&error.message.includes('not available'));
 const offline=api.createClient(async()=>{throw new Error('Offline');},{transaction:action=>action()});
 await assert.rejects(()=>offline.collectEvidence({riderId:scope.rider_id,tripId:scope.trip_id}),/Start the FastAPI server/);
 assert.equal(report.statement,'Original account');
 for(const changed of [{...scope,rider_id:'another'},{...scope,trip_id:'another'}]){
  const wrong=api.createClient(async()=>({ok:true,status:200,json:async()=>({context:changed,original_report:report,transcript_handle:'handle'})}),{transaction:action=>action()});
  await assert.rejects(()=>wrong.prepareCase({riderId:scope.rider_id,report}),/different report or scope/);
 }
});

test('deadline aborts both hanging request and hanging response JSON',async()=>{
 for(const phase of ['fetch','json']){
  let expire,signal;const client=api.createClient(async(_,options)=>{signal=options.signal;return phase==='fetch'?new Promise(()=>{}):{ok:true,status:200,json:()=>new Promise(()=>{})};},{transaction:action=>action(),setTimer:fn=>{expire=fn;return 1;},clearTimer(){}});
  const pending=client.previewPolicy(report);await new Promise(resolve=>setImmediate(resolve));expire();
  await assert.rejects(()=>pending,/timed out/);assert.equal(signal.aborted,true);
 }
});

test('case and evidence owner-cookie requests share AgentChat serialization while preview is independent',async()=>{
 const first=deferred(),requests=[];let cookie='';
 const client=api.createClient(async(url)=>{requests.push({url,cookie});if(url.endsWith('cases')){await first.promise;cookie='server-owner';}return {ok:true,status:200,json:async()=>url.endsWith('policy-preview')?{matches:[]}:{context:scope,original_report:report,transcript_handle:'handle',communication_log:[],log:[]}};},{transaction:chat.transaction});
 const a=client.prepareCase({riderId:scope.rider_id,report}),b=client.collectEvidence({riderId:scope.rider_id,tripId:scope.trip_id});
 await new Promise(resolve=>setImmediate(resolve));assert.equal(requests.length,1);
 await client.previewPolicy(report);assert.equal(requests.length,2);first.resolve();await Promise.all([a,b]);
 assert.deepEqual(requests.map(r=>r.url),['/api/rider/cases','/api/rider/policy-preview','/api/rider/evidence']);
 assert.equal(requests[2].cookie,'server-owner');
});

test('AgentChat retains server-created handle and never registers an empty replacement',async()=>{
 const result={context:scope,original_report:report,transcript_handle:'server-created',communication_log:[],evidence:{log:[]}};
 let calls=0;await chat.prepare(result,{register:async()=>{calls++;return {handle:'wrong'};}});
 assert.equal(calls,0);assert.equal(result.transcript_handle,'server-created');assert.deepEqual(result.original_report,report);
});
