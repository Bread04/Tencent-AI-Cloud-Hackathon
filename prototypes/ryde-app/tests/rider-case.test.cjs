const {test}=require('node:test');
const assert=require('node:assert/strict');
const pipeline=require('./python-results.cjs');
const {create}=require('../rider-case-store.js');
const {redact}=require('../../shared/agent-chat.js');
const riderId='R-7823',tripId='TRIP-2026-09945';
const report=(overrides={})=>({id:'DEMO-CASE-TEST',createdAt:'2026-10-11T10:00:00Z',demo:true,submitted:false,refundProcessed:false,mediaIncluded:false,
 reporterRole:'Rider',trip:{reference:tripId},category:'No-show / cancellation',summary:'Review SGD 5 no-show fee',statement:'I waited at the pickup point. Please review the cancellation fee.',categoryDetails:{waiting:'10'},requestedResolution:{type:'Refund',amount:5,currency:'SGD'},evidence:[],confirmation:'Accurate to the best of my knowledge',...overrides});
function memory(){const entries=new Map();return {getItem:k=>entries.get(k)||null,setItem:(k,v)=>entries.set(k,v),removeItem:k=>entries.delete(k)};}

test('session cases stay scoped, reject stale report snapshots, and can be cleared',()=>{
 const source=report(),result=pipeline.run({riderId,report:source}),store=create(memory());
 assert.throws(()=>store.save(riderId,tripId,source,result),/Register/);
 result.transcript_handle='opaque-server-handle';redact(result);
 store.save(riderId,tripId,source,result);assert.deepEqual(store.read(riderId,tripId,source),result);
 assert.throws(()=>store.read(riderId,tripId,{...source,statement:'Updated account'}),/snapshot/);
 assert.equal(store.read('R-DEMO-02','TRIP-DEMO-AISHA-01',report({trip:{reference:'TRIP-DEMO-AISHA-01'}})),null);
 assert.throws(()=>store.save('R-DEMO-02','TRIP-DEMO-AISHA-01',source,result),/snapshot/);
 store.remove(riderId,tripId);assert.equal(store.read(riderId,tripId,source),null);
});

test('storage failures propagate and output mutations do not alter later collections',()=>{
 const source=report(),result=pipeline.run({riderId,report:source});
 const store=create({setItem(){throw new Error('Quota exceeded');}});
 result.transcript_handle='opaque-server-handle';redact(result);
 assert.throws(()=>store.save(riderId,tripId,source,result),/Quota/);
 result.evidence.items[0].content.pickup='Changed';result.original_report.statement='Changed';
 const next=pipeline.run({riderId,report:source});assert.notEqual(next.evidence.items[0].content.pickup,'Changed');assert.equal(next.original_report.statement,source.statement);
});
