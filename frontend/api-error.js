(function exposeApiErrorHelpers(globalScope) {
  function responseErrorMessage(payload, fallback) {
    return payload?.error?.message || payload?.detail || fallback;
  }

  const helpers = { responseErrorMessage };
  globalScope.ToolGuideApiErrors = helpers;

  if (typeof module === 'object' && module.exports) {
    module.exports = helpers;
  }
})(globalThis);
