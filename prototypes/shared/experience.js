(() => {
  const reduce=matchMedia('(prefers-reduced-motion: reduce)');
  const items=[...document.querySelectorAll('[data-reveal]')];
  let scheduled=false;
  function update(){scheduled=false;for(const el of items){const rect=el.getBoundingClientRect();const progress=reduce.matches?1:Math.max(0,Math.min(1,(innerHeight*.98-rect.top)/(Math.min(innerHeight*.38,260))));el.style.setProperty('--reveal',progress.toFixed(3));el.style.setProperty('--reveal-offset',`${((1-progress)*52).toFixed(1)}px`);el.style.setProperty('--reveal-scale',(0.94+progress*.06).toFixed(3));}}
  function queue(){if(!scheduled){scheduled=true;requestAnimationFrame(update);}}
  if(!reduce.matches)document.documentElement.classList.add('motion-enabled');
  update();addEventListener('scroll',queue,{passive:true});addEventListener('resize',queue);
  reduce.addEventListener('change',()=>{document.documentElement.classList.toggle('motion-enabled',!reduce.matches);update();});
  // Keyboard users should never land on a visually hidden control.
  document.addEventListener('focusin',e=>{const section=e.target.closest('[data-reveal]');if(section)section.style.setProperty('--reveal','1');});
  document.querySelectorAll('[data-open-scene]').forEach(link=>link.addEventListener('click',()=>{
    const details=document.getElementById('trip-demo');
    if(details){
      details.open=true;
      if(link.hasAttribute('data-start-trip'))requestAnimationFrame(()=>{
        const scene=details.querySelector('waypoint-scene');
        if(scene){scene.view='rider';scene.progress=0;scene.update();scene.play();}
      });
    }
  }));
})();
