(function () {
  'use strict';
  // On the report form: once a report is created, offer to file it as a Dispute and show the Case and its log here.
  const node = (tag, className, text) => { const element = document.createElement(tag); if (className) element.className = className; if (text !== undefined) element.textContent = text; return element; };
  const section = node('div', 'section');
  const note = node('p', 'notice', 'Simulated: filing sends this report to the local demo backend, which creates a Case and runs the agents on mock data. Nothing is sent to Ryde and no money moves.');
  const file = node('button', 'primary', 'File this report as a Dispute');
  file.type = 'button'; file.id = 'fileDispute';
  const mount = node('div'); mount.id = 'reportDispute';
  section.append(note, file, mount);
  document.getElementById('result').append(section);
  let current = null;
  window.addEventListener('waypoint:report-created', event => {
    DisputePanel.dispose(mount);
    current = event.detail;
    file.disabled = false;
  });
  window.addEventListener('waypoint:report-reset', () => { current = null; DisputePanel.dispose(mount); file.disabled = false; });
  file.onclick = async () => {
    if (!current) return;
    const report = current, query = new URLSearchParams(location.search);
    file.disabled = true;
    await DisputePanel.file(mount, report, {onFiled: caseId => {
      if (query.get('from') === 'rider-app') DisputePanel.remember(window.sessionStorage, query.get('rider'), report.trip.reference, caseId);
    }});
    if (current === report) file.disabled = false;
  };
})();
