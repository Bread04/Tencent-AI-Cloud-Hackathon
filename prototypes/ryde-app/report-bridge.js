(function () {
  'use strict';
  const query = new URLSearchParams(location.search);
  const back = document.createElement('a'); back.textContent = '← Rider app'; back.href = '../ryde-app/index.html'; back.style.cssText = 'color:var(--teal);font-size:13px;font-weight:650;text-underline-offset:3px';
  document.querySelector('header').append(back);
  if (query.get('from') !== 'rider-app') return;
  const get = id => document.getElementById(id);
  let trip, rider;
  try { rider = RydeDemo.rider(query.get('rider')); trip = RydeDemo.trip(rider.id,query.get('trip')); }
  catch (error) { const note=document.createElement('p');note.className='error';note.textContent=`Rider app link unavailable: ${error.message} No trip has been prefilled.`;document.querySelector('main').prepend(note);return; }
  back.href = `../ryde-app/index.html?rider=${encodeURIComponent(rider.id)}&trip=${encodeURIComponent(trip.id)}&tab=evidence`;
  function prefill() {
    document.querySelector('input[name=role][value=Rider]').checked = true;
    document.querySelector('input[name=role][value=Driver]').disabled = true;
    get('tripSelect').value = ''; get('tripSelect').disabled = true;
    get('tripRef').value = trip.id; get('tripRef').readOnly = true;
    get('tripDate').value = trip.date; get('tripDate').readOnly = true;
    get('tripDetails').value = `${trip.pickup} → ${trip.destination}`; get('tripDetails').readOnly = true;
    get('category').value = trip.category; renderCategory();
    get('location').value = trip.pickup;
    get('tripSample').hidden = false; get('tripSample').textContent = `Simulated rider app trip · ${rider.name} · ${trip.time} SGT. Your statement is left blank for you to complete.`;
    get('loadSample').hidden = true;
    get('sampleNotice').hidden = true;
  }
  prefill();
  get('reset').onclick = () => { if(clearDraft()) prefill(); };
  get('startAnother').onclick = () => { if(clearDraft()) prefill(); };
  const helper = document.createElement('p'); helper.className = 'notice'; helper.textContent = 'Linked rider app demo: after creating a report, you can save its text and attachment metadata to this tab’s session. Original media files remain in this form and are not transferred.';
  get('details').prepend(helper);
  const save = document.createElement('button'); save.type='button'; save.className='primary'; save.id='saveToRiderApp';save.textContent='Save demo report to rider app';
  const notice = document.createElement('p');notice.className='notice';notice.id='appSaveStatus';notice.hidden=true;notice.setAttribute('role','status');
  const returnLink=document.createElement('a');returnLink.href=back.href;returnLink.textContent='Return to rider evidence →';returnLink.style.cssText='display:block;margin-top:15px;color:var(--teal)';
  const section = document.createElement('div');section.className='section'; section.append(save,notice,returnLink);get('result').append(section);
  save.onclick = () => {
    try {
      if (!generated || get('result').hidden) throw new Error('Create and confirm the report first.');
      const payload = JSON.parse(JSON.stringify(generated));
      if(payload.reporterRole!=='Rider'||payload.trip.reference!==trip.id) throw new Error('This report does not match the linked rider trip.');
      payload.trip.simulatedSourceTrip=true;
      RiderReportStore.save(rider.id,trip.id,payload);
      notice.className='notice';notice.textContent='Saved to this browser tab’s session. The Rider Evidence Agent can now collect the report. Media bytes were not saved; nothing was sent to Ryde.';
    }catch(error){notice.className='error';notice.textContent=`Could not save: ${error.message} Use the JSON download to keep your report.`;}
    notice.hidden=false;
  };
  const originalCreate=get('createReport').onclick;
  get('createReport').onclick=()=>{notice.hidden=true;originalCreate();if(generated){generated.trip.simulatedSourceTrip=true;}};
  const side=document.querySelector('.side-foot');side.replaceChildren();const strong=document.createElement('strong');strong.textContent='A local rider app demo';side.append(strong,document.createTextNode('Saving to the rider app is optional. Saved report text and metadata remain in this tab’s session until cleared or the tab closes. No report is sent to Ryde.'));
})();
