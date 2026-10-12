(function (root) {
  'use strict';
  const node = (tag, cls, text) => { const element=document.createElement(tag); if(cls) element.className=cls; if(text!==undefined) element.textContent=text; return element; };
  const button = (text, action) => { const element=node('button','secondary-button',text); element.type='button'; element.onclick=action; return element; };
  const states = new WeakMap();
  function dispose(mount) { const previous=states.get(mount); if(previous){previous.active=false;previous.chat?.dispose();} mount.replaceChildren(); }
  function begin(mount) { dispose(mount); const state={active:true}; states.set(mount,state); return state; }
  function download(result) {
    const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));
    const link=node('a'); link.href=url; link.download=`${result.context.report_id}-rider-case.json`; document.body.append(link); link.click(); link.remove(); setTimeout(()=>URL.revokeObjectURL(url),1500);
  }
  function show(mount, result, {saved=false, saveError='', chatError='', returnUrl='', saveReport=false, recovery}={}) {
    const state=begin(mount);
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
      if(result.review_required) panel.append(node('p','case-warning',result.review_reasons?.join(' ') || 'Possible safety concern: human review is needed. This demo has not contacted support or emergency services.'));
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
    const communication=node('section'); panel.append(communication);
    const foot=node('p','case-foot'); foot.textContent=saveError?`Prepared in this page, but session save failed: ${saveError} Download the case to keep a copy.`:saved?'Saved with this report in this browser tab’s session. Media bytes are not included.':'Prepared in page memory. Download to keep a copy; closing this page clears this copy.';foot.setAttribute('role','status');panel.append(foot);
    panel.append(node('p','case-foot','Predefined rules, simulated records and draft policies. No live AI, Driver Submission, Judge Ruling, or refund processing.'));
    const actions=node('div','case-actions');
    const exportError=node('p','case-foot');exportError.setAttribute('role','alert');
    const exportCase=button('Download Rider case JSON',async()=>{
      exportCase.disabled=true;exportError.textContent='';
      try {const log=await state.chat.readForExport();if(state.active)download({...result,communication_log:log});}
      catch(error){if(state.active)exportError.textContent=error.message;}
      finally {if(state.active)exportCase.disabled=!state.unlocked;}
    });
    actions.append(exportCase);
    if(returnUrl&&saved){const link=node('a','case-link','View in the Rider app →');link.href=returnUrl;actions.append(link);} panel.append(actions,exportError); mount.append(panel);
    state.chat=root.AgentChat.mount(communication,result.transcript_handle,{context:result.context,caseLabel:`${result.context.trip_id} · ${result.context.report_id}`,
      onRecover:recovery || (()=>prepare(mount,{riderId:result.context.rider_id,tripId:result.context.trip_id,report:result.original_report,returnUrl,saveReport})),
      onAccessChange:unlocked=>{state.unlocked=unlocked;if(unlocked)exportError.textContent='';exportCase.disabled=!unlocked;exportCase.title=unlocked?'':'Unlock the Communication Log to download the case, which includes recorded activity.';}});
    if(chatError)state.chat.clear(chatError);
  }
  async function prepare(mount,{riderId,tripId,report,returnUrl='',saveReport=false}) {
    const state=begin(mount);mount.append(node('p','notice','Preparing your Rider case and storing its Communication Log with the local backend…'));
    let saved=false,saveError='',chatError='';
    try {
      if(saveReport){try{root.RiderReportStore.save(riderId,tripId,report);}catch(error){saveError=error.message;}}
      const result=await root.RiderApi.prepareCase({riderId,report});
      if(!state.active)return;
      try{await root.AgentChat.prepare(result);}catch(error){chatError=error.message;}
      if(!state.active)return;
      try{root.RiderCaseStore.save(riderId,tripId,report,result);saved=!saveError;}catch(error){saveError=error.message;}
      show(mount,result,{saved,saveError,chatError,returnUrl,saveReport});
    }catch(error){if(state.active)mount.replaceChildren(node('p','notice error',`Rider case unavailable: ${error.message} Your original report is preserved.${saveError?` Report session save failed: ${saveError}. Use the report JSON download.`:saveReport?' Check the saved report or use the report JSON download.':''}`),button('Retry Rider case',()=>prepare(mount,{riderId,tripId,report,returnUrl,saveReport})));}
  }
  async function migrate(mount, {riderId,tripId,report}, original, expected=original) {
    const state=begin(mount), result=JSON.parse(JSON.stringify(original));
    mount.append(node('p','notice','Moving this older case’s recorded Communication Log to the local backend…'));
    let saveError='',chatError='',registered=!!result.transcript_handle && !result.communication_log?.length && !result.evidence?.log?.length;
    if(!registered)try { await root.AgentChat.prepare(result); registered=true; } catch(error) {chatError=error.message;}
    if(registered) {
      // A completed migration may persist after navigation, but never replace a different report/case.
      try {
        const current=root.RiderCaseStore.read(riderId,tripId,report);
        if(JSON.stringify(current)===JSON.stringify(expected))root.RiderCaseStore.save(riderId,tripId,report,result);
        else if(state.active)saveError='The saved case changed while its Communication Log was being registered. Reopen the current report.';
      }catch(error){saveError=error.message;}
    }
    if(state.active)show(mount,result,{saved:registered&&!saveError,saveError,chatError,
      recovery:()=>migrate(mount,{riderId,tripId,report},registered?result:original,expected)});
  }
  async function load(mount, {riderId,tripId,report}) {
    const state=begin(mount);
    if(!report){mount.append(node('p','notice','Create a Rider report for this trip to prepare your case. You can start from “Report an issue” in Overview.'));return;}
    try {
      const result=root.RiderCaseStore.read(riderId,tripId,report);
      if(result){
        // Migrate recorded activity once; never rerun agents while opening an older case.
        if(result.communication_log?.length || result.evidence?.log?.length){
          await migrate(mount,{riderId,tripId,report},result);return;
        }
        if(state.active)show(mount,result,{saved:true});return;
      }
    }
    catch(error){mount.append(node('p','notice',`The previous case cannot be used: ${error.message}`));}
    mount.append(node('p','notice','A Rider report is saved for this trip. Prepare a local case using its evidence and policies.'),button('Prepare Rider case',()=>prepare(mount,{riderId,tripId,report})));
  }
  root.RiderCasePanel=Object.freeze({show,load,prepare,dispose});
})(window);
