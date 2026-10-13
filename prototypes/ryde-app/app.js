(function () {
  'use strict';
  const el = id => document.getElementById(id), data = window.RydeDemo;
  const money = value => `SGD ${value.toFixed(2)}`;
  const time = value => new Intl.DateTimeFormat('en-SG', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Singapore' }).format(new Date(value));
  const node = (tag, className, text) => { const n = document.createElement(tag); if (className) n.className = className; if (text !== undefined) n.textContent = text; return n; };
  const query = new URLSearchParams(location.search);
  let riderId = query.get('rider') || data.riders()[0].id, tripId, tab = ['evidence','case'].includes(query.get('tab')) ? query.get('tab') : 'overview', bundle = null;
  let evidenceGeneration=0, evidenceChat=null;
  try { data.rider(riderId); } catch { riderId = data.riders()[0].id; }
  tripId = query.get('trip') || data.trips(riderId)[0].id;
  try { data.trip(riderId, tripId); } catch { tripId = data.trips(riderId)[0].id; showError('The requested trip is not available to this rider. Showing their own trip instead.'); }
  function showError(message) { el('appError').textContent = message; el('appError').hidden = false; }
  function readReport() {
    try { return RiderReportStore.read(riderId, tripId); }
    catch (error) { showError(`Session report unavailable: ${error.message}`); return null; }
  }
  function updateLocation() { try { history.replaceState(null, '', `?rider=${encodeURIComponent(riderId)}&trip=${encodeURIComponent(tripId)}&tab=${tab}${location.hash}`); } catch {} }
  function switchTab(next) {
    tab = next;
    document.querySelectorAll('[data-tab]').forEach(b => { const selected = b.dataset.tab === next; b.setAttribute('aria-pressed', String(selected)); el(b.dataset.tab).hidden = !selected; });
    updateLocation();
  }
  function invalidateEvidence() { evidenceGeneration++;evidenceChat?.dispose();evidenceChat=null;bundle = null;el('collectEvidence').disabled=false;el('downloadEvidence').disabled=true;el('evidenceResults').hidden = true;el('collectionNotice').textContent = 'No evidence collected yet. Run the agent to inspect the records.'; }
  function invalidate() { invalidateEvidence();RiderCasePanel.dispose(el('riderCaseMount'));DisputePanel.dispose(el('filedDisputeMount')); }
  function render() {
    const rider = data.rider(riderId), trips = data.trips(riderId), trip = data.trip(riderId, tripId);
    el('greeting').textContent = rider.name.split(' ')[0]; el('avatar').textContent = rider.initials;
    el('riderSelect').value = riderId; el('tripCount').textContent = trips.length;
    el('tripList').replaceChildren();
    trips.forEach(t => {
      const b = node('button', 'trip-choice'); b.type = 'button'; b.setAttribute('aria-pressed', String(t.id === tripId)); b.dataset.trip = t.id;
      const row = node('span', 'row'); row.append(node('strong', '', new Intl.DateTimeFormat('en-SG', {day:'numeric',month:'short',timeZone:'Asia/Singapore'}).format(new Date(`${t.date}T12:00:00+08:00`))), node('span', `tag ${t.status === 'Cancelled' ? 'cancelled' : ''}`, t.status));
      const journey = node('span', 'journey', t.pickup); journey.append(node('small', '', `→ ${t.destination}`));
      b.append(row, journey, node('span', 'small muted', `${t.time} SGT · ${t.sampleReport ? t.sampleReport.id + ' · ' : ''}${t.category} · ${t.receipt ? money(t.receipt.total) : 'Fare unavailable'}`));
      b.onclick = () => { tripId = t.id; el('appError').hidden = true; invalidate(); render(); };
      el('tripList').append(b);
    });
    el('tripMeta').textContent = `${trip.date} · ${trip.time} SGT · ${trip.category}`; el('tripTitle').textContent = trip.service.split(' · ')[0];
    el('tripId').textContent = trip.id; el('tripStatus').textContent = trip.status; el('tripStatus').className = `status ${trip.status === 'Cancelled' ? 'cancelled' : ''}`;
    el('pickup').textContent = trip.pickup; el('destination').textContent = trip.destination; el('fare').textContent = trip.receipt ? money(trip.receipt.total) : 'Fare unavailable';
    el('fixture').textContent = `Source: ${trip.fixture}. All times shown in Singapore time.`;
    el('timeline').replaceChildren();
    trip.events.forEach(event => { const li = node('li'); li.append(node('strong', '', event.title), node('p', '', event.detail), node('time', '', `${time(event.timestamp)} SGT`)); el('timeline').append(li); });
    el('reportLink').href = `../ryde-report/index.html?from=rider-app&rider=${encodeURIComponent(riderId)}&trip=${encodeURIComponent(tripId)}`;
    el('receiptId').textContent = trip.receipt?.id || 'Receipt unavailable'; el('receiptLines').replaceChildren();
    if (trip.receipt) {
      [...trip.receipt.lines, {label:'Total charged',amount:trip.receipt.total}].forEach((line, i) => {
        const row = node('div', `receipt-row ${i === trip.receipt.lines.length ? 'total' : ''}`); row.append(node('dt','',line.label),node('dd','',money(line.amount))); el('receiptLines').append(row);
      });
    }
    el('paymentMethod').textContent = trip.receipt ? `${trip.receipt.method} · ${time(trip.receipt.timestamp)} SGT · Simulated receipt` : 'No rider receipt is supplied for this trip. Fare and payment details are unavailable.';
    el('messageList').replaceChildren();
    if (!trip.messages.length) el('messageList').append(node('p','notice','No conversation records are supplied for this trip.'));
    trip.messages.forEach(message => {
      const b = node('article', `message ${message.sender === 'Rider' ? 'mine' : ''}`); b.append(node('div','meta',`${message.sender === 'Rider' ? 'You' : message.sender === 'Driver' ? 'Driver → you' : message.sender}${message.type === 'call' ? ' · Call log' : ''} · ${time(message.timestamp)} SGT`),node('p','',message.text)); el('messageList').append(b);
    });
    const report = readReport(); el('savedHint').textContent = report ? 'A rider report is saved in this app session.' : 'Photos and files can be added in the report form.';
    RiderCasePanel.load(el('riderCaseMount'),{riderId,tripId,report});
    const filedCase = DisputePanel.recall(window.sessionStorage, riderId, tripId); // a Dispute filed from the report form for this trip
    if (filedCase) DisputePanel.resume(el('filedDisputeMount'), filedCase);
    // Keep recovery available even when a stored report is malformed.
    el('clearReport').hidden = !report && el('appError').hidden;
    switchTab(tab);
  }
  data.riders().forEach(r => el('riderSelect').append(new Option(`${r.name} · ${r.id}`, r.id)));
  el('riderSelect').onchange = () => { riderId = el('riderSelect').value; tripId = data.trips(riderId)[0].id; el('appError').hidden = true; invalidate(); render(); };
  document.querySelectorAll('[data-tab]').forEach(b => b.onclick = () => switchTab(b.dataset.tab));
  el('collectEvidence').onclick = async () => {
    invalidateEvidence();const version=evidenceGeneration,selectedRider=riderId,selectedTrip=tripId;
    el('collectEvidence').disabled=true;el('collectionNotice').textContent='Collecting Rider evidence from the local Python service…';
    try {
      const report = RiderReportStore.read(riderId, tripId);
      const result=await RiderApi.collectEvidence({riderId:selectedRider,tripId:selectedTrip,report});
      if(version!==evidenceGeneration)return;
      bundle=result;
      const available = bundle.items.filter(i => i.status === 'available').length;
      el('collectionNotice').textContent = `Collection complete for ${data.rider(riderId).name} · ${tripId}. No live Ryde data accessed.`;
      el('evidenceSummary').textContent = `${available} available · ${bundle.items.length - available} missing`;
      el('evidenceList').replaceChildren();
      bundle.items.forEach(item => {
        const details = node('details','evidence-item'), summary = node('summary');
        summary.append(node('span','',item.source.replace('rider_app.','').replaceAll('_',' ')),node('span',`state ${item.status}`,item.status));
        const body = node('div','evidence-body'); body.append(node('p','',`${item.id} · ${item.timestamp || 'Timestamp unavailable'} · rider side`),node('pre','',JSON.stringify(item.content,null,2)));
        details.append(summary,body); el('evidenceList').append(details);
      });
      evidenceChat=AgentChat.mount(el('communicationLog'),bundle.transcript_handle,{context:bundle.context,caseLabel:tripId,
        onRecover:()=>el('collectEvidence').onclick(),onAccessChange:unlocked=>{el('downloadEvidence').disabled=!unlocked;}});
      el('evidenceResults').hidden = false;
    } catch (error) { if(version===evidenceGeneration){invalidateEvidence();showError(error.message);el('clearReport').hidden = false;} }
    finally {if(version===evidenceGeneration)el('collectEvidence').disabled=false;}
  };
  el('downloadEvidence').onclick = async () => {
    if (!bundle || bundle.rider_id !== riderId || bundle.trip_id !== tripId) return;
    const version=evidenceGeneration;
    try{
    const log=await evidenceChat.readForExport();if(version!==evidenceGeneration)return;
    const url = URL.createObjectURL(new Blob([JSON.stringify({...bundle,log},null,2)], {type:'application/json'}));
    const a = node('a'); a.href = url; a.download = `${tripId}-rider-evidence.json`; document.body.append(a); a.click(); a.remove(); setTimeout(()=>URL.revokeObjectURL(url),1000);
    }catch(error){if(version===evidenceGeneration)showError(error.message);}
  };
  el('clearReport').onclick = () => { if (!confirm('Clear the saved demo report and Rider case for this trip from this browser session?')) return; try { RiderCaseStore.remove(riderId,tripId); RiderReportStore.remove(riderId,tripId); el('appError').hidden=true; invalidate(); render(); } catch(error){showError(error.message);} };
  window.addEventListener('pageshow', event => { if(event.persisted){ invalidate(); render(); } });
  window.addEventListener('pagehide',invalidate);
  render();
})();
