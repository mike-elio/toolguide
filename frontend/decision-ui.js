(function (root) {
  const copy = {
    en: {
      requirements: 'Must-have requirements', requirementsHelp: 'Optional requirements exclude tools. Your questionnaire answers express preferences and affect ranking. Unverified capabilities do not satisfy a requirement.',
      requires_offline: 'Must work without internet', requires_free_plan: 'Must have a documented free plan', requires_open_source: 'Must be open source', allows_online_preparation: 'Files may be downloaded and prepared before going offline',
      preparationHelp: 'This changes only preparation. The selected task must still run without a network connection.',
      freeHelp: 'A free plan may have usage limits. It does not guarantee that every workflow is free.',
      continue: 'Continue to questions', compare: 'Compare tools', comparison: 'Your tools, side by side',
      feature: 'Feature', offline: 'Works offline', free_plan: 'Free plan', open_source: 'Open source',
      deployment: 'Where it runs', pricing_summary: 'Cost and limits', learning_curve: 'Learning curve · editorial estimate',
      integrations: 'Integrations', limitations: 'Limitations', sources: 'Sources', reviewed: 'Reviewed',
      yes: 'Yes', no: 'No', unknown: 'Not documented', source: 'Source',
      setupScope: 'Selected setup and task', setupMissing: 'Selected setup is not documented. Product-wide details cannot verify this task.',
      scopeHelp: 'These capabilities apply only to the selected setup and task.',
      platform: 'Platform', version: 'Version', local_components: 'Local components', model: 'Model',
      preparation_network: 'Network during preparation', runtime_network: 'Network during the task',
      download_requirements: 'Downloads before use', offline_features: 'Available offline', online_only_features: 'Requires online access',
      required: 'Required', not_required: 'Not required', optional: 'Optional', version_scope: 'Evidence scope', allowed: 'Allowed', notAllowed: 'Not allowed',
      guide: 'Start with this tool', unavailable: 'Guide unavailable', prerequisites: 'Before you start',
      steps: 'First steps', example: 'Try this example', expected: 'Expected outcome',
      noMatch: 'No documented tool meets all requirements', noMatchHelp: 'Some tools conflict with your requirements; others lack enough evidence. Change a requirement explicitly to explore alternatives.',
      closestAlternatives: 'Closest documented alternatives', changeRequired: 'Change required', unknownCoverage: 'tools need more evidence',
      task_scope: 'Task, stage and domain coverage', hardware: 'Device requirements',
      official_documentation: 'Officially documented', independent_test: 'Tested in a specific environment', conflicting: 'Conflicting evidence',
      excluded: 'Why other tools were excluded', failed: 'Does not meet', undocumented: 'Not verified',
      scoring: 'Rank uses weighted preference scores. Match is a separate fit indicator, not a probability, so percentages may not follow rank order.',
      lowConfidence: 'With fewer than four eligible tools, confidence stays low because comparison evidence is limited.',
      whatIf: 'What if?', scenarioTitle: 'Explore a different decision', scenarioHelp: 'Change requirements or previous answers. Preview uses the same questions and knowledge as your original session. Your original stays unchanged until you adopt the scenario.',
      previousAnswers: 'Previous answers', preview: 'Preview changes', adopt: 'Adopt scenario', cancel: 'Cancel',
      original: 'Original', variant: 'Scenario', changes: 'What changed', rank: 'Rank', match: 'Match', absent: 'Outside results',
      needsMore: 'This scenario needs another answer. Adopt it to continue the questionnaire.',
      clarification: 'The revised answer needs clarification. Adopt the scenario to choose an intent.',
      loading: 'Loading…', retry: 'Try again', loadError: 'Could not load the details. Your results are still here.',
      noChanges: 'No ranking or match changes.', changedRequirements: 'Requirements changed', changedAnswers: 'Answers changed',
      reasonHelp: 'Ranking changes reflect the edited answers and requirements. Read the scenario reasons below for supporting rule evidence.',
      enabled: 'Required', disabled: 'Optional', refresh: 'Re-evaluate original', stale: 'Knowledge has changed. Re-evaluate the original before comparing.',
      edit: 'Change requirements', count: 'eligible tools', selectAnswer: 'Choose an answer',
    },
    ar: {
      requirements: 'الشروط الإلزامية', requirementsHelp: 'شروط اختيارية تستبعد الأدوات غير المتوافقة. إجابات الاستبيان تعبّر عن تفضيلات تؤثر في الترتيب. القدرة غير الموثقة لا تحقق شرطاً إلزامياً.',
      requires_offline: 'يجب أن تعمل دون إنترنت', requires_free_plan: 'يجب أن تتوفر خطة مجانية موثقة', requires_open_source: 'يجب أن تكون مفتوحة المصدر', allows_online_preparation: 'يمكن تنزيل الملفات وتجهيزها قبل قطع الإنترنت',
      preparationHelp: 'هذا السماح يخص التجهيز فقط؛ يجب أن تبقى المهمة المختارة قابلة للتنفيذ بلا شبكة.',
      freeHelp: 'قد تكون الخطة المجانية محدودة الاستخدام، ولا تضمن إنجاز كل المهام مجاناً.',
      continue: 'المتابعة إلى الأسئلة', compare: 'مقارنة الأدوات', comparison: 'أدواتك جنباً إلى جنب',
      feature: 'الخاصية', offline: 'تعمل دون إنترنت', free_plan: 'خطة مجانية', open_source: 'مفتوحة المصدر',
      deployment: 'بيئة التشغيل', pricing_summary: 'التكلفة والحدود', learning_curve: 'سهولة التعلم · تقدير تحريري',
      integrations: 'التكاملات', limitations: 'القيود', sources: 'المصادر', reviewed: 'تاريخ المراجعة',
      yes: 'نعم', no: 'لا', unknown: 'غير موثّق', source: 'المصدر',
      setupScope: 'الإعداد والمهمة المختاران', setupMissing: 'الإعداد المختار غير موثق. معلومات المنتج العامة لا تثبت ملاءمته لهذه المهمة.',
      scopeHelp: 'تنطبق هذه القدرات على الإعداد والمهمة المختارين فقط.',
      platform: 'المنصة', version: 'الإصدار', local_components: 'المكونات المحلية', model: 'النموذج',
      preparation_network: 'الشبكة أثناء التجهيز', runtime_network: 'الشبكة أثناء المهمة',
      download_requirements: 'التنزيلات قبل الاستخدام', offline_features: 'الميزات المتاحة دون شبكة', online_only_features: 'الميزات التي تتطلب الاتصال',
      required: 'مطلوب', not_required: 'غير مطلوب', optional: 'اختياري', version_scope: 'نطاق الدليل', allowed: 'مسموح', notAllowed: 'غير مسموح',
      guide: 'ابدأ بهذه الأداة', unavailable: 'الدليل غير متاح', prerequisites: 'قبل أن تبدأ',
      steps: 'الخطوات الأولى', example: 'جرّب هذا المثال', expected: 'النتيجة المتوقعة',
      noMatch: 'لا توجد أداة موثقة تستوفي كل الشروط', noMatchHelp: 'بعض الأدوات تخالف شروطك، وأخرى تفتقر للدليل الكافي. عدّل شرطاً بشكل صريح لاستكشاف البدائل.',
      closestAlternatives: 'أقرب البدائل الموثقة', changeRequired: 'التغيير المطلوب', unknownCoverage: 'أدوات تحتاج أدلة إضافية',
      task_scope: 'تغطية المهمة والمرحلة والمجال', hardware: 'متطلبات الجهاز',
      official_documentation: 'موثق رسمياً', independent_test: 'مختبر في بيئة محددة', conflicting: 'أدلة متعارضة',
      excluded: 'لماذا استُبعدت الأدوات الأخرى؟', failed: 'لا تحقق', undocumented: 'لم يُوثّق',
      scoring: 'يعتمد الترتيب على درجات التفضيلات الموزونة. نسبة المطابقة مؤشر منفصل وليست احتمالاً، لذلك قد لا تتبع النسب ترتيب الأدوات.',
      lowConfidence: 'عند وجود أقل من أربع أدوات مؤهلة تبقى الثقة منخفضة بسبب محدودية المقارنة.',
      whatIf: 'ماذا لو؟', scenarioTitle: 'استكشف قراراً مختلفاً', scenarioHelp: 'غيّر شرطاً أو إجابة سابقة. تستخدم المعاينة نفس الأسئلة والمعرفة في جلستك الأصلية. تبقى النتيجة الأصلية كما هي حتى تعتمد السيناريو.',
      previousAnswers: 'الإجابات السابقة', preview: 'معاينة التغييرات', adopt: 'اعتماد السيناريو', cancel: 'إلغاء',
      original: 'الأصل', variant: 'السيناريو', changes: 'ما الذي تغيّر؟', rank: 'الترتيب', match: 'المطابقة', absent: 'خارج النتائج',
      needsMore: 'يحتاج السيناريو إجابة إضافية. اعتمده لاستكمال الاستبيان.',
      clarification: 'تحتاج الإجابة المعدّلة إلى توضيح. اعتمد السيناريو لاختيار القصد المناسب.',
      loading: 'جارِ التحميل…', retry: 'إعادة المحاولة', loadError: 'تعذر تحميل التفاصيل. نتائجك ما زالت موجودة.',
      noChanges: 'لم يتغير الترتيب أو مؤشر المطابقة.', changedRequirements: 'الشروط المعدّلة', changedAnswers: 'الإجابات المعدّلة',
      reasonHelp: 'تعكس تغييرات الترتيب الإجابات والشروط المعدّلة. اقرأ أسباب السيناريو أدناه للاطلاع على الأدلة الداعمة من القواعد.',
      enabled: 'إلزامي', disabled: 'اختياري', refresh: 'إعادة تقييم الأصل', stale: 'تغيّرت قاعدة المعرفة. أعد تقييم الأصل قبل المقارنة.',
      edit: 'تعديل الشروط', count: 'أدوات مؤهلة', selectAnswer: 'اختر إجابة',
    },
  };
  function labels(language) { return copy[language] || copy.en; }
  function element(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined && text !== null) node.textContent = text;
    if (className) node.className = className;
    return node;
  }
  function link(url, title) {
    const node = element('a', title, 'evidence-link');
    try {
      const parsed = new URL(url);
      if (!['http:', 'https:'].includes(parsed.protocol)) return element('span', title);
      node.href = parsed.href;
    } catch { return element('span', title); }
    node.target = '_blank'; node.rel = 'noopener noreferrer';
    return node;
  }
  const requirementKeys = ['requires_offline', 'requires_free_plan', 'requires_open_source', 'allows_online_preparation'];
  function constraintsEditor(values, language, onChange) {
    const t = labels(language);
    const fieldset = element('fieldset', null, 'requirements');
    fieldset.append(element('legend', t.requirements), element('p', t.requirementsHelp, 'support-copy'));
    let offlineInput;
    for (const key of requirementKeys.slice(0, 3)) {
      const label = element('label', null, 'answer-choice');
      const input = element('input'); input.type = 'checkbox'; input.name = key;
      input.checked = Boolean(values?.[key]);
      if (key === 'requires_offline') offlineInput = input;
      input.addEventListener('change', () => {
        syncPreparation();
        onChange?.(readConstraints(fieldset));
      });
      label.append(input, element('span', t[key])); fieldset.append(label);
    }
    const preparation = element('div', null, 'preparation-requirement');
    const preparationLabel = element('label', null, 'answer-choice');
    const preparationInput = element('input');
    preparationInput.type = 'checkbox'; preparationInput.name = 'allows_online_preparation';
    preparationInput.checked = Boolean(values?.allows_online_preparation);
    preparationInput.addEventListener('change', () => onChange?.(readConstraints(fieldset)));
    preparationLabel.append(preparationInput, element('span', t.allows_online_preparation));
    preparation.append(preparationLabel, element('p', t.preparationHelp, 'support-copy'));
    fieldset.append(preparation);
    function syncPreparation() {
      const visible = Boolean(offlineInput?.checked);
      preparation.hidden = !visible;
      preparationInput.disabled = !visible;
      if (!visible) preparationInput.checked = false;
    }
    syncPreparation();
    fieldset.append(element('p', t.freeHelp, 'support-copy'));
    return fieldset;
  }
  function readConstraints(container) {
    return Object.fromEntries(requirementKeys.map(key => [key, Boolean(container.querySelector(`[name="${key}"]`)?.checked)]));
  }
  function setupContext(tool) {
    const setups = tool.profile?.operation_setups || [];
    return { scoped: Boolean(tool.matching_setup_id || setups.length),
      setup: setups.find(item => item.id === tool.matching_setup_id) };
  }
  function renderSetupScope(setup, language) {
    const t = labels(language), section = element('div', null, 'setup-scope');
    section.dir = language === 'ar' ? 'rtl' : 'ltr';
    if (!setup) { section.append(element('p', t.setupMissing)); return section; }
    section.append(element('p', t.scopeHelp), element('p', setup.task));
    const list = element('dl');
    for (const key of ['platform', 'version', 'local_components', 'model', 'preparation_network', 'runtime_network', 'download_requirements', 'offline_features', 'online_only_features']) {
      const value = setup[key];
      const text = Array.isArray(value) ? (value.join(' · ') || t.unknown) : key.endsWith('_network') ? (t[value] || t.unknown) : (value || t.unknown);
      const description = element('dd', text); description.dir = 'auto';
      list.append(element('dt', t[key]), description);
    }
    section.append(list); return section;
  }
  root.ToolGuideDecisionUI = { labels, element, link, constraintsEditor, readConstraints, requirementKeys, setupContext, renderSetupScope };
}(typeof globalThis !== 'undefined' ? globalThis : this));
