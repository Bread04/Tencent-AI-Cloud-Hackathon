(function(root){
  'use strict';
  const states=new WeakMap(), active=new Set();
  const node=(tag,cls,text)=>{const item=document.createElement(tag);if(cls)item.className=cls;if(text!==undefined)item.textContent=text;return item;};
  function dispose(container){const state=states.get(container);if(state){state.active=false;active.delete(state);}}
  async function render(container,report,currentReport=()=>report){
    dispose(container);const state={active:true};states.set(container,state);active.add(state);
    const snapshot=JSON.stringify(report),current=()=>state.active&&JSON.stringify(currentReport())===snapshot;
    container.replaceChildren();
    if(report.reporterRole!=='Rider'){container.append(node('p','notice','This agent is rider-only. Driver policy references are available in the Policies section.'));return;}
    container.append(node('p','hint','Loading draft policy references…'));
    try{
      const result=await root.RiderApi.previewPolicy(report);if(!current())return;
      container.replaceChildren();
      if(!result.matches.length){container.append(node('p','hint','No matching rider clauses were found. You can still read the full policy guide.'));return;}
      result.matches.forEach(match=>{const article=node('article','policy-match'),heading=node('div','policy-match-heading');heading.append(node('strong',null,match.reference+' · '+match.title),node('span','policy-match-category',match.category));article.append(heading,node('p',null,match.excerpt),node('p','policy-match-signals','Matched from: '+match.relevance_signals.join('; ')));container.append(article);});
      container.append(node('p','policy-match-foot','Draft references only · No findings, fault assessment, refund or compensation recommendation.'));
    }catch(error){if(current()){const message=node('p','notice error',error.message);message.setAttribute('role','alert');const retry=node('button','ghost small','Retry policy preview');retry.type='button';retry.onclick=()=>render(container,currentReport(),currentReport);container.replaceChildren(message,retry);}}
  }
  function clear(){for(const state of active)state.active=false;active.clear();}
  root.addEventListener?.('waypoint:report-reset',clear);root.addEventListener?.('pagehide',clear);
  root.RiderPolicyPreview=Object.freeze({render,dispose});
})(typeof window!=='undefined'?window:globalThis);
