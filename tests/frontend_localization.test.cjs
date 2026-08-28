const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

function element() {
  return {
    className: '',
    innerHTML: '',
    style: {},
    textContent: '',
    classList: {
      add() {},
      remove() {},
      toggle() {},
    },
    addEventListener() {},
    setAttribute() {},
  };
}

test('initial language sets a visible results heading', async () => {
  const elements = new Map();
  const bySelector = selector => {
    if (!elements.has(selector)) elements.set(selector, element());
    return elements.get(selector);
  };
  const document = {
    documentElement: { lang: '', dir: '' },
    title: '',
    querySelector: bySelector,
    querySelectorAll: () => [],
  };
  const context = {
    CSS: { escape: value => value },
    ToolGuideApiErrors: { responseErrorMessage: () => 'error' },
    document,
    fetch: async () => ({ ok: true, json: async () => [] }),
    localStorage: {
      getItem: () => 'en',
      setItem() {},
    },
    window: {
      location: { port: '8000' },
      scrollTo() {},
    },
  };
  const stateScript = fs.readFileSync(
    path.join(__dirname, '..', 'frontend', 'questionnaire-state.js'),
    'utf8',
  );
  const script = fs.readFileSync(
    path.join(__dirname, '..', 'frontend', 'app.js'),
    'utf8',
  );

  vm.runInNewContext(stateScript, context);
  vm.runInNewContext(script, context);
  await new Promise(resolve => setImmediate(resolve));

  assert.equal(
    bySelector('#results-heading').textContent,
    'Best-fit recommendations',
  );
});
