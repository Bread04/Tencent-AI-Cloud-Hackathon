---
title: 'Document the Rider Policy Agent'
type: 'chore'
created: '2026-10-11'
status: 'done'
route: 'one-shot'
---

# Document the Rider Policy Agent

## Intent

**Problem:** The app has shared draft Rider policies and a browser matcher, but no adjacent agent document defining report-specific extraction and the Rider Advocate handoff.

**Approach:** Add `rider-policy-agent.md` beside the existing Rider Advocate and Evidence Agent documents. Specify exact-source retrieval, report/version binding, full relevance coverage, limitations, shared-store handoffs, failure handling, and acceptance criteria. Distinguish implemented matcher behaviour from proposed integration. The user confirmed Markdown only; app code remains unchanged.

## Suggested Review Order

- Start with the agent's role and shared policy authority.
  [rider-policy-agent.md:9](../../src/agents/advocates/rider-policy-agent.md#L9)

- Check report validation and category-to-clause coverage.
  [rider-policy-agent.md:27](../../src/agents/advocates/rider-policy-agent.md#L27)

- Review complete extraction versus the current capped matcher and proposed adapter.
  [rider-policy-agent.md:73](../../src/agents/advocates/rider-policy-agent.md#L73)

- Check readiness, storage failures, and shared agent handoffs.
  [rider-policy-agent.md:105](../../src/agents/advocates/rider-policy-agent.md#L105)

- Finish with the sample and Given/When/Then acceptance criteria.
  [rider-policy-agent.md:157](../../src/agents/advocates/rider-policy-agent.md#L157)
