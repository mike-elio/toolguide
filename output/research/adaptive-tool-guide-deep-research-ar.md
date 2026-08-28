# دليل الأدوات الذكي: بحث عميق وتصميم قائم على الأدلة

**تاريخ المراجعة:** 28 أغسطس 2026
**النطاق:** أربع مراحل × ثلاثة مجالات × أربع أدوات = **48 أداة فريدة**
**المراحل:** التحليل، التصميم، التنفيذ، الاختبار
**المجالات:** البرمجيات، الذكاء الاصطناعي، الأمن السيبراني

## الخلاصة التنفيذية

التصميم الأنسب ليس استبياناً ثابتاً، ولا أسئلة يولدها نموذج لغوي أثناء التشغيل. الأنسب هو **محرك أسئلة تكيفي قائم على بنك أسئلة موثق ومسبق الكتابة**:

- يختار المستخدم المرحلة ثم المجال صراحة قبل بدء الأسئلة.
- يسأل النظام بين **6 و10 أسئلة** فقط.
- بعد كل إجابة، يعيد ترتيب الأدوات المرشحة ويختار السؤال التالي الأكثر قدرة على التمييز بينها.
- تتغير الأسئلة وترتيبها بين الجلسات من مجموعة مرشحة متقاربة في القيمة، مع منع التكرار والمحافظة على تغطية المحاور الضرورية.
- لا يولد Ollama الأسئلة ولا الحقائق. يقتصر دوره على **تصنيف إجابة النص القصير** إلى قيم معروفة في القواعد.
- كل سؤال وقاعدة وتوصية تحمل مصدرها، تاريخ مراجعتها، ودرجة قوة الدليل.

هذا الأسلوب مستند إلى مبادئ الاختبارات التكيفية: اختيار العنصر الأعلى معلومات، موازنة المحتوى، التحكم في تكرار العناصر، والتوقف عند بلوغ دقة كافية أو الحد الأعلى للأسئلة. راجع [مكونات الاختبار التكيفي](https://pmc.ncbi.nlm.nih.gov/articles/PMC5676016/)، و[المعلومات القصوى مع موازنة المحتوى والتحكم في التعرض](https://pmc.ncbi.nlm.nih.gov/articles/PMC5968224/)، و[دورة التقييم التكيفي لدى ETS](https://www.ets.org/Media/Research/pdf/CBT-2011.pdf).

## 1. سياسة الأدلة

| الطبقة | الاستخدام | أمثلة | ما لا يسمح به |
|---|---|---|---|
| A - مرجع معياري أو رسمي | صياغة محاور الأسئلة، إثبات قدرات المنتج وحدوده المعلنة | NIST، OWASP، W3C، ISO، وثائق المنتج | لا نستنتج رضا المستخدمين من وثائق البائع |
| B - مشروع وتقارير تقنية قابلة للفحص | النشاط، التكاملات، المشكلات المتكررة، حدود التنفيذ | GitHub repository، releases، issues، docs | لا نساوي عدد النجوم بجودة المنتج |
| C - خبرة مجتمع | كشف احتكاكات عملية وصياغة «متى قد لا تناسبك» | Reddit ومناقشات GitHub | لا تتحول تجربة واحدة إلى حقيقة عامة أو ادعاء قدرة |

**قاعدة الحسم:** ادعاءات الميزات تأتي من A أو B. تجارب Reddit وGitHub Issues تخفض الثقة أو تضيف تحذيراً فقط عندما تتكرر أو تتوافق مع قيد رسمي. كل دليل مجتمعي يظهر في البيانات بوصفه `anecdotal` وليس حقيقة قطعية.

## 2. مصادر محاور الأسئلة

الأسئلة لا تنسخ النصوص حرفياً؛ بل تُصاغ كمعايير قرار قصيرة مرتبطة بالمصدر الذي يثبت أهمية المعيار.

| المجال/المحور | مصادر مرجعية | أمثلة لما يقاس |
|---|---|---|
| جودة البرمجيات | [ISO/IEC 25010:2023](https://www.iso.org/standard/78176.html)، [NIST SSDF](https://csrc.nist.gov/pubs/sp/800/218/final) | الأداء، الاعتمادية، قابلية الصيانة، بيئة التطوير، ضوابط سلسلة التوريد |
| تجربة المستخدم | [WCAG 2.2](https://www.w3.org/TR/WCAG22/) | إمكانية الوصول، المنصة، دقة النموذج الأولي، التعاون والتسليم |
| مخاطر أنظمة AI | [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework)، [NIST AI RMF Playbook](https://www.nist.gov/itl/ai-risk-management-framework/nist-ai-rmf-playbook)، [OWASP GenAI](https://genai.owasp.org/llm-top-10/)، [MITRE ATLAS](https://atlas.mitre.org/) | الخصوصية، الاستضافة، التقييم، المراقبة، RAG والوكلاء، الهجمات الخاصة بالذكاء الاصطناعي |
| الأمن السيبراني | [NIST CSF 2.0](https://www.nist.gov/cyberframework)، [OWASP Threat Modeling](https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html)، [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/)، [OWASP WSTG](https://owasp.org/www-project-web-security-testing-guide/latest/) | نوع الأصل، سطح الهجوم، SDLC، الامتثال، أسلوب الاختبار، قابلية الاستغلال |

## 3. بنك الأسئلة والقواعد

### حجم مقترح قابل للتوسع

- **12 حوضاً**: مرحلة × مجال.
- **14 سؤالاً موثقاً في كل حوض** كبداية = **168 سؤالاً**، مع إمكانية زيادة أي حوض عند ظهور فجوة تغطية.
- لا يرى المستخدم سوى 6-10 أسئلة في الجلسة.
- ستة محاور أساسية في كل حوض، وثمانية أسئلة شرطية أو فاصلة بين الأدوات المتقاربة.
- نحو **450-600 مجموعة قواعد** كبداية، وليس رقماً ثابتاً؛ يزداد العدد عندما يثبت اختبار التغطية أن جواباً مهماً لا يغير النتيجة كما يجب.

### بنية السؤال الموثق

```text
id, stage, domain, prompt_ar, prompt_en, answer_type, options
dimension, eligibility_conditions, exclusion_conditions
source_urls, source_tier, evidence_note, reviewed_at
tool_impacts, confidence, fallback_question_id
```

### دورة القرار التكيفية

1. **التهيئة:** تحديد المرحلة والمجال، ثم تحميل أربع أدوات مرشحة فقط من الخانة المطابقة.
2. **الأساس:** أول سؤالين أو ثلاثة يثبتان نوع المهمة، المخرج المطلوب، والبيئة/البيانات.
3. **التحديث:** كل إجابة تضيف نقاط ملاءمة، نقاط استبعاد، ومستوى ثقة لكل أداة.
4. **اختيار التالي:** من الأسئلة المؤهلة غير المستخدمة، يحسب النظام قدرة كل سؤال على فصل المرشحين، مع موازنة محاور المحتوى.
5. **التنويع:** يختار من أفضل ثلاثة أسئلة متقاربة باستخدام بذرة جلسة؛ لذلك يتغير المسار بلا توليد عشوائي غير منضبط.
6. **التوقف:** بعد السؤال السادس، يتوقف إذا استقرت الأدوات الثلاث الأولى وكان هامش الثقة كافياً؛ وإلا يتابع حتى السؤال العاشر.
7. **الاحتياط:** إن لم يوجد سؤال فرعي صالح، يعود إلى سؤال عام موثق من المحور الأقل تغطية.

### قواعد تحقق إلزامية

- لا سؤال بلا مصدر وتاريخ مراجعة.
- لا فرع ميت ولا سؤال بلا إجابات صالحة.
- كل جواب يجب أن يؤثر في أداة واحدة على الأقل.
- كل أداة يجب أن تملك أدلة إيجابية، أدلة سلبية، وقاعدة تعارض واحدة على الأقل.
- لا تتكرر صياغة السؤال في الجلسة، ولا يتكرر المحور أكثر من مرتين قبل تغطية المحاور الأساسية.
- نتيجة النص القصير تحت عتبة الثقة لا تغيّر الترتيب مباشرة؛ تعرض سؤال توضيح من خيارات ثابتة.
- المصادر المتقادمة أو الروابط المعطلة تخفض الثقة وتمنع نشر ادعاء جديد.

## 4. مصفوفة الأدوات - 48 أداة

### مرحلة التحليل

#### مجال البرمجيات

| الأداة | أقوى ملاءمة | متى قد لا تناسبك | دليل أساسي |
|---|---|---|---|
| ChatGPT Deep Research | بحث متعدد المصادر وتقرير موثق مع مرونة عامة | عندما يجب أن تبقى كل البيانات محلية أو تحتاج سيراً بحثياً متخصصاً جداً | [OpenAI](https://openai.com/index/introducing-deep-research/) |
| Claude Research | تحليل طويل ومقارنة مصادر مع سياق واسع | عندما تكون تكاملاتك أو سياسات مؤسستك مبنية حصراً على منظومة أخرى | [Anthropic](https://support.claude.com/en/articles/11088861-use-research-on-claude) |
| Gemini Deep Research | البحث المرتبط بخدمات Google ومستندات المستخدم | عندما لا تستخدم منظومة Google أو تحتاج تحكماً دقيقاً بمصادر داخلية خاصة | [Google](https://support.google.com/gemini/answer/15719111) |
| Perplexity Research | اكتشاف سريع للمصادر وإجابات تتمحور حول الاستشهادات | عندما تحتاج تحليلاً داخلياً محلياً أو سير عمل أكاديمي منضبط بالكامل | [Perplexity](https://www.perplexity.ai/help-center/en/articles/13600190-what-s-new-in-advanced-deep-research) |

#### مجال الذكاء الاصطناعي

| الأداة | أقوى ملاءمة | متى قد لا تناسبك | دليل أساسي |
|---|---|---|---|
| Elicit | مراجعات أدبية واستخراج بيانات منظمة من الأوراق | البحث البرمجي العام أو المصادر غير الأكاديمية | [Elicit](https://elicit.com/) |
| Consensus | سؤال علمي مع تلخيص اتجاه الأدلة المنشورة | عندما تحتاج تحليلاً كاملاً للكود أو بيانات الشركة الداخلية | [Consensus](https://help.consensus.app/en/articles/12641232-research-agent) |
| NotebookLM | الاستدلال داخل مجموعة مصادر يرفعها المستخدم | اكتشاف الويب المفتوح بلا مجموعة مصادر منسقة؛ كما توجد تقارير مجتمعية متفرقة عن تفاوت الإسناد | [Google](https://support.google.com/notebooklm/answer/16215270)، [تجربة مجتمع](https://www.reddit.com/r/notebooklm/comments/1rhs7ac) |
| Scite | فحص كيفية استشهاد الأبحاث بنتيجة ما: دعم أو تعارض أو ذكر | ليس بديلاً عن مراجعة منهجية كاملة أو تحليل منتج برمجي | [Scite](https://scite.ai/) |

#### مجال الأمن السيبراني

| الأداة | أقوى ملاءمة | متى قد لا تناسبك | دليل أساسي |
|---|---|---|---|
| Microsoft Security Copilot | تحقيقات وملخصات أمنية ضمن منظومة Microsoft | بيئة غير Microsoft أو عندما لا تقبل المؤسسة حدود الذكاء الاصطناعي المعلنة | [Microsoft](https://learn.microsoft.com/en-us/copilot/security/responsible-ai-overview-security-copilot) |
| Google Threat Intelligence with Gemini | استخبارات تهديدات وربط مؤشرات وسياق عالمي | إذا كانت بياناتك وأدوات SOC خارج منظومة Google وتحتاج تكاملاً محلياً عميقاً | [Google Cloud](https://cloud.google.com/security/products/threat-intelligence) |
| CrowdStrike Charlotte AI | تسريع تحقيقات SOC على منصة Falcon | إذا لم تكن Falcon مركز العمليات أو تحتاج أداة مستقلة عن البائع | [CrowdStrike](https://www.crowdstrike.com/en-us/platform/charlotte-ai/) |
| SentinelOne Purple AI | استعلام وتحقيق باللغة الطبيعية داخل Singularity | إذا لم تستخدم SentinelOne أو لا تتحمل خصائص ناشئة؛ توجد تجارب مجتمع تصف تفاوت النضج | [SentinelOne](https://www.sentinelone.com/platform/purple/)، [تجربة مجتمع](https://www.reddit.com/r/SentinelOneXDR/comments/1k8qrec) |

### مرحلة التصميم

#### مجال البرمجيات

| الأداة | أقوى ملاءمة | متى قد لا تناسبك | دليل أساسي |
|---|---|---|---|
| Figma Make / AI | واجهات تعاونية ونماذج أولية قابلة للتعديل والتسليم | عندما تريد موقعاً منشوراً بالكامل بلا سير تصميم أو قيود منظومة Figma | [Figma](https://www.figma.com/make/) |
| Uizard | الانتقال السريع من فكرة أو رسم إلى واجهة أولية | التصميم عالي التخصيص أو نظام تصميم مؤسسي شديد الدقة | [Uizard](https://uizard.io/product/) |
| Framer AI | إنشاء موقع تفاعلي ونشره بسرعة | تطبيقات منطقية معقدة أو حاجة لتجنب الارتباط بالمنصة؛ المجتمع يذكر أن الناتج الأولي يحتاج تهذيباً | [Framer](https://www.framer.com/ai/)، [تجربة مجتمع](https://www.reddit.com/r/framer/comments/1vis0r4) |
| Whimsical AI | مخططات، تدفقات، وwireframes سريعة وتعاونية | نماذج مرئية عالية الدقة أو تسليم production UI | [Whimsical](https://whimsical.com/ai) |

#### مجال الذكاء الاصطناعي

| الأداة | أقوى ملاءمة | متى قد لا تناسبك | دليل أساسي |
|---|---|---|---|
| Adobe Firefly | أصول إبداعية ضمن سير Adobe مع تركيز على الاستخدام التجاري المسؤول | فريق لا يستخدم Adobe أو يحتاج نموذجاً محلياً مفتوحاً | [Adobe](https://business.adobe.com/products/firefly-business/firefly-ai-approach.html) |
| Canva Magic Studio | إنتاج سريع ومتعدد القنوات لفرق غير متخصصة | تحكم احترافي دقيق أو خط إنتاج برمجي قابل للنسخ | [Canva](https://www.canva.com/magic-studio/) |
| Midjourney | استكشاف بصري وصور مفاهيمية قوية | هوية تحتاج ضبطاً تكرارياً صارماً أو شروط استخدام غير مناسبة؛ راجع الشروط بدلاً من الاعتماد على نقاشات المجتمع | [Midjourney Terms](https://docs.midjourney.com/docs/terms-of-service)، [نقاش مجتمع](https://www.reddit.com/r/midjourney/comments/1e4bvvn) |
| OpenAI Image Generation | توليد وتحرير صور عبر واجهة API داخل منتج | عندما تحتاج نموذجاً محلياً أو سير تصميم بصري متخصصاً خارج API | [OpenAI](https://openai.com/index/image-generation-api/) |

#### مجال الأمن السيبراني

| الأداة | أقوى ملاءمة | متى قد لا تناسبك | دليل أساسي |
|---|---|---|---|
| IriusRisk | نمذجة تهديدات منظمة ومتصلة بـSDLC | مشروع صغير يحتاج رسماً خفيفاً ومجانياً فقط | [IriusRisk](https://www.iriusrisk.com/) |
| ThreatModeler | أتمتة نمذجة التهديدات لبيئات وهندسات واسعة | فريق يريد أداة مفتوحة بسيطة أو لا يملك نضج AppSec كافياً | [ThreatModeler](https://www.threatmodeler.ai/why-threatmodeler/ai-ml-threat-modeling) |
| Security Compass SD Elements | متطلبات أمنية ونمذجة تهديدات مرتبطة بالتطوير والامتثال | نموذج أولي صغير بلا متطلبات حوكمة أو تكامل مؤسسي | [Security Compass](https://www.securitycompass.com/platform/) |
| OWASP Threat Dragon | نمذجة تهديدات مفتوحة المصدر وقابلة للفحص | الأتمتة المؤسسية العميقة وإدارة برنامج واسع من النماذج | [GitHub](https://github.com/owasp/threat-dragon)، [OWASP](https://owasp.org/www-project-threat-dragon/) |

### مرحلة التنفيذ

#### مجال البرمجيات

| الأداة | أقوى ملاءمة | متى قد لا تناسبك | دليل أساسي |
|---|---|---|---|
| GitHub Copilot | إكمال، محادثة ووكلاء ضمن GitHub وIDE | مستودعات لا يسمح لها بسياسة الخدمة أو فرق لا تستخدم GitHub | [GitHub Docs](https://docs.github.com/en/copilot/get-started/what-is-github-copilot) |
| Cursor | تحرير وكيل واعٍ بالمستودع داخل IDE متكامل | بيئة تفرض IDE مختلفاً أو سياسات لا تسمح بإرسال السياق للخدمة | [Cursor Docs](https://cursor.com/docs)، [Security](https://prod.cursor.com/docs/agent/security) |
| Windsurf | سير agentic داخل IDE عبر Cascade | فريق مرتبط بأدوات تحرير أخرى أو يحتاج ضوابط مؤسسية غير متاحة في خطته | [Windsurf Docs](https://docs.windsurf.com/) |
| Claude Code | وكيل برمجي في الطرفية وتدفقات قابلة للبرمجة | مستخدم يريد واجهة IDE رسومية فقط أو لا يقبل صلاحيات وكيل الطرفية | [Anthropic Docs](https://code.claude.com/docs/en/how-claude-code-works) |

#### مجال الذكاء الاصطناعي

| الأداة | أقوى ملاءمة | متى قد لا تناسبك | دليل أساسي |
|---|---|---|---|
| Hugging Face | نماذج وبيانات وتطبيقات ومكتبات مفتوحة ضمن منظومة واحدة | فريق يريد خدمة مغلقة مُدارة بالكامل بلا تشغيل أو اختيار نماذج | [Hugging Face Hub](https://huggingface.co/docs/hub/index) |
| LangGraph | وكلاء ذوو حالة ومسارات طويلة وتحكم صريح | chatbot بسيط لا يحتاج graph أو persistence | [Docs](https://docs.langchain.com/oss/python/langgraph/overview)، [GitHub](https://github.com/langchain-ai/langgraph) |
| LlamaIndex | تطبيقات RAG ووكلاء تتمحور حول البيانات والفهرسة | مهمة لا تعتمد على معرفة خارجية أو تحتاج إطاراً أدنى حجماً | [LlamaIndex Docs](https://docs.llamaindex.ai/en/latest/understanding/agent/structured_output/) |
| CrewAI | فرق وكلاء مبنية على أدوار ومهام وتدفقات | عملية حتمية بسيطة أو حاجة لتحكم graph منخفض المستوى | [Docs](https://docs.crewai.com/index)، [GitHub](https://github.com/crewaiinc/crewai) |

#### مجال الأمن السيبراني

| الأداة | أقوى ملاءمة | متى قد لا تناسبك | دليل أساسي |
|---|---|---|---|
| Snyk Code / Agent Fix | SAST وإصلاحات مقترحة داخل سير المطور | إذا أردت محرك قواعد مفتوحاً بالكامل أو تغطية أمنية خارج نطاقه | [Snyk Code](https://docs.snyk.io/scan-with-snyk/snyk-code)، [Auto Fix](https://docs.snyk.io/scan-with-snyk/snyk-code/manage-code-vulnerabilities/fix-code-vulnerabilities-automatically) |
| Semgrep Assistant | قواعد قابلة للفحص مع مساعدة AI للفرز والإصلاح | فريق لا يريد إدارة قواعد أو يحتاج منصة أمن تطبيقات شاملة من بائع واحد | [Semgrep](https://semgrep.dev/blog/2024/the-tech-behind-semgrep-assistant/) |
| Aikido AutoFix | إصلاحات أمنية موحدة ضمن منصة AppSec للمطور | إذا كانت الدقة في تغييرات كبيرة تتطلب مراجعة بشرية عميقة؛ المجتمع يناقش حدود الإصلاح التلقائي | [Aikido](https://help.aikido.dev/aikido-autofix)، [نقاش مجتمع](https://www.reddit.com/r/cybersecurity/comments/1utspyr) |
| GitLab Duo Vulnerability Resolution | تحليل وإصلاح ثغرات داخل GitLab DevSecOps | مستودعات وخطوط CI خارج GitLab | [GitLab Docs](https://docs.gitlab.com/user/gitlab_duo/prompt_examples/analyze_vulnerabilities/) |

### مرحلة الاختبار

#### مجال البرمجيات

| الأداة | أقوى ملاءمة | متى قد لا تناسبك | دليل أساسي |
|---|---|---|---|
| Qodo | توليد اختبارات ومراجعة كود وPR ضمن سير المطور | فريق يريد أداة UI end-to-end بلا تركيز على الكود | [Qodo Testing](https://www.qodo.ai/solutions/testing/) |
| Diffblue Cover | توليد اختبارات وحدة Java آلياً | مشروع ليس Java أو يحتاج اختبارات سلوك end-to-end | [Diffblue Docs](https://cover-docs.diffblue.com/get-started/what-is-diffblue-cover) |
| Testim | أتمتة اختبارات واجهات ويب مدعومة بالذكاء الاصطناعي | اختبارات وحدة أو backend فقط، أو حاجة لإطار مفتوح بالكامل | [Testim](https://help.testim.io/docs/testim-automate) |
| mabl | اختبارات end-to-end وAPI مع توليد ومراقبة ضمن منصة مُدارة | فريق يريد تشغيل محلي خفيف أو تحكماً برمجياً منخفض المستوى فقط | [mabl](https://help.mabl.com/hc/en-us/articles/31649455424660-Create-tests-with-generative-AI) |

#### مجال الذكاء الاصطناعي

| الأداة | أقوى ملاءمة | متى قد لا تناسبك | دليل أساسي |
|---|---|---|---|
| LangSmith | تقييم ومراقبة تطبيقات LLM ووكلاء LangChain وما حولها | تطبيق بسيط بلا traces أو فريق يريد حزمة مفتوحة محلية بالكامل | [LangSmith](https://docs.langchain.com/langsmith/evaluation) |
| Arize Phoenix | observability وتقييم مفتوح المصدر لتطبيقات LLM | فريق يريد SaaS مغلقاً بلا تشغيل أو إعداد | [Docs](https://arize.com/docs/phoenix/evaluation/llm-evals)، [GitHub](https://github.com/arize-ai/phoenix) |
| DeepEval | اختبارات وتقييمات برمجية قابلة للدمج في CI | فريق غير برمجي يريد واجهة no-code فقط | [Docs](https://deepeval.com/docs/evaluation-end-to-end-llm-evals)، [GitHub](https://github.com/confident-ai/deepeval) |
| Giskard | مسح وتقييم مخاطر تطبيقات AI/LLM | فحص سريع جداً على بيئة محدودة؛ توجد تجربة مجتمع تشير إلى كلفة زمنية في بعض المسوح | [Docs](https://docs.giskard.ai/oss)، [GitHub](https://github.com/Giskard-AI/giskard-oss)، [تجربة مجتمع](https://www.reddit.com/r/LangChain/comments/1qw0mgk) |

#### مجال الأمن السيبراني

| الأداة | أقوى ملاءمة | متى قد لا تناسبك | دليل أساسي |
|---|---|---|---|
| Burp Suite AI / Burp Suite DAST | اختبار تطبيقات الويب اليدوي والمتقدم مع أتمتة | فرق تريد خدمة DAST مُدارة بالكامل بلا خبرة أمن ويب | [PortSwigger AI](https://portswigger.net/burp/documentation/desktop/burp-ai)، [Burp Suite DAST](https://portswigger.net/burp/burp-at) |
| Invicti | DAST مؤسسي واكتشاف أصول وتكاملات واسعة | مشروع صغير يحتاج اختباراً يدوياً منخفض الكلفة فقط | [Invicti](https://www.invicti.com/platform-overview) |
| StackHawk | DAST موجه للمطور وCI/CD وواجهات API | اختبار اختراق يدوي عميق أو تطبيق خارج سير DevOps | [StackHawk](https://docs.stackhawk.com/getting-started/)، [Agentic guide](https://docs.stackhawk.com/ai-security/agentic-stackhawk-guide/) |
| Bright Security | DAST مبكر في SDLC واختبارات API مع تكاملات AI | فريق لا يملك تعريفات API أو يريد اختباراً يدوياً حصراً | [Bright](https://docs.brightsec.com/docs/introducing-to-bright)، [STAR](https://docs.brightsec.com/docs/star-faq) |

## 5. كيف تتحول الإجابات إلى نتيجة مفهومة

كل بطاقة نتيجة تعرض فقط:

1. **اسم الأداة ونسبة المطابقة**، مع وسم المجال.
2. **لماذا اخترناها لك:** سببان أو ثلاثة مقتبسان من إجابات المستخدم بصياغة قصيرة.
3. **قد لا تناسبك إذا:** تحذير واحد أو اثنان مستندان إلى تعارض في الإجابات أو قيد موثق.
4. **الدليل:** رابط رسمي رئيسي، مع رابط مجتمع اختياري ظاهر بوسم «تجربة مجتمع».

مثال مختصر:

> **LangGraph - مطابقة 89%**
> اخترناه لأنك تحتاج وكيلًا متعدد الخطوات مع حالة مستمرة وتحكم صريح بالمسار.
> قد لا يناسبك إذا كان المطلوب chatbot بسيطاً بلا ذاكرة أو تفرعات.
> الدليل: وثائق رسمية + مستودع GitHub نشط.

النسبة ليست احتمالاً علمياً. هي **درجة ملاءمة داخل الأدوات الأربع المرشحة**، وتعرض معها ثقة مستقلة: عالية، متوسطة، أو منخفضة.

## 6. إصلاح الخطأ الحالي في السؤال النصي

رسالة `short text could not be resolved for question: design-q4` تعني أن مصنف النص لم يجد نية معروفة بدرجة ثقة كافية. السلوك الصحيح في التصميم الجديد:

- لا يفشل الاستبيان ولا يظهر خطأ تقني للمستخدم.
- يعرض سؤال توضيح ثابتاً مثل: «هل المخرج واجهة تطبيق، موقع، أم أصل بصري؟»
- يحتفظ بالنص الأصلي كدليل شرح، لكن لا يضيف وزناً حتى تثبت الفئة.
- يسجل سبب عدم المطابقة ودرجة الثقة لمراجعة قاموس الأمثلة لاحقاً، من دون تدريب نموذج جديد.

## 7. متطلبات البيانات والتنفيذ لاحقاً

البيانات الحالية تحتاج توسيع نماذجها لتشمل:

- `domain`، `limitations`، `ai_capabilities`، `last_reviewed_at` للأدوات.
- `source_urls`، `source_tier`، `evidence_note` للأسئلة والقواعد.
- شروط الأهلية، الاستبعاد، التعارض، والأسئلة البديلة.
- جلسة تحفظ الإجابات، البذرة، الأسئلة المستخدمة، ترتيب الأدوات، والثقة بعد كل خطوة.
- اختبارات تغطية آلية للمصفوفة 4×3×4، واختبارات تمنع الفروع الميتة والمصادر المفقودة.

## 8. سياسة الحداثة والصيانة

- فحص الروابط تلقائياً في CI، مع مراجعة بشرية للمحتوى.
- تحذير عند مرور **180 يوماً** على المصدر دون مراجعة، وليس حذف الأداة آلياً.
- إعادة اعتماد الأداة سنوياً أو عند تغيير الاسم/الترخيص/المنتج.
- الأداة القديمة زمنياً تبقى فقط إذا كانت نشطة ومعروفة وتملك دعماً حديثاً أو ميزات AI موثقة.
- GitHub activity إشارة صيانة وليست حكماً منفرداً على الجودة.
- إدخال ملاحظات Reddit/GitHub Issues بعد تكرار النمط أو توافقه مع قيد رسمي، مع وسمها كتجربة مجتمع.

## 9. قرار التصميم المطلوب قبل البرمجة

التوصية النهائية هي اعتماد **محرك تكيفي محسوب** ببنك أسئلة موثق مسبقاً، 168 سؤالاً كبداية، 450-600 مجموعة قواعد قابلة للزيادة حسب اختبار التغطية، و48 أداة فريدة. يولّد التنويع ترتيباً مختلفاً بين الجلسات، بينما تبقى صياغة كل سؤال ودليله ثابتين وقابلين للمراجعة.

بعد الموافقة على هذا التصميم، الخطوة الصحيحة التالية هي كتابة مواصفة تنفيذية دقيقة ثم خطة تغيير واختبارات، قبل تعديل الكود أو البيانات.
