(function (root) {
  function renderStarterGuide(tool, language) {
    const { labels, element, link, setupContext, renderSetupScope } = root.ToolGuideDecisionUI;
    const { setup, scoped } = setupContext(tool);
    const t = labels(language), guide = scoped ? setup?.starter_guide : tool.profile?.starter_guide;
    const details = element('details', null, 'starter-guide');
    const summary = element('summary', t.guide); summary.setAttribute('aria-expanded', 'false');
    details.addEventListener('toggle', () => summary.setAttribute('aria-expanded', String(details.open)));
    details.append(summary);
    if (scoped && !setup) { details.append(renderSetupScope(null, language)); return details; }
    if (!guide) { details.append(element('p', t.unavailable)); return details; }
    details.append(element('h4', setup ? `${tool.name} — ${setup.name}` : tool.name));
    if (setup) {
      details.append(renderSetupScope(setup, language));
      details.append(element('p', t[setup.evidence_status] || t.unknown));
      details.append(element('p', `${t.hardware}: ${setup.hardware_requirements || t.unknown}`));
      for (const evidence of setup.evidence || []) {
        details.append(element('p', evidence.summary));
        details.append(element('p', `${t.version_scope}: ${evidence.version_scope || t.unknown}`));
        details.append(element('p', `${t.limitations}: ${evidence.limitations || t.unknown}`));
        if (evidence.source_url) details.append(link(evidence.source_url, t.source));
        if (evidence.reviewed_at) details.append(element('small', `${t.reviewed}: ${evidence.reviewed_at}`));
      }
    }
    details.append(element('h5', t.prerequisites));
    const prerequisites = element('ul');
    guide.prerequisites.forEach(value => prerequisites.append(element('li', value)));
    details.append(prerequisites, element('h5', t.steps));
    const steps = element('ol');
    for (const step of guide.steps) {
      const li = element('li', step.instruction);
      li.append(link(step.source_url, t.source)); steps.append(li);
    }
    details.append(steps, element('h5', t.example), element('p', guide.example, 'guide-example'),
      element('h5', t.expected), element('p', guide.expected_outcome),
      element('small', `${t.reviewed}: ${guide.reviewed_at}`));
    return details;
  }
  root.ToolGuideStarter = { renderStarterGuide };
}(typeof globalThis !== 'undefined' ? globalThis : this));
