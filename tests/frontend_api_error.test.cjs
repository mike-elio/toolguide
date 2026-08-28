const assert = require('node:assert/strict');
const test = require('node:test');

const { responseErrorMessage } = require('../frontend/api-error.js');

test('uses the message from the API error envelope', () => {
  const payload = {
    error: {
      code: 'UNCERTAIN_TEXT_INTENT',
      message: 'Please reword the design description.',
      details: null,
    },
  };

  assert.equal(
    responseErrorMessage(payload, 'The data could not be loaded.'),
    'Please reword the design description.',
  );
});

test('supports FastAPI detail errors and malformed responses', () => {
  assert.equal(
    responseErrorMessage({ detail: 'Stage not found' }, 'Fallback'),
    'Stage not found',
  );
  assert.equal(responseErrorMessage(null, 'Fallback'), 'Fallback');
});
