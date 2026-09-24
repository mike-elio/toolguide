(function (root) {
  function createScenarioPanel({ baseline, version, questions, language, request, onAdopt, onCancel, onRefresh, changedConstraints = [] }) {
    const ui = root.ToolGuideDecisionUI, t = ui.labels(language), el = ui.element;
    const scenario = root.ToolGuideScenarios.createScenarioState(baseline, version);
    for (const key of changedConstraints) {
      if (ui.requirementKeys.includes(key)) scenario.variant.constraints[key] = key === 'allows_online_preparation';
    }
    const panel = el('section', null, 'scenario-panel'); panel.setAttribute('aria-label', t.scenarioTitle);
    const heading = el('h3', t.scenarioTitle); heading.tabIndex = -1;
    panel.append(heading, el('p', t.scenarioHelp, 'support-copy'));
    const form = el('form');
    const result = el('div', null, 'scenario-result'); result.setAttribute('aria-live', 'polite');
    const preview = el('button', t.preview, 'button button-primary'); preview.type = 'submit';
    const adopt = el('button', t.adopt, 'button button-primary'); adopt.type = 'button'; adopt.disabled = true;
    const cancel = el('button', t.cancel, 'button button-secondary'); cancel.type = 'button';
    function invalidate() { scenario.invalidate(); adopt.disabled = true; result.replaceChildren(); }
    form.append(ui.constraintsEditor(scenario.variant.constraints, language, values => {
      scenario.variant.constraints = values; invalidate();
    }));
    if (baseline.answers.length) form.append(el('h4', t.previousAnswers));
    const editors = [];
    baseline.answers.forEach((answer, index) => {
      const question = questions[answer.question_id];
      if (!question) return;
      const group = el('fieldset', null, 'scenario-answer'); group.append(el('legend', question.prompt));
      if (question.type === 'short_text' && answer.text !== undefined) {
        const input = el('textarea'); input.value = answer.text; input.maxLength = 500; input.required = true;
        input.className = 'text-answer'; input.setAttribute('aria-label', question.prompt); group.append(input);
        editors.push(() => { scenario.variant.answers[index] = { question_id: question.id, text: input.value.trim() }; });
      } else {
        for (const option of question.options || []) {
          const label = el('label', null, 'answer-choice'), input = el('input');
          input.type = question.type === 'multiple_choice' ? 'checkbox' : 'radio';
          input.name = `scenario-${index}`; input.value = option.id;
          input.checked = answer.option_ids?.includes(option.id) || false;
          label.append(input, el('span', option.label)); group.append(label);
        }
        editors.push(() => {
          const selected = [...group.querySelectorAll('input:checked')].map(input => input.value);
          if (!selected.length) throw new Error(t.selectAnswer);
          scenario.variant.answers[index] = { question_id: answer.question_id, option_ids: selected };
        });
      }
      group.addEventListener('input', invalidate); form.append(group);
    });
    const actions = el('div', null, 'support-actions'); actions.append(preview, cancel); form.append(actions);
    panel.append(form, result, adopt);
    cancel.addEventListener('click', () => { scenario.invalidate(); onCancel(); });
    adopt.addEventListener('click', () => { if (scenario.result) onAdopt(scenario.variant, scenario.result.variant); });

    function summary(outcome, title) {
      const card = el('article', null, 'scenario-summary'); card.append(el('h4', title));
      if (outcome.status === 'no_match') card.append(el('p', t.noMatch));
      if (outcome.status === 'question') card.append(el('p', t.needsMore));
      if (outcome.status === 'clarification') card.append(el('p', t.clarification));
      for (const [index, tool] of (outcome.recommendations || []).entries()) {
        card.append(el('h5', `${index + 1}. ${tool.tool_name} · ${tool.match_percent}%`));
        const reasons = el('ul'); tool.reasons.forEach(reason => reasons.append(el('li', reason))); card.append(reasons);
      }
      for (const tool of outcome.excluded_tools || []) {
        const reasons = [...tool.failed_constraints.map(key => `${t.failed}: ${t[key]}`),
          ...tool.unknown_constraints.map(key => `${t.undocumented}: ${t[key]}`)];
        card.append(el('p', `${tool.tool_name || tool.tool_id}: ${reasons.join(' · ')}`));
      }
      return card;
    }
    function render(outcomes) {
      result.replaceChildren();
      const edits = el('div', null, 'scenario-edits');
      for (const key of ui.requirementKeys) {
        if (Boolean(scenario.baseline.constraints?.[key]) !== Boolean(scenario.variant.constraints?.[key])) {
          const valueLabel = key === 'allows_online_preparation'
            ? (scenario.variant.constraints[key] ? t.allowed : t.notAllowed)
            : (scenario.variant.constraints[key] ? t.enabled : t.disabled);
          edits.append(el('p', `${t.changedRequirements} — ${t[key]}: ${valueLabel}`));
        }
      }
      scenario.variant.answers.forEach((answer, index) => {
        if (JSON.stringify(answer) !== JSON.stringify(scenario.baseline.answers[index])) {
          edits.append(el('p', `${t.changedAnswers} — ${questions[answer.question_id]?.prompt || answer.question_id}`));
        }
      });
      result.append(el('h4', t.changes), edits, el('p', t.reasonHelp, 'support-copy'));
      const pairs = el('div', null, 'scenario-summaries');
      pairs.append(summary(outcomes.baseline, t.original), summary(outcomes.variant, t.variant)); result.append(pairs);
      const names = Object.fromEntries([...(outcomes.baseline.recommendations || []), ...(outcomes.variant.recommendations || [])].map(tool => [tool.tool_id, tool.tool_name]));
      const changed = outcomes.changes.filter(change => change.before_rank !== change.after_rank || change.before_match !== change.after_match);
      const list = el('ul');
      changed.forEach(change => list.append(el('li', `${names[change.tool_id] || change.tool_id} — ${t.rank}: ${change.before_rank ?? t.absent} → ${change.after_rank ?? t.absent}; ${t.match}: ${change.before_match ?? '—'} → ${change.after_match ?? '—'}`)));
      result.append(list);
      if (!changed.length && ['complete', 'no_match'].includes(outcomes.baseline.status) && ['complete', 'no_match'].includes(outcomes.variant.status)) result.append(el('p', t.noChanges));
    }
    form.addEventListener('submit', async event => {
      event.preventDefault();
      try { editors.forEach(read => read()); } catch (error) { result.replaceChildren(el('p', error.message)); return; }
      const revision = scenario.beginPreview(); adopt.disabled = true; result.replaceChildren(el('p', t.loading));
      try {
        const outcomes = await request('/questionnaire/compare', { method: 'POST', body: JSON.stringify({
          baseline: scenario.baseline, variant: scenario.variant, knowledge_version: scenario.version,
        }) });
        if (!scenario.receive(revision, outcomes)) return;
        render(outcomes); adopt.disabled = false;
      } catch (error) {
        if (!scenario.receive(revision, null)) return;
        const stale = error.code === 'KNOWLEDGE_VERSION_MISMATCH';
        result.replaceChildren(el('p', stale ? t.stale : t.loadError));
        if (stale) {
          const refresh = el('button', t.refresh, 'button button-secondary'); refresh.type = 'button';
          refresh.addEventListener('click', onRefresh); result.append(refresh);
        }
      }
    });
    return { element: panel, focus: () => heading.focus(), dispose: () => scenario.invalidate() };
  }
  root.ToolGuideScenarioPanel = { createScenarioPanel };
}(typeof globalThis !== 'undefined' ? globalThis : this));
