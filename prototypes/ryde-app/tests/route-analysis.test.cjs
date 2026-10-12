// Catalog/API parity replaces the deleted browser/Python calculator parity tests.
const {test}=require('node:test');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../../..'),data=require('../data.js');
test('all public UI records equal the trusted Python catalog and exclude private data',()=>{
 const catalog=JSON.parse(fs.readFileSync(path.join(root,'data/prototype/rider-catalog.json'),'utf8'));
 assert.deepEqual(catalog.riders,data.riders());
 assert.deepEqual(catalog.trips,data.riders().flatMap(rider=>data.trips(rider.id)));
 assert.equal(catalog.trips.length,11);assert.equal(catalog.riders.length,6);
 for(const field of ['rider_history','driver_history','driver_statement','expected_outcome','expected_remedy','scenario_classification'])assert(!JSON.stringify(catalog).includes(field));
 for(const id of ['DISP-008','DISP-009','DISP-010']){
  const raw=JSON.parse(fs.readFileSync(path.join(root,'data/cases',id.toLowerCase()+'.json'),'utf8'));
  const sample=data.sampleReports().find(item=>item.id===id),trip=data.trip(sample.riderId,sample.tripId);
  assert.equal(sample.category,'Route deviation');assert.equal(sample.statement,raw.dispute.description);
  assert.deepEqual(trip.routeRecord,Object.fromEntries(['trip','gps_telemetry','route_baseline','route_landmarks','tariff','receipt'].map(key=>[key,raw[key]])));
  assert.deepEqual(trip.messages.map(m=>m.text),raw.chat_logs.map(m=>m.content));
  assert.equal(trip.receipt.total,Number(raw.receipt.paid_net));
  assert.equal(Math.round(trip.receipt.lines.reduce((sum,line)=>sum+line.amount,0)*100),Math.round(trip.receipt.total*100));
 }
});
test('both pages import only async API adapters and refresh changed cached assets',()=>{
 for(const page of ['prototypes/ryde-app/index.html','prototypes/ryde-report/index.html']){
  const html=fs.readFileSync(path.join(root,page),'utf8');
  assert(html.includes('rider-api.js?feature=python-rider-v1'));
  assert(html.includes('data.js?feature=remaining-samples-v1'));
  if(page.includes('ryde-app/'))assert(html.includes('app.js?feature=remaining-samples-v1'));
  assert(html.includes('agent-chat.js?feature=python-rider-v1'));
  assert(html.indexOf('agent-chat.js?')<html.indexOf('rider-api.js?'));
  for(const name of ['rider-evidence-agent.js','rider-policy-agent.js','rider-advocate-agent.js','rider-case-pipeline.js','route-analysis.js'])assert(!html.includes(name));
 }
 for(const name of ['prototypes/shared/route-analysis.js','prototypes/ryde-app/rider-evidence-agent.js','prototypes/ryde-app/rider-policy-agent.js','prototypes/ryde-app/rider-advocate-agent.js','prototypes/ryde-app/rider-case-pipeline.js'])assert(!fs.existsSync(path.join(root,name)));
});
