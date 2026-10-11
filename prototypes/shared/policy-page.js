(function () {
  'use strict';
  const tabs = [...document.querySelectorAll('[data-role]')];
  const cards = document.getElementById('policyCards');
  function show(role) {
    const clauses = WaypointPolicies.clauses.filter(item => item.role === role);
    cards.replaceChildren();
    clauses.forEach(item => {
      const article = document.createElement('article'); article.className = 'policy-card';
      const ref = document.createElement('span'); ref.className = 'policy-ref'; ref.textContent = `WAYPOINT / ${item.id}`;
      const title = document.createElement('h3'); title.textContent = item.title;
      const copy = document.createElement('p'); copy.textContent = item.text;
      const category = document.createElement('span'); category.className = 'policy-category'; category.textContent = item.category;
      article.append(ref, title, copy, category); cards.append(article);
    });
    tabs.forEach(tab => { const selected = tab.dataset.role === role; tab.setAttribute('aria-selected', String(selected)); tab.tabIndex = selected ? 0 : -1; });
    cards.setAttribute('aria-labelledby', role === 'Rider' ? 'riderTab' : 'driverTab');
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => show(tab.dataset.role));
    tab.addEventListener('keydown', event => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length;
      tabs[next].focus(); show(tabs[next].dataset.role);
    });
  });
  document.getElementById('policySources').replaceChildren(...WaypointPolicies.sourceNotes.map(source => {
    const li = document.createElement('li'), a = document.createElement('a');
    a.href = source.url; a.target = '_blank'; a.rel = 'noopener noreferrer'; a.textContent = source.label;
    li.append(a); return li;
  }));
  show('Rider');
})();
