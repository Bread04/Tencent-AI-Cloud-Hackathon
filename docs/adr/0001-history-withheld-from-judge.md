# History is withheld from the Judge until the outcome is decided

The Judge rules without seeing a party's History (prior disputes, ratings, account age). Only after the outcome is fixed does a rule table in code apply History, and it may only lower Confidence or add a Review Trigger; it cannot raise Confidence or change the outcome. We chose this so that "History never decides a Ruling" is true by construction: a rider with a poor record must still win when the evidence supports them, and that has to be demonstrable, not a promise in a prompt.

## Considered Options

- **Give the Judge History as labelled context and rely on a self-check to catch misuse.** Simpler, one step fewer, and closer to how a human agent works. Rejected because a model that has read "3 of 4 prior disputes rejected" cannot be shown to have ignored it, and the sample dataset itself over-reads a rider's profile.
- **Drop History entirely.** Rejected because the challenge brief lists historical behaviour profiles as an evidence source, and a pattern of repeated identical claims is a fair reason for a human to take a second look.

## Consequences

- The Judge's prompt and inputs must never include History, including indirectly through an advocate's Submission. Advocates therefore do not receive History either.
- History rules are plain, published and listed in the Ruling with each adjustment, so they can be audited.
- If a Fraud and Bad-Faith Detection Agent is ever added, it belongs in the same post-outcome step, not in front of the Judge.
