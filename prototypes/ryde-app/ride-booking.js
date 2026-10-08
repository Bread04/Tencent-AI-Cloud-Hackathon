(() => {
  const form=document.getElementById('ride-form');
  const pickup=document.getElementById('ride-pickup');
  const dropoff=document.getElementById('ride-dropoff');
  const match=document.getElementById('match-result');
  const message=document.getElementById('match-detail');
  const places={
    tbp:{name:'Tiong Bahru Plaza',lat:1.2864,lon:103.8271},
    vivo:{name:'VivoCity',lat:1.2644,lon:103.8222},
    bugis:{name:'Bugis Junction',lat:1.3007,lon:103.8550},
    marina:{name:'Marina Bay Sands',lat:1.2839,lon:103.8590},
    airport:{name:'Changi Airport · T1',lat:1.3644,lon:103.9913},
    orchard:{name:'Orchard Road',lat:1.3048,lon:103.8318}
  };
  const money=n=>`SGD ${n.toFixed(2)}`;
  function estimate(){
    const a=places[pickup.value],b=places[dropoff.value];
    const toRad=n=>n*Math.PI/180;
    const dy=toRad(b.lat-a.lat),dx=toRad(b.lon-a.lon);
    const hav=Math.sin(dy/2)**2+Math.cos(toRad(a.lat))*Math.cos(toRad(b.lat))*Math.sin(dx/2)**2;
    const km=Math.max(.8,6371*2*Math.asin(Math.sqrt(hav))*1.26);
    const factors={everyday:1.35,comfort:1.7,xl:2.05};
    document.querySelectorAll('[data-price]').forEach(el=>{
      const factor=factors[el.dataset.price];
      el.textContent=`Est. ${money(4.2+km*factor)}`;
    });
    return {a,b,km,factors};
  }
  form.addEventListener('change',()=>{match.hidden=true;estimate();});
  form.addEventListener('submit',e=>{
    e.preventDefault();
    const route=estimate();
    if(pickup.value===dropoff.value){
      dropoff.setCustomValidity('Choose a different destination to plan this demo ride.');
      dropoff.reportValidity();return;
    }
    dropoff.setCustomValidity('');
    const type=form.querySelector('[name="ride-type"]:checked').value;
    const factor=route.factors[type];
    const estimate=4.2+route.km*factor;
    const mins=Math.max(5,Math.round(route.km*2.2+4));
    const pickupMinutes=Math.min(8,Math.max(2,Math.round(route.km/4+2)));
    const vehicle=type==='xl'?'Waypoint XL':type==='comfort'?'Waypoint Comfort':'Waypoint Everyday';
    const driver={name:'Jamie L.',initials:'JL'};
    message.textContent=`${driver.name} · ${vehicle} · about ${pickupMinutes} min to pickup. ${route.a.name} to ${route.b.name} · estimated fare ${money(estimate)}. Sample match for your demo rider.`;
    const scene=document.querySelector('#trip-demo waypoint-scene');
    scene?.setRide({pickup:route.a.name,destination:route.b.name,vehicle,minutes:pickupMinutes,duration:mins,price:money(estimate),driver:driver.name});
    document.querySelector('.match-link').setAttribute('data-start-trip','');
    match.hidden=false;
    match.scrollIntoView({behavior:match.matches(':target')?'auto':'smooth',block:'nearest'});
  });
  dropoff.addEventListener('input',()=>dropoff.setCustomValidity(''));
  dropoff.addEventListener('change',()=>dropoff.setCustomValidity(''));
  pickup.addEventListener('input',()=>{match.hidden=true;});
  estimate();
})();
