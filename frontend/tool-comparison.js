(function (root) {
  function renderToolComparison(tools, language) {
    const { labels, element, link, setupContext, renderSetupScope } = root.ToolGuideDecisionUI;
    const t = labels(language);
    const section = element('section', null, 'comparison-section');
    section.append(element('h3', t.comparison));
    if (!tools.length) { section.append(element('p', t.noMatch)); return section; }
    const scroll = element('div', null, 'comparison-scroll');
    scroll.tabIndex = 0; scroll.setAttribute('role', 'region'); scroll.setAttribute('aria-label', t.comparison);
    const table = element('table', null, 'comparison-table');
    const head = element('thead'), header = element('tr');
    header.append(element('th', t.feature));
    for (const tool of tools) {
      const { setup, scoped } = setupContext(tool);
      const th = element('th', tool.name); th.scope = 'col';
      if (scoped) th.append(element('p', setup?.name || t.unknown));
      header.append(th);
    }
    head.append(header); table.append(head);
    const body = element('tbody');
    const fields = ['setupScope', 'offline', 'free_plan', 'open_source', 'deployment', 'pricing_summary', 'learning_curve', 'integrations', 'limitations', 'reviewed', 'sources'];
    for (const key of fields) {
      const row = element('tr'); const heading = element('th', t[key]); heading.scope = 'row'; row.append(heading);
      for (const tool of tools) {
        const cell = element('td'), profile = tool.profile;
        const { setup, scoped } = setupContext(tool);
        if (key === 'setupScope') {
          cell.append(renderSetupScope(setup, language));
        } else if (scoped && !setup) {
          cell.textContent = t.unknown;
        } else if (['offline', 'free_plan', 'open_source'].includes(key)) {
          const evidence = scoped ? setup?.[key] : profile?.[key];
          cell.append(element('span', evidence?.value === true ? t.yes : evidence?.value === false ? t.no : t.unknown));
          if (evidence?.source_url) cell.append(link(evidence.source_url, t.source));
          if (evidence?.reviewed_at) cell.append(element('small', `${t.reviewed}: ${evidence.reviewed_at}`));
        } else if (key === 'sources') {
          const sources = scoped ? [...new Set((setup.evidence || []).map(item => item.source_url).filter(Boolean))] : profile?.sources || [];
          for (const [index, url] of sources.entries()) cell.append(link(url, `${t.source} ${index + 1}`));
          if (!sources.length) cell.textContent = t.unknown;
        } else if (key === 'limitations' || key === 'integrations') {
          const items = scoped ? (key === 'limitations' ? (setup.evidence || []).map(item => item.limitations).filter(Boolean) : []) : key === 'limitations' ? tool.limitations : profile?.integrations;
          if (items?.length) { const list = element('ul'); items.forEach(value => list.append(element('li', value))); cell.append(list); }
          else cell.textContent = t.unknown;
        } else if (scoped) {
          cell.textContent = key === 'deployment' ? setup.platform || t.unknown : key === 'reviewed' ? [...new Set((setup.evidence || []).map(item => item.reviewed_at).filter(Boolean))].join(' · ') || t.unknown : t.unknown;
        } else cell.textContent = (key === 'reviewed' ? profile?.reviewed_at : profile?.[key]) || t.unknown;
        row.append(cell);
      }
      body.append(row);
    }
    table.append(body); scroll.append(table); section.append(scroll);
    return section;
  }
  root.ToolGuideComparison = { renderToolComparison };
}(typeof globalThis !== 'undefined' ? globalThis : this));
