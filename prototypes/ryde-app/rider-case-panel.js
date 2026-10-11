(function (root) {
  'use strict';
  const node = (tag, cls, text) => { const element=document.createElement(tag); if(cls) element.className=cls; if(text!==undefined) element.textContent=text; return element; };
  const button = (text, action) => { const element=node('button','secondary-button',text); element.type='button'; element.onclick=action; return element; };
  function download(result) {
    const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));
    const link=node('a'); link.href=url; link.download=`${result.context.report_id}-rider-case.json`; document.body.append(link); link.click(); link.remove(); setTimeout(()=>URL.revokeObjectURL(url),1500);
  }
  function show(mount, result, {saved=false, saveError='', returnUrl=''}={}) {
    mount.replaceChildren();
    const panel=node('section','rider-case'); panel.setAttribute('aria-label','Your Rider case');
    const head=node('div','case-header');
    const title=node('div'); title.append(node('p','case-eyebrow','Rider case studio / Local prototype'),node('h3','',result.status==='draft'?'Your side, clearly presented.':'This report needs support review.'));
    head.append(title,node('span','case-badge',result.status==='draft'?'Rider Submission draft':'Support routing')); panel.append(head);
    panel.append(node('p','case-intro',result.status==='draft'?'Your Evidence, Policy and Advocate agents have assembled a review request from the selected trip. This is the Rider’s argument, not a Judge’s decision.':result.message));
    if (result.status==='draft') {
      const stages=node('ol','case-stages');
      for (const [number,name,detail] of [['03','Evidence','Trip records and gaps'],['04','Policy','Relevant draft clauses'],['05','Advocate','Your supported case']]) {
        const stage=node('li'); stage.append(node('span','case-stage-number',number),node('strong','',name),node('span','',detail)); stages.append(stage);
      }
      panel.append(stages);
      if(result.review_required) panel.append(node('p','case-warning','Possible safety concern: human review is needed. This demo has not contacted support or emergency services.'));
      panel.append(node('p','case-reference',`${result.context.trip_id} · ${result.context.report_id}`));
      const statement=node('details','case-details'); statement.append(node('summary','','Your original report'),node('p','case-quote',result.submission.rider_statement)); panel.append(statement);
      const request=result.submission.requested_outcome;
      panel.append(node('p','case-request',`Requested help: ${request.type || 'Review the report'}${request.amount!==undefined?` · ${request.currency} ${request.amount.toFixed(2)}`:''}${request.details?` · ${request.details}`:''}`));
      function points(title, items, cls) {
        const section=node('section',`case-section ${cls || ''}`); section.append(node('h4','',title));
        const list=node('ol','case-points');
        for(const item of items){const point=node('li'); if(item.title) point.append(node('strong','',item.title)); point.append(node('p','',item.text));
          const refs=[...(item.evidence_ids || []),...(item.policy_ids || [])]; if(refs.length) point.append(node('p','case-citations',refs.join(' · '))); list.append(point);}
        section.append(list); panel.append(section);
      }
      points('The case for the Rider',result.submission.arguments);
      points('Counter-evidence and policy limits',result.submission.counter_arguments,'case-counter');
      if(result.submission.gaps.length) points('What still needs to be checked',result.submission.gaps,'case-gaps');
      panel.append(node('p','case-conclusion',result.submission.conclusion));
      const policy=node('details','case-details'); policy.append(node('summary','',`Policy references · ${result.policy.matches.length}`));
      result.policy.matches.forEach(match=>{const article=node('article','case-policy');article.append(node('h4','',`${match.reference} · ${match.title}`),node('p','',match.excerpt),node('p','case-citations',match.relevance_signals.join(' · ')));policy.append(article);});
      policy.append(node('p','case-reference',result.policy_version)); panel.append(policy);
      const records=node('details','case-details'); records.append(node('summary','',`Source records · ${result.evidence.items.length}`));
      result.evidence.items.forEach(item=>{const source=node('details','case-source');source.append(node('summary','',`${item.source.replace('rider_app.','')} · ${item.status}`),node('p','case-citations',item.id),node('pre','',JSON.stringify(item.content,null,2)));records.append(source);});panel.append(records);
    }
    const communication=node('details','case-details case-communication'); communication.open=true;
    communication.append(node('summary','','How the agents worked together'));
    const log=node('ol','case-log'); result.communication_log.forEach(entry=>{const item=node('li');item.append(node('strong','',entry.agent),node('span','',entry.summary),node('small','',entry.kind));if(entry.references?.length)item.append(node('small','case-citations',entry.references.join(' · ')));log.append(item);});communication.append(log);panel.append(communication);
    const foot=node('p','case-foot'); foot.textContent=saveError?`Prepared in this page, but session save failed: ${saveError} Download the case to keep a copy.`:saved?'Saved with this report in this browser tab’s session. Media bytes are not included.':'Prepared in page memory. Download to keep a copy; closing this page clears this copy.';foot.setAttribute('role','status');panel.append(foot);
    panel.append(node('p','case-foot','Predefined rules, simulated records and draft policies. No live AI, Driver Submission, Judge Ruling, or refund processing.'));
    const actions=node('div','case-actions');actions.append(button('Download Rider case JSON',()=>download(result)));
    if(returnUrl){const link=node('a','case-link','View in the Rider app →');link.href=returnUrl;actions.append(link);} panel.append(actions); mount.append(panel);
  }
  function load(mount, {riderId,tripId,report}) {
    mount.replaceChildren();
    if(!report){mount.append(node('p','notice','Create a Rider report for this trip to prepare your case. You can start from “Report an issue” in Overview.'));return;}
    function prepare(){
      try {const result=RiderCasePipeline.run({riderId,report});let saved=false,saveError='';try{RiderCaseStore.save(riderId,tripId,report,result);saved=true;}catch(error){saveError=error.message;}show(mount,result,{saved,saveError});}
      catch(error){mount.replaceChildren(node('p','notice error',`Rider case unavailable: ${error.message}`));}
    }
    try {const result=RiderCaseStore.read(riderId,tripId,report);if(result){show(mount,result,{saved:true});return;}}
    catch(error){mount.append(node('p','notice',`The previous case cannot be used: ${error.message}`));}
    mount.append(node('p','notice','A Rider report is saved for this trip. Prepare a local case using its evidence and policies.'),button('Prepare Rider case',prepare));
  }
  root.RiderCasePanel=Object.freeze({show,load});
})(window);
