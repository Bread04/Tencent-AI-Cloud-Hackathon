/* Independent illustrative simulation. Never reads or writes rider evidence records. */
(() => {
  const assets = new URL('.', document.currentScript.src);
  class WaypointScene extends HTMLElement {
    connectedCallback() {
      if (this.shadowRoot) return;
      this.progress = 0; this.view = 'rider'; this.playing = false; this.lastStage = '';
      this.ride={pickup:'Tiong Bahru Plaza',destination:'VivoCity',vehicle:'Waypoint Everyday',minutes:9,price:'SGD 8.20',driver:'Jamie L.'};
      const root = this.attachShadow({mode:'open'});
      const blocks = [[60,70,75,65,58],[165,55,55,75,84],[325,65,85,65,43],[445,55,48,74,68],[70,185,63,60,34],[325,244,60,68,67],[424,258,85,54,41],[78,350,110,35,8]];
      root.innerHTML = `<link rel="stylesheet" href="${new URL('journey.css',assets)}">
      <section class="experience" aria-label="Interactive simulated trip">
      <div class="toolbar"><p><strong>One trip. Two perspectives.</strong>Interactive 3D illustration · Simulated, not live</p><div class="toggle" role="group" aria-label="Scene perspective"><button data-view="rider" aria-pressed="true">Rider view</button><button data-view="driver" aria-pressed="false">Driver view</button></div></div>
      <div class="scene-layout"><div class="viewport" aria-hidden="true"><span class="scene-label">Waypoint district / Illustrative map</span><div class="world-wrap"><div class="world"><div class="ground"></div><div class="road a"></div><div class="road b"></div><div class="road c"></div>
      <svg class="route" viewBox="0 0 560 420"><path class="base" d="M60 301 H221 V180 H470"/><path class="travelled" d="M60 301 H221 V180 H470" pathLength="100" stroke-dasharray="100" stroke-dashoffset="100"/></svg>
      ${blocks.map(([x,y,w,d,h],i)=>`<div class="block ${i===7?'park':''}" style="left:${x}px;top:${y}px;--w:${w}px;--d:${d}px;--h:${h}px"><i class="roof"></i><i class="front"></i><i class="side"></i></div>`).join('')}
      <div class="pickup-pad"></div><div class="destination-pad"></div><span class="landmark pickup-label" style="left:233px;top:336px">Pickup</span><span class="landmark destination-label" style="left:443px;top:211px">Drop-off</span><div class="car"><i></i><i></i></div><div class="rider"></div></div></div><div class="scene-caption"><span>Driver · Blue car</span><span>Rider · Light marker</span></div></div>
      <div class="panel"><p class="label" data-perspective>Rider perspective</p><div role="status" aria-live="polite" aria-atomic="true"><h3 data-title></h3><p class="detail" data-detail></p></div><div class="event-log" aria-label="Simulated trip messages"></div></div></div>
      <div class="controls"><div class="transport"><button data-play>Play trip ▷</button><button class="reset" data-reset>Reset</button><label>Trip progress<input type="range" min="0" max="100" value="0" step="1" aria-label="Trip progress"><output>0%</output></label></div><div class="stages" aria-label="Jump to a trip moment"><button data-stage="0" aria-current="step">01 · Matched</button><button data-stage="35">02 · Pickup</button><button data-stage="65">03 · Together</button><button data-stage="100">04 · Arrived</button></div><p class="footnote">An invented journey to explore both viewpoints. No real users, messages or GPS. This scene is separate from your app records and evidence.</p></div></section>`;
      this.q = s => root.querySelector(s);
      root.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>{this.view=b.dataset.view;this.update();}));
      root.querySelectorAll('[data-stage]').forEach(b=>b.addEventListener('click',()=>{this.pause();this.progress=Number(b.dataset.stage);this.update();}));
      this.q('[data-play]').addEventListener('click',()=>{if(this.playing)this.pause();else this.play();});
      this.q('[data-reset]').addEventListener('click',()=>{this.pause();this.progress=0;this.update();});
      this.q('input').addEventListener('input',e=>{this.pause();this.progress=Number(e.target.value);this.update();});
      this.onVisibility=()=>{if(document.hidden)this.pause();};
      document.addEventListener('visibilitychange',this.onVisibility);
      this.observer=new IntersectionObserver(entries=>{if(!entries[0].isIntersecting)this.pause();});this.observer.observe(this);
      this.update();
    }
    disconnectedCallback(){this.pause();this.observer?.disconnect();document.removeEventListener('visibilitychange',this.onVisibility);}
    play(){if(this.progress>=100)this.progress=0;this.playing=true;this.q('[data-play]').textContent='Pause trip Ⅱ';let last=performance.now();const tick=now=>{if(!this.playing)return;this.progress=Math.min(100,this.progress+Math.min(now-last,100)/260);last=now;this.update();if(this.progress>=100)this.pause();else this.frame=requestAnimationFrame(tick);};this.frame=requestAnimationFrame(tick);}
    pause(){this.playing=false;cancelAnimationFrame(this.frame);if(this.q)this.q('[data-play]').textContent=this.progress>=100?'Replay trip ↻':'Play trip ▷';}
    update(){
      const p=this.progress, stage=p<35?0:p<65?1:p<100?2:3;
      const ratio=p<35?p/35*.303:p<65?.303:.303+(p-65)/35*.697;
      const distance=ratio*531;
      let x,y,rotation=0;if(distance<=161){x=60+distance;y=301;}else if(distance<=282){x=221;y=301-(distance-161);rotation=-90;}else{x=221+(distance-282);y=180;}
      this.q('.car').style.transform=`translate3d(${x-14}px,${y-8}px,6px) rotateZ(${rotation}deg)`;
      this.q('.rider').style.transform=p<65?'translate3d(218px,328px,20px)':`translate3d(${x-5}px,${y+18}px,22px)`;
      this.q('.travelled').style.strokeDashoffset=100-ratio*100;
      this.q('.world').classList.toggle('driver',this.view==='driver');
      this.shadowRoot.querySelectorAll('[data-view]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.view===this.view)));
      this.q('input').value=Math.round(p);this.q('output').value=`${Math.round(p)}%`;
      this.shadowRoot.querySelectorAll('[data-stage]').forEach((b,i)=>{if(i===stage)b.setAttribute('aria-current','step');else b.removeAttribute('aria-current');});
      this.q('.pickup-label').textContent=this.ride.pickup;
      this.q('.destination-label').textContent=this.ride.destination;
      const key=this.view+stage+this.ride.pickup+this.ride.destination+this.ride.vehicle;if(key===this.lastStage)return;this.lastStage=key;
      const rider=this.view==='rider';this.q('[data-perspective]').textContent=rider?'Rider perspective':'Driver perspective';
      const titles=rider?['Your ride is on the way.','Find each other, easily.','A shared journey begins.','You’ve reached your stop.']:['A new pickup, ahead.','You’re at the pickup.','Your passenger is aboard.','One journey, complete.'];
      const details=rider?[`Your ${this.ride.vehicle} with ${this.ride.driver} is heading to ${this.ride.pickup}. The demo pickup is about ${this.ride.minutes} minutes away.`,`The car has arrived at ${this.ride.pickup}. A quick message helps you both agree on where to meet.`,`You’re on board. Follow the car from ${this.ride.pickup} to ${this.ride.destination}.`,`You’ve reached ${this.ride.destination}. A demo fare estimate of ${this.ride.price} is ready to review.`]:[`You’re driving a sample ${this.ride.vehicle} pickup for ${this.ride.driver}. Follow the route to ${this.ride.pickup}.`,`You’ve arrived at ${this.ride.pickup}. A quick message helps both sides find the same meeting point.`,`Pickup complete. Continue from ${this.ride.pickup} to ${this.ride.destination}.`,`You’ve reached ${this.ride.destination}. Switch views to see the rider’s arrival.`];
      this.q('[data-title]').textContent=titles[stage];this.q('[data-detail]').textContent=details[stage];
      const chats=[['Driver',`I’m on my way to ${this.ride.pickup}.`],['Rider',`I’ll wait at ${this.ride.pickup}.`],['Driver',`I’m here at ${this.ride.pickup}.`],['Rider','I can see you. Coming over now.'],['Rider',`We’re on our way to ${this.ride.destination}.`],['Driver',`We’ve arrived at ${this.ride.destination}. Have a lovely day.`]];
      const selected=stage===0?[0,1]:stage===1?[2,3]:stage===2?[3,4]:[4,5];
      this.q('.event-log').replaceChildren(...selected.map(i=>{const [sender,message]=chats[i],bubble=document.createElement('div');bubble.className='bubble'+(sender.toLowerCase()===this.view?' mine':'');const who=document.createElement('small');who.textContent=sender.toLowerCase()===this.view?`You · ${sender}`:sender;bubble.append(who,document.createTextNode(message));return bubble;}));
    }
    setRide(ride){this.ride={...this.ride,...ride};this.lastStage='';this.update();}
  }
  customElements.define('waypoint-scene',WaypointScene);
})();
