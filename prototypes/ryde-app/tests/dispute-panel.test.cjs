const {test}=require('node:test');
const assert=require('node:assert/strict');
const {createClient,isFinished,describe,remember,recall}=require('../dispute-panel.js');

const report={id:'DEMO-1',reporterRole:'Rider',trip:{reference:'TRIP-1'}};
const body=(status,extra={})=>({case:{case_id:'CASE-0001',status,ruling:null,dispute:{filed_report:report}},log:[],run_error:null,...extra});
const reply=(status,payload)=>Promise.resolve({ok:status<400,status,json:()=>Promise.resolve(payload)});
const memory=()=>{const m=new Map();return {getItem:k=>m.get(k)??null,setItem:(k,v)=>m.set(k,v)};};

test('filing posts the report as it is and returns the Case ID',async()=>{
 const seen=[];
 const client=createClient(async(url,options)=>{seen.push([url,options.method,JSON.parse(options.body)]);return reply(202,{case_id:'CASE-0001'});});
 assert.equal(await client.fileReport(report),'CASE-0001');
 assert.deepEqual(seen,[['/api/reports','POST',report]]);
});

test('a refused report surfaces the server reason, so the form can show it',async()=>{
 const client=createClient(async()=>reply(422,{error:'Trip TRIP-NOPE does not exist.'}));
 await assert.rejects(client.fileReport(report),{message:'Trip TRIP-NOPE does not exist.',status:422});
});

test('no server means a plain instruction, never a hang',async()=>{
 const client=createClient(async()=>{throw new TypeError('Failed to fetch');});
 await assert.rejects(client.fileReport(report),/Start the FastAPI server/);
});

test('watching a Case polls until the run finishes and reports each step',async()=>{
 const steps=[body('filed'),body('judging'),body('ruled')],updates=[];
 const client=createClient(async()=>reply(200,steps.shift()),{wait:async()=>{}});
 const final=await client.watch('CASE-0001',update=>updates.push(update.case.status));
 assert.equal(final.case.status,'ruled');assert.deepEqual(updates,['filed','judging','ruled']);
});

test('a failed run ends the watch and keeps its error',async()=>{
 const client=createClient(async()=>reply(200,body('judging',{run_error:'ModelError: down'})),{wait:async()=>{}});
 assert.equal((await client.watch('CASE-0001',()=>{})).run_error,'ModelError: down');
});

test('a run that never finishes stops after the poll limit',async()=>{
 const client=createClient(async()=>reply(200,body('judging')),{wait:async()=>{},maxPolls:3});
 await assert.rejects(client.watch('CASE-0001',()=>{}),/still running/);
});

test('rejected, held and ruled Cases all count as finished; a running one does not',()=>{
 for(const status of ['rejected','pending_review','ruled','notified','closed'])assert.equal(isFinished(body(status)),true,status);
 for(const status of ['filed','prioritised','gathering_evidence','building_cases','judging'])assert.equal(isFinished(body(status)),false,status);
});

test('describe tells a final Ruling, a held proposal and a rejection apart, and always says simulated',()=>{
 const ruling={status:'final',outcome:'uphold',remedy:'fee_reversal',amount:'5.00',currency:'SGD',reasoning_summary:'Driver was 40 m away.',confidence:{value:0.8,components:{evidence:0.9}},review_triggers:[]};
 const ruled=describe(body('notified',{case:{...body('notified').case,ruling}}));
 assert.match(ruled.headline,/uphold/i);assert.equal(ruled.amount,'SGD 5.00');assert.match(ruled.simulated,/simulated/i);
 const held=describe(body('pending_review',{case:{...body('pending_review').case,ruling:{...ruling,status:'proposal',review_triggers:[{trigger:'low_confidence',reason:'Confidence is low.'}]}}}));
 assert.match(held.headline,/no final decision/i);assert.deepEqual(held.reasons,['low_confidence: Confidence is low.']);
 const rejected=describe(body('rejected',{log:[{kind:'case_rejected',summary:'Dispute rejected: Trip X does not exist.'}]}));
 assert.match(rejected.headline,/rejected/i);assert.match(rejected.reasons[0],/Trip X/);
});

test('the filed Case is remembered per rider and trip in the tab session',()=>{
 const storage=memory();
 remember(storage,'R-1','TRIP-1','CASE-0007');
 assert.equal(recall(storage,'R-1','TRIP-1'),'CASE-0007');
 assert.equal(recall(storage,'R-1','TRIP-2'),null);
 assert.equal(recall({getItem(){throw new Error('denied');}},'R-1','TRIP-1'),null);
});
