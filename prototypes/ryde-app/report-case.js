(function () {
  'use strict';
  const mount=document.createElement('div');mount.id='reportRiderCase';document.getElementById('result').append(mount);
  window.addEventListener('waypoint:report-created',event=>{
    mount.replaceChildren();
    const report=event.detail;
    if(report.reporterRole!=='Rider')return;
    try {
      const query=new URLSearchParams(location.search);
      if(query.get('from')==='rider-app'&&query.get('trip')!==report.trip.reference)throw new Error('The report no longer matches the linked trip.');
      const riderId=RiderCasePipeline.resolveRider(report,query.get('from')==='rider-app'?query.get('rider'):null);
      const result=RiderCasePipeline.run({riderId,report});
      let saved=false,saveError='';
      try {RiderReportStore.save(riderId,report.trip.reference,report);RiderCaseStore.save(riderId,report.trip.reference,report,result);saved=true;}
      catch(error){saveError=error.message;}
      const returnUrl=`../ryde-app/index.html?rider=${encodeURIComponent(riderId)}&trip=${encodeURIComponent(report.trip.reference)}&tab=case#workspace`;
      RiderCasePanel.show(mount,result,{saved,saveError,returnUrl:saved?returnUrl:''});
    } catch(error) {
      const message=document.createElement('p');message.className='notice';message.setAttribute('role','status');message.textContent=`Your report is ready, but a Rider case could not be prepared: ${error.message}`;mount.append(message);
    }
  });
  window.addEventListener('waypoint:report-reset',()=>mount.replaceChildren());
})();
