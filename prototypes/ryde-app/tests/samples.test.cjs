const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const data=require('../data.js');
const pipeline=require('../rider-case-pipeline.js');

for(const id of ['DISP-003','DISP-004']){
 test(`${id} app records match the source report without private data or evaluation labels`,()=>{
  const source=JSON.parse(fs.readFileSync(path.join(__dirname,'../../..','data/cases',`${id.toLowerCase()}.json`),'utf8'));
  const sample=data.sampleReports().find(item=>item.id===id);
  assert(sample);
  assert.equal(sample.statement,source.dispute.description);
  assert.equal(sample.tripId,source.trip.trip_id);
  assert.equal(sample.riderId,source.trip.rider_id);
  const trip=data.trip(sample.riderId,sample.tripId);
  assert.equal(trip.receipt.total,Number(source.trip.cancellation_fee));
  assert.equal(trip.receipt.timestamp,source.trip.cancellation_time);
  assert.equal(trip.date,source.trip.scheduled_time.slice(0,10));
  assert.equal(trip.time,source.trip.scheduled_time.slice(11,16));
  assert.deepEqual(trip.messages.map(item=>item.timestamp),source.chat_logs.filter(item=>['rider','driver'].includes(item.sender)).map(item=>item.timestamp));
  assert.deepEqual(trip.messages.map(item=>({sender:item.sender.toLowerCase(),type:item.type||'message',content:item.text})),source.chat_logs.filter(item=>['rider','driver'].includes(item.sender)).map(item=>({sender:item.sender,type:item.type,content:item.content})));
  assert(trip.events.some(item=>item.title==='Trip cancelled'&&item.detail.includes('Driver cancelled')));
  assert(!('waiting' in sample.categoryDetails));
  assert.equal(trip.riderLocations.length,0);
  for(const key of ['gps_telemetry','driver_statement','driver_history','rider_history','expected_outcome','expected_remedy','scenario_classification']){
   assert(!JSON.stringify(trip).includes(key));
  }
  assert.throws(()=>data.trip('R-7823',sample.tripId),/not available/);
 });

 test(`${id} prepares the existing Rider case using its own trip and confirmed sample report`,()=>{
  const sample=data.sampleReports().find(item=>item.id===id);
  const report={id:`DEMO-${id}`,createdAt:'2026-10-11T10:00:00Z',demo:true,reporterRole:'Rider',
   trip:{reference:sample.tripId},category:'No-show / cancellation',summary:sample.summary,statement:sample.statement,
   categoryDetails:sample.categoryDetails,requestedResolution:{type:'Refund',amount:sample.amount,currency:sample.currency},evidence:[],confirmation:'Accurate to the best of my knowledge'};
  assert.equal(pipeline.resolveRider(report),sample.riderId);
  const result=pipeline.run({riderId:sample.riderId,report});
  assert.equal(result.status,'draft');
  assert.equal(result.context.trip_id,sample.tripId);
  assert.equal(result.submission.rider_statement,sample.statement);
  assert(result.evidence.items.every(item=>item.trip_id===sample.tripId&&item.rider_id===sample.riderId));
  assert.equal(result.evidence.items.find(item=>item.source==='rider_app.device_location').status,'missing');
  const calls=result.evidence.items.filter(item=>item.source==='rider_app.conversation'&&item.content.type==='call');
  assert.equal(calls.length,id==='DISP-004'?2:0);
  assert(calls.every(item=>item.content.interpretation.includes('call-log')));
  assert(!('ruling' in result));
  assert.throws(()=>pipeline.run({riderId:'R-7823',report}),/not available/);
 });
}

test('sample templates are independent copies and retain the original DISP-002 example',()=>{
 const samples=data.sampleReports();
 assert.deepEqual(samples.map(sample=>sample.id),['DISP-002','DISP-003','DISP-004']);
 samples[1].statement='Changed';samples[1].categoryDetails.contact='Changed';
 const again=data.sampleReports().find(sample=>sample.id==='DISP-003');
 assert.notEqual(again.statement,'Changed');assert.equal(again.categoryDetails.contact,'In-app message');
});
