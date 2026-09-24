(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.ToolGuideScenarios = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const clone = value => JSON.parse(JSON.stringify(value));
  function createScenarioState(baseline, version) {
    let revision = 0;
    return {
      baseline: clone(baseline), variant: clone(baseline), version, result: null,
      beginPreview() { this.result = null; return ++revision; },
      receive(requestRevision, result) {
        if (requestRevision !== revision) return false;
        this.result = clone(result);
        return true;
      },
      invalidate() { ++revision; this.result = null; },
    };
  }
  return { createScenarioState };
}));
