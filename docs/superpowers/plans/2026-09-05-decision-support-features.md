# خطة تنفيذ ميزات دعم القرار

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking. لا تبدأ التنفيذ ضمن طلب إعداد الخطة.

**Goal:** تنفيذ مقارنة الأدوات، وتجربة «ماذا لو؟»، وخطة بداية لكل توصية، والقيود الإلزامية مقابل التفضيلات.

**Architecture:** توسيع كتالوج المعرفة الحالي بخصائص موثقة وخطوات بداية، وإضافة تقييم موحد تستخدمه جلسة الأسئلة وتجربة السيناريوهات. يبقى الخادم بلا جلسات مخزنة، وتبقى الواجهة JavaScript عادية، وتُحسب النتائج في الخادم.

**Tech Stack:** Python 3.12+، FastAPI، Pydantic، clipspy، HTML/CSS/JavaScript، pytest، واختبارات Node.js 24+ الحالية.

**Spec:** متطلبات المستخدم في المحادثة بتاريخ 2026-09-05؛ التصميم المقترح ومعايير القبول مثبتة أدناه في هذه الخطة. الخطة مقترحة وليست تنفيذاً أو اعتماداً سابقاً لكل تفاصيل التصميم.

## النطاق والقرارات

المقصود بالأرقام هو قائمة الميزات في الرد السابق: 1 المقارنة، 2 ماذا لو، 4 خطة البداية، 5 القيود. ترتيب التنفيذ يختلف عن ترتيب العرض بسبب الاعتماديات.

- واجهة ومحتوى بالعربية والإنجليزية، مع RTL والموبايل ولوحة المفاتيح.
- المحافظة على الكتالوج الحالي: 48 أداة في 12 مساراً؛ توسيع عدد الأدوات مشروع لاحق.
- البيانات المنشورة والمقارنات وخطوات البداية موثقة من المصادر الرسمية وقت التنفيذ؛ لا نختلق أسعاراً أو قدرات، ولا نضيف بحثاً حياً أثناء استخدام التطبيق.
- المعلومات غير المتاحة تظهر «غير موثّق»، ولا تُعامل كإثبات استيفاء شرط إلزامي.
- الإبقاء على 6–10 أسئلة عند وجود أدوات مؤهلة؛ عند عدم وجود أي أداة مؤهلة يمكن إظهار نتيجة عدم التطابق مبكراً.
- لا تتغير نتيجة الأصل عند معاينة سيناريو؛ اعتماد التعديل إجراء صريح.
- الحفاظ على عقد `/api/recommendations` القديم الذي يطلب ثلاث نتائج. الميزات الجديدة تخص مسار questionnaire وعقوده.
- حفظ الجلسات الدائم، الحسابات، لوحة إدارة المعرفة، وتوسيع الكتالوج خارج هذه الدفعة.
- لا نضيف قاعدة بيانات أو إطار واجهة جديداً. تُضاف أدوات اختبار متصفح فقط إذا احتاج التشغيل الآلي ذلك.

## تجربة المستخدم المقترحة

1. اختيار المرحلة والمجال، ثم شروط إلزامية اختيارية مع شرح الفرق بينها وبين التفضيلات.
2. الإجابة عن الأسئلة الحالية؛ التفضيلات تؤثر في النقاط، والشروط تحدد الأهلية.
3. عرض صفر إلى ثلاث أدوات مؤهلة، مع سبب قلة العدد عند الحاجة.
4. فتح مقارنة الخصائص بين النتائج، ثم «ابدأ بهذه الأداة» لعرض خطواتها.
5. فتح «ماذا لو؟»، وتغيير شرط أو إجابة سابقة، ثم مشاهدة الأصل والسيناريو والفرق بينهما.
6. اختيار «اعتماد السيناريو» أو «إلغاء». أي أسئلة إضافية مطلوبة تظهر قبل وصف السيناريو بأنه نتيجة مكتملة.

## بدائل التصميم

- **الموصى به:** توسيع الكتالوج والتقييم الحاليين. مصدر واحد للخصائص والتفسير، وتغييرات محدودة في البنية.
- تنفيذ المقارنة والسيناريو في المتصفح فقط أسهل مبدئياً، لكنه يكرر منطق التقييم ويجعل قواعد الأهلية مختلفة بين الواجهة والخادم.
- توليد المقارنات وخطط البداية بنموذج أثناء الطلب يزيد عدم الحتمية ومتطلبات التحقق؛ لا نعتمده لهذه النسخة.

## العقود المشتركة المقترحة

ملف جديد `app/domain/tool_profiles.py` يملك النماذج التالية؛ تُستخدم `DomainModel` و`LocalizedText` الموجودتان:

```python
class CapabilityEvidence(DomainModel):
    value: bool | None = None
    source_url: HttpUrl | None = None
    reviewed_at: date | None = None

class HardConstraints(DomainModel):
    requires_offline: bool = False
    requires_free_plan: bool = False
    requires_open_source: bool = False

class StarterStep(DomainModel):
    instruction: LocalizedText
    source_url: HttpUrl

class StarterGuide(DomainModel):
    prerequisites: list[LocalizedText]
    steps: list[StarterStep] = Field(min_length=3, max_length=5)
    example: LocalizedText
    expected_outcome: LocalizedText
    reviewed_at: date

class ToolProfile(DomainModel):
    offline: CapabilityEvidence
    free_plan: CapabilityEvidence
    open_source: CapabilityEvidence
    deployment: LocalizedText
    pricing_summary: LocalizedText
    learning_curve: LocalizedText
    integrations: list[LocalizedText]
    sources: list[HttpUrl] = Field(min_length=1)
    reviewed_at: date
    starter_guide: StarterGuide
```

تضاف `profile: ToolProfile | None = None` إلى Tool للتوافق مع بيانات الاختبارات القديمة؛ تدقيق كتالوج الإنتاج يفرض وجودها للأدوات الـ48. قيم القدرات المعروفة تتطلب رابطاً وتاريخ مراجعة؛ القيمة المجهولة تبقى None. التشغيل المحلي لا يثبت العمل دون إنترنت، والمصدر المفتوح لا يثبت وجود خطة مجانية. صعوبة التعلم تقدير تحريري معلن مع سبب مختصر، وليست حقيقة يدّعيها المورد.

تضاف `constraints` إلى QuestionnaireRequest بقيمة افتراضية خالية. تُعرّف EligibilityDecision في `app/questionnaire/eligibility.py` بحقول `tool_id` و`eligible` و`failed_constraints` و`unknown_constraints`؛ القائمتان تحتويان مفاتيح HardConstraints نفسها.

تضاف إلى النتيجة `eligible_count` و`excluded_tools` و`knowledge_version`. تُضاف حالة `no_match`؛ تحتوي نتائجها قائمة توصيات فارغة. الحالات المكتملة الأخرى تعرض 1–3 توصيات. نسخة المعرفة SHA-256 لمحتوى JSON المفكوك بترتيب مفاتيح ثابت، بما فيه ملفات التوسعة المدمجة؛ لا تعتمد على طابع gzip الزمني.

## المهمة 1: إثراء المعرفة والتحقق منها

**تعديل:** `app/domain/models.py`، `app/knowledge/models.py`، `app/knowledge/loader.py`، `scripts/build_adaptive_knowledge.py`، `scripts/audit_phase6.py`.

**إنشاء:** `app/domain/tool_profiles.py`، `data/knowledge/tool_profiles.json`، `tests/test_tool_profiles.py`.

**مخرجات:** ملفات خصائص عربية وإنجليزية، مدمجة في `data/knowledge/adaptive.json.gz` بواسطة الباني الحالي؛ نسخة معرفة قابلة لإعادة الإنتاج.

- [x] كتابة اختبار يرفض قدرة value=True أو False بلا مصدر/تاريخ، ويقبل None كمعلومة مجهولة.
- [x] تشغيل `python -m pytest tests/test_tool_profiles.py -q` والتأكد أن الفشل ناتج عن السلوك الجديد المفقود.
- [x] تطبيق النماذج أعلاه ومدققاتها، ودمج ملفات الخصائص بحسب tool_id؛ رفض التكرار والمعرفات المجهولة وفقدان أدوات الإنتاج.
- [x] مراجعة المصادر الرسمية للأدوات الـ48 أثناء التنفيذ؛ توثيق أو ترك مجهول لكل قدرة، وكتابة 3–5 خطوات بداية خاصة بالأداة والمسار مع مثال ومخرج متوقع.
- [x] إضافة تدقيق اكتمال اللغتين والمصادر والتواريخ وتوافق المراجع، واختبار أن إعادة بناء الكتالوج تنتج نسخة محتوى ثابتة.
- [x] تشغيل اختبارات المعرفة والباني والتدقيق؛ مراجعة فرق البيانات ثم حفظ تغييرات المهمة في commit مستقل.

**قبول:** لا معلومة مخترعة أو قيمة مجهولة تتحول إلى true، ولا أداة بلا خطة بداية. عند تعذر الوصول لمصدر لازم يُسجل النقص ويمنع إعلان اكتمال المحتوى.

## المهمة 2: الأهلية وتوحيد التقييم

**إنشاء:** `app/questionnaire/eligibility.py`، `app/questionnaire/evaluation.py`، `tests/test_questionnaire_eligibility.py`.

**تعديل:** `app/questionnaire/service.py`، `app/questionnaire/selector.py`، `app/questionnaire/models.py`، `tests/test_questionnaire_service.py`، `tests/test_questionnaire_selector.py`.

**واجهة الأهلية:** `evaluate_eligibility(tool: Tool, constraints: HardConstraints) -> EligibilityDecision`.

**واجهة التقييم:** `evaluate_pool(*, tools, questions, rules, answers, constraints, engine) -> PoolEvaluation`؛ تُعرّف PoolEvaluation في evaluation.py وتحتوي `ranked_eligible: tuple[RankedTool, ...]` و`inference: InferenceResult` و`eligibility: tuple[EligibilityDecision, ...]`. الأنواع المستهلكة هي Tool، Question، Rule، AnswerSelection، ClipspyAdapter الموجودة.

```python
def test_no_constraints_keeps_legacy_tool_eligible():
    tool = Tool(id="sample", name=LocalizedText(ar="مثال", en="Example"),
                description=LocalizedText(ar="وصف", en="Description"),
                stages=[StageId.ANALYSIS])
    assert evaluate_eligibility(tool, HardConstraints()).eligible

def test_unknown_offline_capability_cannot_satisfy_requirement():
    tool = Tool(id="sample", name=LocalizedText(ar="مثال", en="Example"),
                description=LocalizedText(ar="وصف", en="Description"),
                stages=[StageId.ANALYSIS])
    result = evaluate_eligibility(tool, HardConstraints(requires_offline=True))
    assert not result.eligible
    assert result.unknown_constraints == ["requires_offline"]
```

- [x] إضافة الاختبارين مع imports من ملفات العقود المحددة، ثم حالات قيمة false وقيمة true وتعارض شروط متعددة.
- [x] تشغيل الاختبارات الجديدة قبل التطبيق.
- [x] تشغيل الاستدلال على المسار الكامل بأدواته الأربع للحفاظ على مراجع قواعد CLIPS، ثم تطبيق الأهلية قبل اختيار النتائج النهائية. لا تمرر مجموعة مختزلة إلى قواعد تشير لأدوات مستبعدة.
- [x] اختيار أول ثلاث أدوات مؤهلة وفق الدرجة الخام مع tool_id لكسر التعادل؛ إزالة إعادة الترتيب المنفصلة بحسب match_percent. النسبة مؤشر مستقل عن الرتبة وليست احتمالاً؛ تُشرح هذه النقطة في الواجهة.
- [x] حساب اختيار السؤال من درجات الأدوات المؤهلة؛ عند حساب التمييز العام تُستبعد أيضاً أوزان الأدوات غير المؤهلة. مع أداة واحدة تُستخدم موازنة أبعاد الأسئلة دون ادعاء تمييز بين أدوات.
- [x] مع أربع أدوات مؤهلة يبقى شرط الاستقرار والفصل الحالي؛ مع 1–3 أدوات يتوقف بعد ست إجابات عند ثبات ترتيب المؤهلات مقارنة بالخطوة السابقة، وإلا يستمر إلى عشر. صفر أدوات ينتج no_match.
- [x] عدم منح ثقة عالية بسبب انخفاض عدد المؤهلات وحده؛ عند أقل من أربع أدوات تبقى الثقة low في هذه الدفعة ويُشرح عدم كفاية بدائل المقارنة. معايرة الثقة العلمية خارج النطاق.
- [x] اختبار 0 و1 و2 و3 و4 أدوات مؤهلة، وبقاء الأدوات المخالفة خارج النتائج مهما علت درجاتها، واستقرار التعادل وعدم القسمة على صفر.
- [x] تشغيل اختبارات المحرك والتوصيات والاستبيان وحفظ commit مستقل.

## المهمة 3: إدخال الشروط ونتائج عدم التطابق

**تعديل:** `app/api/contracts.py`، `app/api/routes.py`، `app/localization/models.py`، `app/localization/projector.py`، `frontend/questionnaire-state.js`، `frontend/app.js`، `frontend/index.html`، `frontend/styles.css`، `tests/test_questionnaire_api.py`، `tests/frontend_questionnaire.test.cjs`.

**مخرجات:** الشروط تصل من الواجهة إلى التقييم نفسه وتُعرض أسباب الاستبعاد باللغة المختارة.

- [x] إضافة اختبارات API لطلب قديم بلا constraints وطلب بكل شرط على حدة، ولـno_match، ورفض مفاتيح غير معروفة.
- [x] تمرير HardConstraints ضمن advance؛ توسيع نماذج النتائج والمترجم والحالات في الواجهة دون تعديل العقد القديم /recommendations.
- [x] إضافة مفاتيح اختيار واضحة قبل الأسئلة، وشرح أن «مجاني» يعني وجود خطة مجانية موثقة بحدودها، وليس ضمان تنفيذ كل احتياج بلا تكلفة.
- [x] عرض «لا توجد أداة موثقة تستوفي الشروط» مع أسباب المخالفة ونقص المعلومات، وإجراء صريح لتعديل الشروط دون تخفيفها تلقائياً.
- [x] إضافة اختبارات حالة تثبت بقاء الشروط ضمن payload ومسحها عند بدء مسار جديد.
- [x] تشغيل `python -m pytest tests/test_questionnaire_api.py -q` و`node --test tests/frontend_questionnaire.test.cjs`؛ مراجعة عربية/إنجليزية وحفظ commit.

## المهمة 4: المقارنة المباشرة — الميزة 1

**تعديل:** `app/localization/models.py`، `app/localization/projector.py`، `frontend/app.js`، `frontend/index.html`، `frontend/styles.css`، `tests/test_api.py`.

**إنشاء:** `frontend/tool-comparison.js`، `tests/frontend_comparison.test.cjs`.

**واجهة:** توسيع ToolResponse بحقل profile مترجم اختياري؛ استخدام GET /api/tools/{tool_id}?language=ar الحالي لجلب تفاصيل الأدوات الظاهرة فقط. `renderToolComparison(tools, language)` في الملف الجديد يُرجع DOM آمن، ويستخدم textContent للنصوص.

- [x] اختبار أن الرد يعرض القيم الموثقة وتاريخها، ويحافظ على الحقول القديمة، ويميز false عن None.
- [x] إظهار جدول مقارنة للمزايا والقيود والتكلفة والتشغيل والتعلم والتكاملات والمصادر؛ عند نتيجة واحدة تُعرض تفاصيلها دون أعمدة فارغة.
- [x] عرض اختلافات الأدوات بنص واضح؛ لا تُعرض عبارة «الأرخص» دون بيانات قابلة للمقارنة.
- [x] تنفيذ تخطيط مناسب للموبايل والتنقل بلوحة المفاتيح، وحالات تحميل/فشل مع إعادة المحاولة دون فقدان النتائج.
- [x] اختبار نصوص غير موثوقة وروابط المصادر واللغة و0–3 أدوات؛ تشغيل اختبارات API وNode وحفظ commit.

## المهمة 5: ماذا لو — الميزة 2

**إنشاء:** `app/questionnaire/scenarios.py`، `frontend/scenario-state.js`، `frontend/scenario-panel.js`، `tests/test_questionnaire_scenarios.py`، `tests/frontend_scenarios.test.cjs`.

**تعديل:** `app/api/contracts.py`، `app/api/routes.py`، `app/localization/models.py`، `app/localization/projector.py`، `frontend/app.js`، `frontend/index.html`، `frontend/styles.css`.

**عقد الطلب الجديد:** POST /api/questionnaire/compare يستقبل `baseline: QuestionnaireRequest` و`variant: QuestionnaireRequest` و`knowledge_version: str`. الطرفان بنفس المرحلة والمجال واللغة والبذرة وتسلسل معرفات الأسئلة؛ التغيير مسموح في قيم الإجابات السابقة والشروط فقط.

**عقد النتيجة:** `baseline: QuestionnaireResponse` و`variant: QuestionnaireResponse` و`changes: list[ScenarioChange]`. تُعرّف ScenarioChange في scenarios.py بحقول `tool_id` و`before_rank: int | None` و`after_rank: int | None` و`before_match: int | None` و`after_match: int | None`. كلا التقييمين يحسبهما الخادم من نفس نسخة المعرفة.

- [x] اختبار أن إعادة نفس الطلب تنتج نفس النتيجة، وأن الأصل لا يتغير، وأن تخفيف شرط يمكن أن يعيد أداة مستبعدة دون ضمان ترتيب معين.
- [x] رفض تغيير المسار أو معرفات الأسئلة في compare بـ422؛ رفض knowledge_version مختلفة بـ409 مع رمز KNOWLEDGE_VERSION_MISMATCH ودعوة لإعادة تقييم الأصل.
- [x] استخدام خدمة الاستبيان والتقييم المشترك للطرفين، لا إنشاء معادلة نقاط ثانية. قبول تعديل إجابات الأسئلة السابقة بوصفه سيناريو مضاداً، لا ادعاء أنه نفس المسار التكيفي الذي كان سيُختار من الصفر.
- [x] إذا رجع الطرف المعدل بحالة question أو clarification تُعرض الحاجة للاستكمال؛ لا يُصطنع ترتيب نهائي ولا فرق نقاط قبل اكتمال الطرفين.
- [x] حفظ الأصل ونسخة معاينة منفصلة في الذاكرة؛ اعتماد النسخة فقط بزر صريح، واستكمال أسئلتها عبر advance عند الحاجة.
- [x] إظهار سبب التغيير بالاستناد إلى الشرط المعدل أو الإجابة وآثار القواعد، مع فصل السبب عن مقدار تغير الرتبة.
- [x] منع رد متأخر من استبدال معاينة أحدث باستخدام رقم طلب أو AbortController؛ الخطأ لا يمس الأصل.
- [x] تشغيل اختبارات السيناريو وواجهة الحالة، ثم اختبار الإلغاء والاعتماد والاستكمال وتغيير اللغة وحفظ commit.

## المهمة 6: خطة البداية — الميزة 4

**إنشاء:** `frontend/starter-guide.js`، `tests/frontend_starter_guide.test.cjs`.

**تعديل:** `frontend/app.js`، `frontend/index.html`، `frontend/styles.css`؛ الاستفادة من profile المترجم في المهمة 4.

**واجهة:** `renderStarterGuide(tool, language)` يُرجع DOM آمن لبيانات starter_guide، دون توليد محتوى جديد وقت الطلب.

- [x] اختبار ظهور المتطلبات و3–5 خطوات والمثال والمخرج المتوقع ومصادرها وتاريخ المراجعة.
- [x] إضافة زر «ابدأ بهذه الأداة» إلى كل نتيجة، وفتح قسم قابل للطي مع حالة aria-expanded وإعادة التركيز بصورة صحيحة.
- [x] استخدام اسم الأداة والمسار في العرض، وإظهار حدود الخطة المجانية أو المتطلبات ذات الصلة دون اختراع تخصيص لا تدعمه البيانات.
- [x] اختبار اللغتين والروابط وحقن HTML وغياب profile في البيانات القديمة؛ عند غيابها إظهار «الدليل غير متاح» دون كسر البطاقة.
- [x] تشغيل اختبارات المكون وقراءة المحتوى المعروض لعينة من كل مسار، ثم حفظ commit مستقل.

## المهمة 7: التحقق المتكامل والتوثيق

**تعديل:** `scripts/simulate_adaptive_questionnaire.py`، `tests/test_adaptive_simulation.py`، `tests/test_frontend_integration.py`، `.github/workflows/ci.yml`، `README.md`.

**إنشاء:** `docs/testing/decision-support-acceptance.md` لتسجيل الحالات والنتائج الفعلية.

- [x] الاحتفاظ بمحاكاة 250 جلسة دون شروط لاكتشاف تراجعات المسارات الحالية؛ إضافة مجموعة مستقلة للشروط تقبل 0–3 نتائج وتتحقق من أهلية كل نتيجة.
- [x] بناء حالات معلومة النتيجة: أداة عالية الدرجة تخالف شرطاً، قدرة مجهولة، تعارض شروط، أداة واحدة، تغير ترتيب، عدم تغيره، نسخة معرفة مختلفة، وفشل شبكة أثناء المعاينة.
- [x] اختبار رحلة كاملة في متصفح فعلي باللغتين وعلى شاشة هاتف وسطح مكتب، بما فيها التنقل بلوحة المفاتيح. ربطها آلياً بـCI إذا أضيف عدّاء متصفح للمشروع.
- [x] تحديث README لشرح صفر إلى ثلاث توصيات، معنى الرتبة والنسبة والثقة، حدود المجاني، ومعنى معاينة ماذا لو.
- [x] تشغيل الأوامر التالية من جذر المشروع بعد تفعيل البيئة، وتسجيل النتائج الفعلية دون نسخ نتائج جلسة سابقة:

```powershell
python -m pytest -q
node --test tests/*.test.cjs
python scripts/audit_phase6.py --knowledge data/knowledge/adaptive.json.gz
python -m compileall -q app scripts
python scripts/simulate_adaptive_questionnaire.py --sessions 250 --output output/research/adaptive-questionnaire-250-session-report.md
```

- [x] مراجعة الفرق النهائي للتأكد من أن كل شرط إلزامي مطبق على الخادم، وأن الأصل لا يتغير أثناء المعاينة، وأن كل خطة بداية ومقارنة تحمل مصادرها؛ حفظ commit التوثيق والتحقق.

## ترتيب التسليم ومعيار الاكتمال

1. المعرفة ثم الأهلية ثم واجهة الشروط: ميزة 5 قابلة للاستخدام.
2. المقارنة: ميزة 1 قابلة للاستخدام على النتائج المؤهلة.
3. السيناريوهات: ميزة 2 مع الإلغاء والاعتماد والاستكمال.
4. إظهار خطط البداية: ميزة 4 تستفيد من المحتوى الذي أُعد أولاً.
5. قبول الرحلة كاملة وتحديث التوثيق.

يكتمل العمل عندما تنجح الاختبارات الحالية والجديدة، وتُراجع بيانات الأدوات الـ48، ولا تُرشّح أداة تخالف شرطاً أو تفتقر لدليل استيفائه، ويعمل كل من المقارنة والمعاينة والدليل باللغتين وعلى الموبايل. تكلفة مراجعة المحتوى تعتمد على توفر المصادر؛ لا يُستبدل نقص الأدلة بتخمين لتسريع التسليم.

## مراجعة الخطة

- الميزات الأربع ممثلة في مهام ومعايير قبول محددة.
- التمييز بين أربع أدوات في الكتالوج وصفر إلى أربع أدوات مؤهلة يمنع كسر CLIPS والتدقيق الحالي.
- السيناريو لا يفرض نتيجة مكتملة عندما تستدعي الإجابات سؤالاً إضافياً.
- لا يتغير عقد التوصيات القديم ذو النتائج الثلاث.
- إصلاح عنوان API للنشر ملاحظة قائمة من المراجعة السابقة، ويتطلب معالجة قبل النشر العام؛ ليس شرطاً لتجربة هذه الدفعة محلياً على المنفذ 8000.

## سجل التنفيذ

أُنجزت المهام السبع بتاريخ 2026-09-05. تفاصيل النتائج وحدود الأدلة والتغييرات التنظيمية في [تقرير القبول](../../testing/decision-support-acceptance.md). جُمّعت التغييرات المترابطة في دفعات المعرفة والخادم والواجهة بعد التحقق المتكامل؛ اختبارات عرض المكونات نُفذت في متصفح فعلي بدلاً من محاكاة DOM في ملفات Node منفصلة.
