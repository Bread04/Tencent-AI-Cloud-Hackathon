(function () {
  'use strict';
  const mount=document.createElement('div');mount.id='reportRiderCase';document.getElementById('result').append(mount);
  window.addEventListener('waypoint:report-created',event=>{
    RiderCasePanel.dispose(mount);
    const report=event.detail;
    if(report.reporterRole!=='Rider')return;
    try {
      const query=new URLSearchParams(location.search);
      if(query.get('from')==='rider-app'&&query.get('trip')!==report.trip.reference)throw new Error('The report no longer matches the linked trip.');
      const riderId=RiderApi.resolveRider(report,query.get('from')==='rider-app'?query.get('rider'):null);
      const returnUrl=`../ryde-app/index.html?rider=${encodeURIComponent(riderId)}&trip=${encodeURIComponent(report.trip.reference)}&tab=case#workspace`;
      RiderCasePanel.prepare(mount,{riderId,tripId:report.trip.reference,report,returnUrl,saveReport:true});
    } catch(error) {
      const message=document.createElement('p');message.className='notice';message.setAttribute('role','status');message.textContent=`Your report is ready, but a Rider case could not be prepared: ${error.message}`;mount.append(message);
    }
  });
  window.addEventListener('waypoint:report-reset',()=>RiderCasePanel.dispose(mount));
})();
