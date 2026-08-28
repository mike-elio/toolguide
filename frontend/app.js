const state = {
  language: localStorage.getItem('tool-guide-language') === 'en' ? 'en' : 'ar',
  stages: [],
  domains: [],
  currentQuestion: null,
  currentStatus: null,
  questionnaire: ToolGuideQuestionnaireState.createQuestionnaireState(),
};

const apiBase = window.location.port === '8000'
  ? '/api'
  : 'http://127.0.0.1:8000/api';

const dictionary = {
  ar: {
    title: 'دليل الأدوات الذكية', eyebrow: 'مساعدك لاختيار الأداة المناسبة بالدليل', description: 'اختر مرحلة مشروعك ومجاله، ثم أجب عن أسئلة تتكيف مع إجاباتك. ستحصل على ثلاث توصيات واضحة ومفسرة.',
    progress: 'الخطوة {step} من 3', stage: 'الاختيار', questions: 'الأسئلة', results: 'النتائج',
    chooseStage: 'اختر مرحلة مشروعك', chooseDomain: 'اختر مجال المشروع', stageKicker: 'الخطوة الأولى', domainKicker: 'تخصيص المسار', questionsKicker: 'الخطوة الثانية', resultsKicker: 'الخطوة الثالثة', resultsHeading: 'التوصيات الأنسب',
    back: 'رجوع', next: 'السؤال التالي', restart: 'ابدأ من جديد',
    questionProgress: '{count} إجابات · من 6 إلى 10 أسئلة', chooseAnswer: 'اختر إجابة واحدة', chooseMany: 'يمكنك اختيار أكثر من إجابة', textAnswer: 'اكتب وصفاً واضحاً ومحدداً…', clarification: 'لم تتضح الفئة بدقة. اختر الأقرب إلى قصدك.',
    required: 'يرجى تقديم إجابة قبل المتابعة.', loading: 'جارِ التحميل…', loadingRecommendations: 'جارِ تحليل الإجابة واختيار السؤال التالي…',
    connectionError: 'تعذر الاتصال بالخادم. تأكد من تشغيله ثم حاول مرة أخرى.', serverError: 'تعذر تحميل البيانات. حاول مرة أخرى.',
    stageDescriptions: { analysis: 'فهم الحاجة وجمع الأدلة.', design: 'تصميم الواجهة وتجربة المستخدم.', implementation: 'بناء الحل وكتابة الكود.', testing: 'اختبار الجودة والتحقق منها.' },
    stageIcons: { analysis: '⌕', design: '✦', implementation: '⌘', testing: '✓' },
    domainDescriptions: { software: 'تطوير البرمجيات والمنتجات الرقمية.', artificial_intelligence: 'النماذج والوكلاء وتطبيقات الذكاء الاصطناعي.', cybersecurity: 'الحماية ونمذجة التهديدات واختبار الأمن.' },
    domainIcons: { software: '⌘', artificial_intelligence: '✦', cybersecurity: '◇' },
    confidence: 'الثقة', confidenceLevels: { high: 'عالية', medium: 'متوسطة', low: 'منخفضة' }, why: 'لماذا اخترناها', notFit: 'قد لا تناسبك عندما', evidence: 'المصدر الرسمي', match: 'مطابقة', footer: 'نظام توصيات أدوات قائم على الأدلة', connected: 'متصل بالخادم',
  },
  en: {
    title: 'Smart Tool Guide', eyebrow: 'Evidence-backed tool selection assistant', description: 'Choose your project stage and domain, then answer questions that adapt to your previous answers. You will get three clear, explainable recommendations.',
    progress: 'Step {step} of 3', stage: 'Selection', questions: 'Questions', results: 'Results',
    chooseStage: 'Choose your project stage', chooseDomain: 'Choose the project domain', stageKicker: 'STEP ONE', domainKicker: 'CUSTOMIZE THE PATH', questionsKicker: 'STEP TWO', resultsKicker: 'STEP THREE', resultsHeading: 'Best-fit recommendations',
    back: 'Back', next: 'Next question', restart: 'Start over',
    questionProgress: '{count} answers · 6 to 10 questions', chooseAnswer: 'Choose one answer', chooseMany: 'You can choose more than one answer', textAnswer: 'Describe the need clearly and specifically…', clarification: 'The category was not clear enough. Choose the closest intent.',
    required: 'Please provide an answer before continuing.', loading: 'Loading…', loadingRecommendations: 'Analyzing the answer and selecting the next question…',
    connectionError: 'Unable to connect to the server. Make sure it is running and try again.', serverError: 'The data could not be loaded. Please try again.',
    stageDescriptions: { analysis: 'Understand the need and collect evidence.', design: 'Design the interface and user experience.', implementation: 'Build the solution and write code.', testing: 'Test and validate quality.' },
    stageIcons: { analysis: '⌕', design: '✦', implementation: '⌘', testing: '✓' },
    domainDescriptions: { software: 'Software engineering and digital products.', artificial_intelligence: 'Models, agents, and AI applications.', cybersecurity: 'Protection, threat modeling, and security testing.' },
    domainIcons: { software: '⌘', artificial_intelligence: '✦', cybersecurity: '◇' },
    confidence: 'Confidence', confidenceLevels: { high: 'High', medium: 'Medium', low: 'Low' }, why: 'Why it was selected', notFit: 'May not fit when', evidence: 'Official source', match: 'match', footer: 'Evidence-backed tool recommendation system', connected: 'Connected to server',
  },
};

const $ = selector => document.querySelector(selector);
const text = (key, values = {}) => Object.entries(values).reduce(
  (value, [name, replacement]) => value.replace(`{${name}}`, replacement),
  dictionary[state.language][key] || key,
);
const safe = value => String(value ?? '').replace(/[&<>'"]/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[character]));
const itemText = value => typeof value === 'string' ? value : value?.[state.language] || value?.en || value?.ar || '';

function setLanguage(language) {
  state.language = language;
  localStorage.setItem('tool-guide-language', language);
  document.documentElement.lang = language;
  document.documentElement.dir = language === 'ar' ? 'rtl' : 'ltr';
  document.title = dictionary[language].title;
  $('#language-button').textContent = language === 'ar' ? 'EN' : 'AR';
  $('#language-button').setAttribute('aria-label', language === 'ar' ? 'Switch to English' : 'التبديل إلى العربية');
  $('#eyebrow').textContent = text('eyebrow');
  $('#page-title').textContent = text('title');
  $('#page-description').textContent = text('description');
  $('#step-stage').textContent = text('stage');
  $('#step-questions').textContent = text('questions');
  $('#step-results').textContent = text('results');
  $('#stages-kicker').textContent = text('stageKicker');
  $('#stages-heading').textContent = text('chooseStage');
  $('#domains-kicker').textContent = text('domainKicker');
  $('#domains-heading').textContent = text('chooseDomain');
  $('#questions-kicker').textContent = text('questionsKicker');
  $('#results-kicker').textContent = text('resultsKicker');
  $('#results-heading').textContent = text('resultsHeading');
  $('#back-button').textContent = text('back');
  $('#domains-back-button').textContent = text('back');
  $('#recommend-button').textContent = text('next');
  $('#restart-button').textContent = text('restart');
  $('#footer-text').textContent = text('footer');
  renderProgress('stages');
}

function showNotice(message, error = false) {
  const notice = $('#notice');
  notice.textContent = message;
  notice.className = `notice${error ? ' error' : ''}`;
}

function clearNotice() { $('#notice').className = 'notice hidden'; }

function showScreen(name) {
  ['stages', 'domains', 'questions', 'results'].forEach(screen => {
    $(`#${screen}-screen`).classList.toggle('hidden', screen !== name);
  });
  renderProgress(name);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function renderProgress(screen) {
  const step = ['stages', 'domains'].includes(screen) ? 1 : screen === 'questions' ? 2 : 3;
  const percentage = step === 1 ? 33 : step === 2 ? 66 : 100;
  $('#progress-text').textContent = text('progress', { step });
  $('#progress-value').textContent = `${percentage}%`;
  $('#progress-bar').style.width = `${percentage}%`;
  ['stage', 'questions', 'results'].forEach((name, index) => {
    $(`#step-${name}`).classList.toggle('text-orange', index < step);
  });
}

async function request(path, options = {}) {
  const response = await fetch(`${apiBase}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!response.ok) {
    let payload = null;
    try { payload = await response.json(); } catch (_) { /* ignored */ }
    throw new Error(ToolGuideApiErrors.responseErrorMessage(payload, text('serverError')));
  }
  return response.json();
}

async function loadStages() {
  clearNotice();
  $('#stages-grid').innerHTML = `<p class="loading">${safe(text('loading'))}</p>`;
  try {
    state.stages = await request(`/stages?language=${state.language}`);
    $('#connection').textContent = text('connected');
    $('#connection').classList.remove('hidden');
    renderStages();
  } catch (error) {
    $('#connection').classList.add('hidden');
    $('#stages-grid').innerHTML = '';
    showNotice(error instanceof TypeError ? text('connectionError') : error.message, true);
  }
}

function renderStages() {
  const labels = dictionary[state.language];
  $('#stages-grid').innerHTML = state.stages.map(stage => `
    <button class="stage-card" type="button" data-stage-id="${safe(stage.id)}">
      <span class="stage-icon" aria-hidden="true">${safe(labels.stageIcons[stage.id] || '•')}</span>
      <h3>${safe(itemText(stage.name))}</h3>
      <p>${safe(labels.stageDescriptions[stage.id] || '')}</p>
    </button>
  `).join('') || `<p class="loading">${safe(text('serverError'))}</p>`;
  document.querySelectorAll('[data-stage-id]').forEach(button => {
    button.addEventListener('click', () => chooseStage(button.dataset.stageId));
  });
}

async function chooseStage(stageId) {
  clearNotice();
  state.questionnaire.selectStage(stageId);
  $('#domains-grid').innerHTML = `<p class="loading">${safe(text('loading'))}</p>`;
  showScreen('domains');
  try {
    state.domains = await request(`/domains?language=${state.language}`);
    renderDomains();
  } catch (error) {
    showNotice(error instanceof TypeError ? text('connectionError') : error.message, true);
  }
}

function renderDomains() {
  const labels = dictionary[state.language];
  $('#domains-grid').innerHTML = state.domains.map(domain => `
    <button class="stage-card domain-card" type="button" data-domain-id="${safe(domain.id)}">
      <span class="stage-icon" aria-hidden="true">${safe(labels.domainIcons[domain.id] || '•')}</span>
      <h3>${safe(itemText(domain.name))}</h3>
      <p>${safe(labels.domainDescriptions[domain.id] || '')}</p>
    </button>
  `).join('');
  document.querySelectorAll('[data-domain-id]').forEach(button => {
    button.addEventListener('click', () => startQuestionnaire(button.dataset.domainId));
  });
}

async function startQuestionnaire(domainId) {
  state.questionnaire.selectDomain(domainId);
  const stage = state.stages.find(candidate => candidate.id === state.questionnaire.stage);
  const domain = state.domains.find(candidate => candidate.id === domainId);
  $('#questions-heading').textContent = `${itemText(stage?.name)} · ${itemText(domain?.name)}`;
  $('#questions-list').innerHTML = `<p class="loading">${safe(text('loading'))}</p>`;
  showScreen('questions');
  await advanceQuestionnaire();
}

async function advanceQuestionnaire() {
  clearNotice();
  try {
    const outcome = await request('/questionnaire/advance', {
      method: 'POST',
      body: JSON.stringify(state.questionnaire.toRequest(state.language)),
    });
    state.currentStatus = outcome.status;
    $('#question-count').textContent = text('questionProgress', { count: outcome.answered_count });
    if (outcome.status === 'complete') {
      state.currentQuestion = null;
      renderResults(outcome.recommendations || []);
      showScreen('results');
      return;
    }
    state.currentQuestion = outcome.question;
    renderQuestion(outcome.question, outcome.status === 'clarification' ? outcome.clarification_options : null);
  } catch (error) {
    showNotice(error instanceof TypeError ? text('connectionError') : error.message, true);
  }
}

function renderQuestion(question, clarificationOptions = null) {
  if (!question) {
    $('#questions-list').innerHTML = `<p class="loading">${safe(text('serverError'))}</p>`;
    return;
  }
  const options = clarificationOptions || question.options || [];
  const multiple = question.type === 'multiple_choice' && !clarificationOptions;
  const textQuestion = question.type === 'short_text' && !clarificationOptions;
  const help = clarificationOptions ? text('clarification') : textQuestion ? '' : multiple ? text('chooseMany') : text('chooseAnswer');
  const input = textQuestion
    ? `<label class="sr-only" for="current-text-answer">${safe(text('textAnswer'))}</label><textarea id="current-text-answer" class="text-answer" name="${safe(question.id)}" required maxlength="500" placeholder="${safe(text('textAnswer'))}"></textarea>`
    : `<fieldset class="answers"><legend class="sr-only">${safe(help)}</legend>${options.map(option => `<label class="answer-choice"><input type="${multiple ? 'checkbox' : 'radio'}" name="${safe(question.id)}" value="${safe(option.id)}" ${multiple ? '' : 'required'} /><span>${safe(itemText(option.label))}</span></label>`).join('')}</fieldset>`;
  const number = Math.min(state.questionnaire.answers.length + 1, 10);
  $('#questions-list').innerHTML = `
    <article class="question-card">
      <p class="question-number">${String(number).padStart(2, '0')}</p>
      <h3 class="question-prompt">${safe(itemText(question.prompt))}</h3>
      <p class="question-help">${safe(help)}</p>
      ${input}
    </article>`;
  const firstControl = $('#questions-list').querySelector('input, textarea');
  firstControl?.focus();
}

function collectCurrentAnswer() {
  const question = state.currentQuestion;
  if (!question) return null;
  const form = $('#questions-form');
  if (question.type === 'short_text' && state.currentStatus !== 'clarification') {
    const field = form.elements.namedItem(question.id);
    const value = field?.value.trim();
    return value ? { question_id: question.id, text: value } : null;
  }
  const selected = [...form.querySelectorAll(`input[name="${CSS.escape(question.id)}"]:checked`)].map(input => input.value);
  return selected.length ? { question_id: question.id, option_ids: selected } : null;
}

async function submitAnswer(event) {
  event.preventDefault();
  clearNotice();
  const answer = collectCurrentAnswer();
  if (!answer) { showNotice(text('required'), true); return; }
  const alreadyRecorded = state.questionnaire.askedQuestionIds.includes(answer.question_id);
  if (alreadyRecorded) state.questionnaire.replaceAnswer(answer);
  else state.questionnaire.recordAnswer(answer);
  const button = $('#recommend-button');
  button.disabled = true;
  button.textContent = text('loadingRecommendations');
  await advanceQuestionnaire();
  button.disabled = false;
  button.textContent = text('next');
}

function renderResults(recommendations) {
  const labels = dictionary[state.language];
  $('#results-list').innerHTML = recommendations.map((recommendation, index) => `
    <article class="result-card">
      <span class="rank">${index + 1}</span>
      <div class="result-content">
        <div class="result-heading">
          <h3>${safe(recommendation.tool_name)}</h3>
          <div class="match-score"><strong>${safe(recommendation.match_percent)}%</strong><span>${safe(text('match'))}</span></div>
        </div>
        <p class="confidence-line">${safe(text('confidence'))}: <strong>${safe(labels.confidenceLevels[recommendation.confidence] || recommendation.confidence)}</strong></p>
        <div class="result-detail"><h4>${safe(text('why'))}</h4><ul>${(recommendation.reasons || []).map(reason => `<li>${safe(reason)}</li>`).join('')}</ul></div>
        <div class="result-detail limitation"><h4>${safe(text('notFit'))}</h4><ul>${(recommendation.limitations || []).map(reason => `<li>${safe(reason)}</li>`).join('')}</ul></div>
        <a class="evidence-link" href="${safe(recommendation.source_url)}" target="_blank" rel="noreferrer">${safe(text('evidence'))} ↗</a>
      </div>
    </article>
  `).join('') || `<p class="loading">${safe(text('serverError'))}</p>`;
}

function restart() {
  state.questionnaire.restart();
  state.currentQuestion = null;
  state.currentStatus = null;
  showScreen('stages');
  loadStages();
}

$('#language-button').addEventListener('click', () => {
  setLanguage(state.language === 'ar' ? 'en' : 'ar');
  restart();
});
$('#domains-back-button').addEventListener('click', () => {
  state.questionnaire.selectStage(state.questionnaire.stage);
  showScreen('stages');
});
$('#back-button').addEventListener('click', () => {
  state.questionnaire.selectStage(state.questionnaire.stage);
  showScreen('domains');
});
$('#restart-button').addEventListener('click', restart);
$('#questions-form').addEventListener('submit', submitAnswer);

setLanguage(state.language);
loadStages();
