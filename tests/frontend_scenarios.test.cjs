const test = require('node:test');
const assert = require('node:assert/strict');

test('scenario state isolates previews, rejects stale responses, and cancels', () => {
  const { createScenarioState } = require('../frontend/scenario-state.js');
  const original = { answers: [{ question_id: 'q', option_ids: ['a'] }], constraints: {} };
  const scenario = createScenarioState(original, 'version');
  scenario.variant.answers[0].option_ids = ['b'];
  assert.deepEqual(original.answers[0].option_ids, ['a']);
  const first = scenario.beginPreview();
  const second = scenario.beginPreview();
  assert.equal(scenario.receive(first, { variant: { status: 'complete' } }), false);
  assert.equal(scenario.receive(second, { variant: { status: 'question' } }), true);
  assert.equal(scenario.result.variant.status, 'question');
  scenario.invalidate();
  assert.equal(scenario.result, null);
  assert.equal(scenario.receive(second, {}), false);
  assert.deepEqual(scenario.baseline, original);
});
