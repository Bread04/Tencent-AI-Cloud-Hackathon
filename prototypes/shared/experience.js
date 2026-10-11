(() => {
  const reduce = matchMedia('(prefers-reduced-motion: reduce)');
  const items = [...document.querySelectorAll('[data-reveal]')];
  const isLanding = document.body.classList.contains('landing');
  const depthItems = isLanding
    ? [...document.querySelectorAll('.hero-drawing,.visual-panel,.interaction-section waypoint-scene,.closing-art')]
    : [];
  const scrollJourneys = isLanding ? [...document.querySelectorAll('[data-scroll-journey]')] : [];
  const stages = [
    { label: '01 / 04 · MATCHED', title: 'Your ride is matched.', body: 'A driver is heading toward Tiong Bahru Plaza.' },
    { label: '02 / 04 · PICKUP', title: 'Meet at the pickup.', body: 'Both sides find the same curb before the trip begins.' },
    { label: '03 / 04 · TOGETHER', title: 'Travel together.', body: 'Follow the car as the route unfolds through the city.' },
    { label: '04 / 04 · ARRIVAL', title: 'Arrive with context.', body: 'The journey ends at VivoCity; your trip details stay ready to review.' }
  ];
  let scheduled = false;

  function update() {
    scheduled = false;
    for (const el of items) {
      const rect = el.getBoundingClientRect();
      const progress = reduce.matches ? 1 : Math.max(0, Math.min(1, (innerHeight * .98 - rect.top) / (Math.min(innerHeight * .38, 260))));
      el.style.setProperty('--reveal', progress.toFixed(3));
      el.style.setProperty('--reveal-offset', `${((1 - progress) * 52).toFixed(1)}px`);
      el.style.setProperty('--reveal-scale', (0.94 + progress * 0.06).toFixed(3));
    }

    for (const el of depthItems) {
      const rect = el.getBoundingClientRect();
      const depth = reduce.matches ? 0 : Math.max(-1, Math.min(1, (innerHeight * .5 - (rect.top + rect.height * .5)) / (innerHeight * .8)));
      const vars = {
        '--scroll-depth': depth, '--depth-angle': depth * 2.2, '--depth-bg-x': depth * -7, '--depth-bg-y': depth * -15,
        '--depth-y-hero': depth * -23, '--depth-y-chip': depth * -18, '--depth-y-driver': depth * 15,
        '--depth-y-evidence': depth * -10, '--depth-y-pip': depth * 22, '--depth-angle-panel': depth * -2.5,
        '--depth-y-panel': depth * -13, '--depth-y-card': depth * -20, '--depth-angle-card': depth * -3,
        '--depth-y-message': depth * -9, '--depth-z-message': 12 + depth * 18, '--depth-y-reply': depth * 12,
        '--depth-y-cards': depth * -12, '--depth-angle-cards': depth * -3, '--depth-y-scene': depth * -20,
        '--depth-angle-scene': depth * -1.2, '--depth-angle-closing': depth * -2, '--depth-y-closing': depth * -15,
        '--depth-y-mascot': depth * 18, '--depth-y-quote': depth * -12
      };
      for (const [name, value] of Object.entries(vars)) {
        const unit = name.includes('angle') ? 'deg' : name.includes('bg') || name.includes('y-') || name.includes('z-') ? 'px' : '';
        el.style.setProperty(name, `${value.toFixed(2)}${unit}`);
      }
    }

    for (const runway of scrollJourneys) {
      const range = Math.max(1, runway.offsetHeight - innerHeight);
      const progress = reduce.matches ? 0 : Math.max(0, Math.min(1, -runway.getBoundingClientRect().top / range));
      runway.style.setProperty('--scroll-progress', progress.toFixed(3));
      const scene = runway.querySelector('waypoint-scene[data-scroll-driven]');
      if (scene && !reduce.matches && Math.abs(scene.progress - progress * 100) > .15) {
        scene.progress = progress * 100;
        scene.update();
      }
      const index = progress < .35 ? 0 : progress < .65 ? 1 : progress < .995 ? 2 : 3;
      if (runway.dataset.currentStage !== String(index)) {
        runway.dataset.currentStage = String(index);
        const stage = stages[index];
        runway.querySelector('[data-scroll-stage]').textContent = stage.label;
        runway.querySelector('[data-scroll-title]').textContent = stage.title;
        runway.querySelector('[data-scroll-body]').textContent = stage.body;
      }
      runway.querySelector('[data-scroll-progress]').style.width = `${progress * 100}%`;
    }
  }

  function queue() {
    if (!scheduled) {
      scheduled = true;
      requestAnimationFrame(update);
    }
  }

  if (!reduce.matches) document.documentElement.classList.add('motion-enabled');
  update();
  addEventListener('scroll', queue, { passive: true });
  addEventListener('resize', queue);
  reduce.addEventListener('change', () => {
    document.documentElement.classList.toggle('motion-enabled', !reduce.matches);
    update();
  });

  // Keyboard users should never land on a visually hidden control.
  document.addEventListener('focusin', e => {
    const section = e.target.closest('[data-reveal]');
    if (section) section.style.setProperty('--reveal', '1');
  });
  document.querySelectorAll('[data-open-scene]').forEach(link => link.addEventListener('click', () => {
    const details = document.getElementById('trip-demo');
    if (details) {
      details.open = true;
      if (link.hasAttribute('data-start-trip')) requestAnimationFrame(() => {
        const scene = details.querySelector('waypoint-scene');
        if (scene) {
          scene.progress = 0;
          scene.update();
          scene.play();
        }
      });
    }
  }));
})();
