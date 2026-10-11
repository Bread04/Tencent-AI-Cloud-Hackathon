// Ports the shared policy set (Kyven's prototypes/shared/policies.js) into data/policy/ for the Python backend.
// Run after changing policies.js:  node scripts/sync_policy.cjs
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const policy = require(path.join(root, 'prototypes', 'shared', 'policies.js'));
const out = {
  _simulated: "Ported unchanged from prototypes/shared/policies.js. Draft prototype guidance, not Ryde's approved terms. Re-sync with: node scripts/sync_policy.cjs",
  version: policy.version,
  status: policy.status,
  clauses: policy.clauses.map((c) => ({ clause_id: c.id, role: c.role, category: c.category, title: c.title, text: c.text, keywords: c.keywords })),
};
const target = path.join(root, 'data', 'policy', `${policy.version}.json`);
fs.writeFileSync(target, JSON.stringify(out, null, 2) + '\n');
console.log(`${out.clauses.length} clauses, version ${out.version} -> ${path.relative(root, target)}`);
