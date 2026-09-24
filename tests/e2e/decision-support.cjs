const { test } = require('node:test');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');

const origin = process.env.TOOLGUIDE_URL || 'http://127.0.0.1:8000';

async function finishQuestionnaire(page, language) {
  for (let n = 0; n < 11; n++) {
    if (await page.locator('#results-screen').isVisible()) return;
    const textarea = page.locator('#questions-list textarea');
    if (await textarea.count()) await textarea.fill(language === 'ar' ? 'اكتشاف المشهد' : 'Discover the landscape');
    else await page.locator('#questions-list input').first().check();
    const response = page.waitForResponse(r => r.url().endsWith('/questionnaire/advance') && r.request().method() === 'POST');
    await page.locator('#recommend-button').click();
    assert.equal((await response).status(), 200);
    await page.waitForFunction(() => !document.querySelector('#recommend-button').disabled);
  }
  assert.fail('Questionnaire did not complete');
}

test('bilingual decision support controls and safe detail rendering', async () => {
  const browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL || undefined });
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(origin);
    await page.locator('[data-stage-id="design"]').click();
    await page.locator('[data-domain-id="cybersecurity"]').click();
    await page.locator('#constraints-form').waitFor({ state: 'visible' });
    assert.equal(await page.locator('#constraints-form input[type="checkbox"]:visible').count(), 3);
    const preparation = page.locator('#constraints-form [name="allows_online_preparation"]');
    assert.equal(await preparation.isVisible(), false);
    await page.locator('#constraints-form [name="requires_offline"]').check();
    assert.equal(await preparation.isVisible(), true);
    await preparation.check();
    await page.locator('#constraints-form [name="requires_offline"]').uncheck();
    assert.equal(await preparation.isVisible(), false);
    assert.equal(await preparation.isChecked(), false);
    await page.locator('#constraints-start-button').click();
    await page.locator('#questions-list input, #questions-list textarea').first().waitFor();
    // Exercise public renderers with hostile content and unknown evidence.
    const result = await page.evaluate(() => {
      const profile = { deployment: '<img src=x onerror=alert(1)>', pricing_summary: 'Limited free plan',
        learning_curve: 'Editorial estimate', integrations: [], sources: ['javascript:alert(1)'],
        reviewed_at: '2026-09-05', offline: { value: null }, free_plan: { value: false },
        open_source: { value: true }, starter_guide: { prerequisites: ['Test prerequisite'],
          steps: [1, 2, 3].map(n => ({ instruction: `Step ${n}`, source_url: 'https://example.com/' })),
          example: '<script>alert(1)</script>', expected_outcome: 'A model', reviewed_at: '2026-09-05' } };
      const tool = { id: 'sample', name: 'Example', profile, limitations: ['A limit'] };
      const comparison = ToolGuideComparison.renderToolComparison([tool], 'en');
      const guide = ToolGuideStarter.renderStarterGuide(tool, 'en');
      document.body.append(comparison, guide);
      return { comparison: comparison.textContent, guide: guide.textContent,
        injected: comparison.querySelectorAll('img,script').length + guide.querySelectorAll('script').length,
        unsafeLinks: comparison.querySelectorAll('a[href^="javascript:"]').length,
        steps: guide.querySelectorAll('ol li').length };
    });
    assert.match(result.comparison, /Not documented/);
    assert.match(result.comparison, /No/);
    assert.match(result.guide, /Step 3/);
    assert.equal(result.injected, 0);
    assert.equal(result.unsafeLinks, 0);
    assert.equal(result.steps, 3);
    assert.deepEqual(errors, []);
  } finally { await browser.close(); }
});

for (const language of ['en', 'ar']) {
  test(`selected setup scope and missing setup never inherit product claims (${language})`, async () => {
    const browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL || undefined });
    try {
      const page = await browser.newPage();
      await page.goto(origin);
      const output = await page.evaluate(language => {
        const guide = { prerequisites: ['Prepared files'], steps: [{ instruction: 'Run locally', source_url: 'https://example.com/docs' }],
          example: 'Local example', expected_outcome: 'Local output', reviewed_at: '2026-09-06' };
        const setup = { id: 'local', name: 'Local selected setup', task: 'Convert one document', platform: 'Local Linux',
          version: '1.2', local_components: ['Converter'], model: 'Local model', preparation_network: 'required',
          runtime_network: 'not_required', download_requirements: 'Cache model weights', offline_features: ['Document conversion'],
          online_only_features: ['Remote enrichment'], hardware_requirements: 'Test hardware', offline: { value: true },
          free_plan: { value: null }, open_source: { value: true }, evidence_status: 'official_documentation',
          evidence: [{ summary: 'Local task evidence', version_scope: 'Converter 1.2 only', limitations: 'Remote plugins excluded',
            source_url: 'https://example.com/local', reviewed_at: '2026-09-06' }], starter_guide: guide };
        const profile = { operation_setups: [setup], offline: { value: false }, free_plan: { value: true }, open_source: { value: false },
          deployment: 'PRODUCT CLOUD CLAIM', pricing_summary: 'PRODUCT PRICE CLAIM', sources: ['https://example.com/product'],
          starter_guide: { ...guide, example: 'PRODUCT GUIDE CLAIM' } };
        const tool = { id: 'test', name: 'Product', matching_setup_id: 'local', profile, limitations: ['PRODUCT LIMIT CLAIM'] };
        const comparison = ToolGuideComparison.renderToolComparison([tool], language);
        const starter = ToolGuideStarter.renderStarterGuide(tool, language); starter.open = true;
        const missing = { ...tool, matching_setup_id: 'missing' };
        const missingComparison = ToolGuideComparison.renderToolComparison([missing], language);
        const missingGuide = ToolGuideStarter.renderStarterGuide(missing, language); missingGuide.open = true;
        document.body.append(comparison, starter, missingComparison, missingGuide);
        return { comparison: comparison.innerText, starter: starter.innerText,
          missingComparison: missingComparison.innerText, missingGuide: missingGuide.innerText,
          direction: starter.querySelector('.setup-scope').dir };
      }, language);
      assert.match(output.comparison, /Local selected setup/);
      assert.match(output.comparison, /Convert one document/);
      assert.match(output.comparison, /Cache model weights/);
      assert.match(output.comparison, /Remote enrichment/);
      assert.match(output.starter, /Converter 1.2 only/);
      assert.match(output.starter, /Remote plugins excluded/);
      assert.match(output.starter, language === 'ar' ? /الشبكة أثناء المهمة/ : /Network during the task/);
      assert.equal(output.direction, language === 'ar' ? 'rtl' : 'ltr');
      for (const text of Object.values(output)) assert.doesNotMatch(text, /PRODUCT (CLOUD|PRICE|GUIDE|LIMIT) CLAIM/);
      assert.match(output.missingGuide, language === 'ar' ? /الإعداد المختار غير موثق/ : /Selected setup is not documented/);
      assert.doesNotMatch(output.missingGuide, /Run locally/);
      assert.doesNotMatch(output.missingComparison, /Local selected setup/);
    } finally { await browser.close(); }
  });
}

test('no-match alternative prefills an isolated scenario without requesting or adopting it', async () => {
  const browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL || undefined });
  try {
    const page = await browser.newPage();
    let compareRequests = 0;
    page.on('request', request => { if (request.url().endsWith('/questionnaire/compare')) compareRequests++; });
    await page.goto(origin);
    await page.locator('[data-stage-id="analysis"]').click();
    await page.locator('[data-domain-id="software"]').click();
    const baseline = await page.evaluate(() => {
      const original = state.questionnaire.toRequest(state.language);
      original.constraints = { requires_offline: true, requires_free_plan: false, requires_open_source: false, allows_online_preparation: false };
      state.questionnaire.adoptRequest(original);
      applyQuestionnaireOutcome({ status: 'no_match', recommendations: [], answered_count: 0, knowledge_version: 'fixture-v1',
        alternatives: [{ tool_name: 'Prepared local tool', setup_name: 'Local task', changed_constraints: ['allows_online_preparation'] }] });
      return state.questionnaire.toRequest(state.language);
    });
    await page.locator('#result-support article button').click();
    assert.equal(await page.locator('#scenario-host [name="requires_offline"]').isChecked(), true);
    assert.equal(await page.locator('#scenario-host [name="allows_online_preparation"]').isChecked(), true);
    assert.equal(await page.locator('#scenario-host > section > button').isDisabled(), true);
    assert.equal(compareRequests, 0);
    assert.deepEqual(await page.evaluate(() => state.questionnaire.toRequest(state.language)), baseline);
    await page.locator('#scenario-host .support-actions button[type="button"]').click();
    assert.deepEqual(await page.evaluate(() => state.questionnaire.toRequest(state.language)), baseline);
  } finally { await browser.close(); }
});

for (const language of ['ar', 'en']) {
  test(`complete comparison, guides, cancel and adopt scenarios (${language})`, async () => {
    const browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL || undefined });
    try {
      const page = await browser.newPage({ viewport: language === 'ar' ? { width: 390, height: 844 } : { width: 1365, height: 900 } });
      const errors = []; page.on('pageerror', error => errors.push(error.message));
      await page.goto(origin);
      if (language === 'en') await page.locator('#language-button').click();
      await page.locator('[data-stage-id="analysis"]').click();
      await page.locator('[data-domain-id="software"]').click();
      await page.locator('#constraints-start-button').click();
      await page.locator('#questions-list input, #questions-list textarea').first().waitFor();
      await finishQuestionnaire(page, language);
      assert.equal(await page.locator('#results-list .result-card').count(), 3);
      const original = await page.locator('#results-list .result-heading h3').allTextContents();
      await page.locator('#results-list .starter-guide').first().waitFor();
      await page.locator('#results-list .starter-guide summary').first().focus();
      await page.keyboard.press('Enter');
      assert.equal(await page.locator('#results-list .starter-guide').first().getAttribute('open'), '');
      assert.ok(await page.locator('#results-list .starter-guide').first().locator('ol li').count() >= 3);
      await page.locator('#compare-button').click();
      assert.equal(await page.locator('#comparison-host table thead th').count(), 4);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
      // An older failed detail retry cannot overwrite a newer successful load.
      let release, started;
      const held = new Promise(resolve => { release = resolve; });
      const firstStarted = new Promise(resolve => { started = resolve; });
      let detailRequests = 0;
      await page.route('**/api/tools/**', async route => {
        detailRequests++;
        if (detailRequests <= 3) {
          if (detailRequests === 3) started();
          await held; await route.abort();
        } else await route.continue();
      });
      await page.evaluate(() => { globalThis.firstDetailLoad = loadResultDetails(state.outcome); });
      await firstStarted;
      await page.evaluate(() => loadResultDetails(state.outcome));
      release();
      await page.evaluate(() => globalThis.firstDetailLoad);
      await page.unroute('**/api/tools/**');
      assert.equal(await page.locator('#results-list .starter-guide').count(), 3);
      assert.equal(await page.locator('#comparison-host table').count(), 1);
      await page.screenshot({ path: `tmp/decision-support/results-${language}.png`, fullPage: true });
      await page.locator('#scenario-button').click();
      const requirement = page.locator('#scenario-host [name="requires_open_source"]');
      await requirement.check();
      const previewResponse = page.waitForResponse(r => r.url().endsWith('/questionnaire/compare'));
      await page.locator('#scenario-host button[type="submit"]').click();
      const previewBody = await (await previewResponse).json();
      assert.equal(previewBody.variant.status, 'no_match');
      const adopt = page.locator('#scenario-host > section > button');
      await adopt.waitFor(); await page.waitForFunction(() => !document.querySelector('#scenario-host > section > button').disabled);
      assert.deepEqual(await page.locator('#results-list .result-heading h3').allTextContents(), original);
      await page.locator('#scenario-host .support-actions button[type="button"]').click();
      assert.equal(await page.locator('#scenario-host section').count(), 0);
      assert.deepEqual(await page.locator('#results-list .result-heading h3').allTextContents(), original);
      // A failed preview must keep the original and disable adoption.
      await page.locator('#scenario-button').click();
      await page.route('**/questionnaire/compare', route => route.abort());
      await page.locator('#scenario-host button[type="submit"]').click();
      await page.locator('#scenario-host .scenario-result p').filter({ hasText: language === 'ar' ? 'تعذر' : 'Could not' }).waitFor();
      assert.equal(await page.locator('#scenario-host > section > button').isDisabled(), true);
      assert.deepEqual(await page.locator('#results-list .result-heading h3').allTextContents(), original);
      await page.unroute('**/questionnaire/compare');
      await page.locator('#scenario-host [name="requires_open_source"]').check();
      await page.locator('#scenario-host button[type="submit"]').click();
      await page.waitForFunction(() => !document.querySelector('#scenario-host > section > button').disabled);
      // Adoption uses the already validated preview, even if a fresh advance is unavailable.
      await page.route('**/questionnaire/advance', route => route.abort());
      await page.locator('#scenario-host > section > button').click();
      await page.waitForFunction(() => document.querySelectorAll('#results-list .result-card').length === 0, null, { timeout: 5000 });
      await page.unroute('**/questionnaire/advance');
      assert.ok((await page.locator('#result-support').innerText()).includes(language === 'ar' ? 'لا توجد أداة' : 'No documented tool'));
      // Explicitly relaxing the requirement restores the original eligible ranking.
      await page.locator('#scenario-button').click();
      await page.locator('#scenario-host [name="requires_open_source"]').uncheck();
      await page.locator('#scenario-host button[type="submit"]').click();
      await page.waitForFunction(() => !document.querySelector('#scenario-host > section > button').disabled);
      await page.locator('#scenario-host > section > button').click();
      await page.waitForFunction(() => document.querySelectorAll('#results-list .result-card').length === 3);
      assert.deepEqual(await page.locator('#results-list .result-heading h3').allTextContents(), original);
      // Editing an earlier answer submits a real counterfactual without changing the original.
      await page.locator('#scenario-button').click();
      const group = page.locator('#scenario-host .scenario-answer:has(input[type="radio"])').first();
      const choices = group.locator('input');
      const oldChoice = await group.locator('input:checked').inputValue();
      for (let i = 0; i < await choices.count(); i++) {
        if (await choices.nth(i).inputValue() !== oldChoice) { await choices.nth(i).check(); break; }
      }
      const answerPreview = page.waitForResponse(r => r.url().endsWith('/questionnaire/compare'));
      await page.locator('#scenario-host button[type="submit"]').click();
      const answerResponse = await answerPreview;
      const sent = answerResponse.request().postDataJSON();
      assert.notDeepEqual(sent.baseline.answers, sent.variant.answers);
      const direct = await page.request.post(`${origin}/api/questionnaire/advance`, { data: sent.variant });
      assert.deepEqual((await answerResponse.json()).variant, await direct.json());
      assert.deepEqual(await page.locator('#results-list .result-heading h3').allTextContents(), original);
      await page.locator('#scenario-host .support-actions button[type="button"]').click();
      assert.deepEqual(errors, []);
    } finally { await browser.close(); }
  });
}

test('early no-match scenario adopts an unfinished questionnaire', async () => {
  const browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL || undefined });
  try {
    const page = await browser.newPage();
    await page.goto(origin);
    await page.locator('[data-stage-id="analysis"]').click();
    await page.locator('[data-domain-id="software"]').click();
    await page.locator('#constraints-editor [name="requires_open_source"]').check();
    await page.locator('#constraints-start-button').click();
    await page.locator('#results-screen').waitFor({ state: 'visible' });
    await page.locator('#scenario-button').click();
    await page.locator('#scenario-host [name="requires_open_source"]').uncheck();
    const response = page.waitForResponse(r => r.url().endsWith('/questionnaire/compare'));
    await page.locator('#scenario-host button[type="submit"]').click();
    const body = await (await response).json();
    assert.equal(body.variant.status, 'question'); assert.deepEqual(body.changes, []);
    await page.waitForFunction(() => !document.querySelector('#scenario-host > section > button').disabled);
    await page.locator('#scenario-host > section > button').click();
    await page.locator('#questions-list input, #questions-list textarea').first().waitFor();
    assert.equal(await page.locator('#questions-screen').isVisible(), true);
  } finally { await browser.close(); }
});
