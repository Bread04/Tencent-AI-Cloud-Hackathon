(function (root) {
  'use strict';
  // Presentation-only adapter. All Evidence, Policy and Advocate rules run in Python.
  // FastAPI is mandatory; there is no browser agent or calculator fallback.
  function createClient(fetcher = (...args) => root.fetch(...args), {timeoutMs = 10000, setTimer = setTimeout, clearTimer = clearTimeout, transaction = action => root.AgentChat.transaction(action)} = {}) {
    async function request(path, payload) {
      const controller = new AbortController(); let timer;
      const work = async () => {
        const response = await fetcher('/api/rider/' + path, {method:'POST', signal:controller.signal,
          credentials:'same-origin', cache:'no-store', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
        const result = await response.json();
        if (!response.ok) throw Object.assign(new Error(result.error || 'The Rider service rejected this request.'), {status:response.status});
        return result;
      };
      try { return await Promise.race([work(), new Promise((_, reject) => {timer=setTimer(() => {controller.abort();reject(new Error('Rider service request timed out.'));},timeoutMs);})]); }
      catch (error) { if(error.status)throw error;throw new Error('Rider service unavailable or timed out. Start the FastAPI server and retry. Your original report is still available.'); }
      finally {clearTimer(timer);}
    }
    function scope(result, riderId, tripId, report) {
      if (result.context?.rider_id !== riderId || result.context?.trip_id !== tripId || typeof result.transcript_handle !== 'string' || !result.transcript_handle || result.communication_log?.length || result.log?.length || result.evidence?.log?.length || (report && JSON.stringify(result.original_report) !== JSON.stringify(report))) throw new Error('The Rider service returned a different report or scope. Retry the current report.');
      return result;
    }
    return Object.freeze({
      prepareCase: ({riderId,report}) => transaction(async () => scope(await request('cases',{riderId,report}),riderId,report.trip.reference,report)),
      collectEvidence: ({riderId,tripId,report=null}) => transaction(async () => scope(await request('evidence',{riderId,tripId,report}),riderId,tripId)),
      previewPolicy: report => request('policy-preview',{report})
    });
  }
  // Synchronous catalog ownership selection is UI logic; Python validates it again.
  function resolveRider(report, selectedRider) {
    const data=root.RydeDemo || require('./data.js');
    if(report?.reporterRole!=='Rider'||typeof report.trip?.reference!=='string')throw new Error('Select a Rider report and known demo trip.');
    if(selectedRider){data.trip(selectedRider,report.trip.reference);return selectedRider;}
    const owners=data.riders().filter(rider=>data.trips(rider.id).some(trip=>trip.id===report.trip.reference));
    if(owners.length!==1)throw new Error('This trip is not in the simulated Rider app. Your report is still available; no trip records were invented.');
    return owners[0].id;
  }
  const api=Object.freeze({...createClient(),createClient,resolveRider});
  root.RiderApi=api;
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof window!=='undefined'?window:globalThis);
