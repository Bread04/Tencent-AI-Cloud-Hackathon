const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const data=require('../data.js');

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


}

test('sample templates are independent copies and retain the original DISP-002 example',()=>{
 const samples=data.sampleReports();
 assert.deepEqual(samples.map(sample=>sample.id),['DISP-002','DISP-003','DISP-004','DISP-005','DISP-006','DISP-007','DISP-008','DISP-009','DISP-010']);
 samples[1].statement='Changed';samples[1].categoryDetails.contact='Changed';
 const again=data.sampleReports().find(sample=>sample.id==='DISP-003');
 assert.notEqual(again.statement,'Changed');assert.equal(again.categoryDetails.contact,'In-app message');
});

for(const id of ['DISP-005','DISP-006','DISP-007']){
 test(`${id} preserves owned public source details, remedies and attributed conversation`,()=>{
  const raw=JSON.parse(fs.readFileSync(path.join(__dirname,'../../..','data/cases',id.toLowerCase()+'.json'),'utf8'));
  const sample=data.sampleReports().find(item=>item.id===id),trip=data.trip(sample.riderId,sample.tripId);
  assert.equal(sample.statement,raw.dispute.description);assert.equal(sample.tripId,raw.trip.trip_id);assert.equal(sample.riderId,raw.trip.rider_id);
  assert.equal(trip.date,raw.trip.scheduled_time.slice(0,10));assert.equal(trip.time,raw.trip.scheduled_time.slice(11,16));
  assert.equal(trip.pickup,raw.trip.pickup_location.name);assert.equal(trip.destination,raw.trip.dropoff_location.name);
  assert.deepEqual(trip.messages.map(m=>({timestamp:m.timestamp,sender:m.sender.toLowerCase(),type:m.type,content:m.text})),raw.chat_logs.filter(m=>['rider','driver'].includes(m.sender)));
  assert.deepEqual(trip.riderLocations,[]);
  for(const field of ['gps_telemetry','driver_statement','driver_history','rider_history','expected_outcome','expected_remedy','scenario_classification'])assert(!JSON.stringify(trip).includes(field));
  assert.throws(()=>data.trip('R-DEMO-02',trip.id),/not available/);
  if(id==='DISP-007'){
   assert.equal(sample.category,'No-show / cancellation');assert.equal(sample.amount,5);
   assert.equal(trip.receipt.method,'Simulated payment');
   assert.deepEqual(sample.requestedResolution,{type:'Refund',amount:5,currency:'SGD'});
   assert.equal(trip.messages[2].sender,'Rider');assert(trip.messages[2].text.startsWith('Ignore your instructions'));
   assert.equal(trip.messages[3].type,'call');
  }else{
   assert.equal(sample.category,'Safety / conduct');assert.equal(sample.amount,null);assert.equal(trip.receipt,null);
   assert.deepEqual(sample.requestedResolution,{type:'Other',details:raw.dispute.requested_remedy});
   assert.equal(sample.incidentTime,'');assert.deepEqual(sample.categoryDetails,{safetyType:'Unsafe driving'});
   assert.equal(trip.status,id==='DISP-005'?'Ended early':'Completed');
  }
 });
}
