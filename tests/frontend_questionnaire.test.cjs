const test = require('node:test');
const assert = require('node:assert/strict');

const { createQuestionnaireState } = require('../frontend/questionnaire-state.js');

test('selecting a stage and domain starts a fresh deterministic session', () => {
  const state = createQuestionnaireState(() => 'fixed-seed');

  state.selectStage('analysis');
  state.selectDomain('software');

  assert.equal(state.stage, 'analysis');
  assert.equal(state.domain, 'software');
  assert.equal(state.sessionSeed, 'fixed-seed');
  assert.deepEqual(state.askedQuestionIds, []);
  assert.deepEqual(state.answers, []);
});

test('answering one question appends aligned history without dropping it', () => {
  const state = createQuestionnaireState(() => 'fixed-seed');
  state.selectStage('analysis');
  state.selectDomain('software');

  state.recordAnswer({ question_id: 'q1', option_ids: ['a'] });
  state.recordAnswer({ question_id: 'q2', text: 'hard input' });

  assert.deepEqual(state.askedQuestionIds, ['q1', 'q2']);
  assert.deepEqual(state.answers, [
    { question_id: 'q1', option_ids: ['a'] },
    { question_id: 'q2', text: 'hard input' },
  ]);
});

test('clarification replaces the answer for the same question', () => {
  const state = createQuestionnaireState(() => 'fixed-seed');
  state.selectStage('analysis');
  state.selectDomain('software');
  state.recordAnswer({ question_id: 'q1', text: 'ambiguous input' });

  state.replaceAnswer({ question_id: 'q1', option_ids: ['intent-a'] });

  assert.deepEqual(state.askedQuestionIds, ['q1']);
  assert.deepEqual(state.answers, [
    { question_id: 'q1', option_ids: ['intent-a'] },
  ]);
});

test('the API payload is a defensive copy of the current history', () => {
  const state = createQuestionnaireState(() => 'fixed-seed');
  state.selectStage('testing');
  state.selectDomain('cybersecurity');
  state.recordAnswer({ question_id: 'q1', option_ids: ['api'] });

  const payload = state.toRequest('ar');
  payload.answers[0].option_ids.push('mutated');

  assert.deepEqual(state.answers[0].option_ids, ['api']);
  assert.equal(payload.language, 'ar');
  assert.equal(payload.stage, 'testing');
  assert.equal(payload.domain, 'cybersecurity');
});

test('restart clears the selected path and accumulated answers', () => {
  const state = createQuestionnaireState(() => 'fixed-seed');
  state.selectStage('design');
  state.selectDomain('artificial_intelligence');
  state.recordAnswer({ question_id: 'q1', option_ids: ['visual'] });

  state.restart();

  assert.equal(state.stage, null);
  assert.equal(state.domain, null);
  assert.equal(state.sessionSeed, null);
  assert.deepEqual(state.askedQuestionIds, []);
  assert.deepEqual(state.answers, []);
});
