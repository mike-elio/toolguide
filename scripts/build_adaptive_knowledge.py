from __future__ import annotations

import gzip
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from app.domain.models import (
    AnswerOption,
    DomainId,
    EvaluationSource,
    Language,
    LocalizedText,
    Question,
    QuestionType,
    Rule,
    RuleImpact,
    SourceKind,
    Stage,
    StageId,
    TextIntent,
    Tool,
)
from app.knowledge import KnowledgeSnapshot


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "knowledge" / "adaptive.json.gz"
REVIEWED_AT = date(2026, 8, 28)


def lt(en: str, ar: str) -> LocalizedText:
    return LocalizedText(en=en, ar=ar)


@dataclass(frozen=True)
class ToolSpec:
    stage: StageId
    domain: DomainId
    id: str
    name: str
    best_en: str
    best_ar: str
    limit_en: str
    limit_ar: str
    url: str
    strengths: tuple[str, ...]


@dataclass(frozen=True)
class OptionSpec:
    id: str
    en: str
    ar: str
    signals: tuple[str, ...]


@dataclass(frozen=True)
class QuestionSpec:
    dimension: str
    en: str
    ar: str
    options: tuple[OptionSpec, OptionSpec, OptionSpec]
    question_type: QuestionType = QuestionType.SINGLE_CHOICE


def tool(
    stage: StageId,
    domain: DomainId,
    id: str,
    name: str,
    best_en: str,
    best_ar: str,
    limit_en: str,
    limit_ar: str,
    url: str,
    *strengths: str,
) -> ToolSpec:
    return ToolSpec(
        stage, domain, id, name, best_en, best_ar, limit_en, limit_ar, url, strengths
    )


TOOL_SPECS = (
    tool(StageId.ANALYSIS, DomainId.SOFTWARE, "chatgpt-deep-research", "ChatGPT Deep Research", "Flexible multi-source research and structured reports.", "بحث مرن متعدد المصادر وتقارير منظمة.", "Not ideal when every source and datum must remain local.", "قد لا يناسبك عندما يجب أن تبقى كل المصادر والبيانات محلية.", "https://openai.com/index/introducing-deep-research/", "deep", "citations", "general", "report", "web"),
    tool(StageId.ANALYSIS, DomainId.SOFTWARE, "claude-research", "Claude Research", "Long-context analysis and careful source comparison.", "تحليل طويل السياق ومقارنة دقيقة للمصادر.", "Less suitable when the organization is standardized on another ecosystem.", "أقل ملاءمة عندما تعتمد المؤسسة منظومة أخرى حصراً.", "https://support.claude.com/en/articles/11088861-use-research-on-claude", "deep", "long_context", "documents", "report", "governance"),
    tool(StageId.ANALYSIS, DomainId.SOFTWARE, "gemini-deep-research", "Gemini Deep Research", "Research connected to Google services and user documents.", "بحث متصل بخدمات غوغل ومستندات المستخدم.", "Weaker fit when Google integrations are not part of the workflow.", "أقل ملاءمة عندما لا تدخل تكاملات غوغل في سير العمل.", "https://support.google.com/gemini/answer/15719111", "workspace", "documents", "web", "collaboration", "fast"),
    tool(StageId.ANALYSIS, DomainId.SOFTWARE, "perplexity-research", "Perplexity Research", "Fast source discovery and citation-centered answers.", "اكتشاف سريع للمصادر وإجابات تتمحور حول الاستشهادات.", "Not a replacement for a fully controlled internal or academic review.", "ليس بديلاً عن مراجعة داخلية أو أكاديمية مضبوطة بالكامل.", "https://www.perplexity.ai/help-center/en/articles/13600190-what-s-new-in-advanced-deep-research", "fast", "citations", "web", "discovery", "current"),
    tool(StageId.ANALYSIS, DomainId.ARTIFICIAL_INTELLIGENCE, "elicit", "Elicit", "Structured literature review and extraction from papers.", "مراجعة أدبية منظمة واستخراج من الأوراق.", "Not intended for general code or non-academic source analysis.", "غير مخصص لتحليل الكود العام أو المصادر غير الأكاديمية.", "https://elicit.com/", "academic", "deep", "structured", "citations", "documents"),
    tool(StageId.ANALYSIS, DomainId.ARTIFICIAL_INTELLIGENCE, "consensus", "Consensus", "Summarizing the direction of published scientific evidence.", "تلخيص اتجاه الأدلة العلمية المنشورة.", "Not suitable for private company data or repository analysis.", "لا يناسب بيانات الشركة الخاصة أو تحليل المستودعات.", "https://help.consensus.app/en/articles/12641232-research-agent", "academic", "citations", "summary", "fast", "evidence"),
    tool(StageId.ANALYSIS, DomainId.ARTIFICIAL_INTELLIGENCE, "notebooklm", "NotebookLM", "Grounded analysis inside a user-supplied source collection.", "تحليل مؤسس على مجموعة مصادر يرفعها المستخدم.", "Weak fit for open-web discovery without a curated source set.", "أقل ملاءمة لاكتشاف الويب المفتوح بلا مجموعة مصادر منسقة.", "https://support.google.com/notebooklm/answer/16215270", "documents", "grounded", "workspace", "summary", "collaboration"),
    tool(StageId.ANALYSIS, DomainId.ARTIFICIAL_INTELLIGENCE, "scite", "Scite", "Checking whether research citations support, contrast, or mention a claim.", "فحص ما إذا كانت الاستشهادات تدعم الادعاء أو تعارضه أو تذكره.", "Not a complete systematic-review or product-analysis platform.", "ليس منصة كاملة للمراجعة المنهجية أو تحليل المنتجات.", "https://scite.ai/", "academic", "validation", "citations", "evidence", "deep"),
    tool(StageId.ANALYSIS, DomainId.CYBERSECURITY, "microsoft-security-copilot", "Microsoft Security Copilot", "Security investigation and summaries in the Microsoft ecosystem.", "تحقيقات وملخصات أمنية ضمن منظومة مايكروسوفت.", "A poor fit for environments centered on non-Microsoft security stacks.", "لا يناسب البيئات التي تتمحور حول حزم أمنية غير مايكروسوفت.", "https://learn.microsoft.com/en-us/copilot/security/responsible-ai-overview-security-copilot", "enterprise", "soc", "workspace", "automation", "governance"),
    tool(StageId.ANALYSIS, DomainId.CYBERSECURITY, "google-threat-intelligence", "Google Threat Intelligence", "Threat intelligence and indicator context at global scale.", "استخبارات تهديدات وربط المؤشرات بسياق عالمي.", "Less useful when the SOC and telemetry are outside Google's ecosystem.", "أقل فائدة عندما يكون مركز العمليات والقياس خارج منظومة غوغل.", "https://cloud.google.com/security/products/threat-intelligence", "threat_intel", "current", "web", "scale", "soc"),
    tool(StageId.ANALYSIS, DomainId.CYBERSECURITY, "crowdstrike-charlotte-ai", "CrowdStrike Charlotte AI", "Accelerating SOC investigations on the Falcon platform.", "تسريع تحقيقات مركز العمليات على منصة فالكون.", "Not appropriate when Falcon is not the operational center.", "لا يناسبك عندما لا تكون فالكون مركز العمليات.", "https://www.crowdstrike.com/en-us/platform/charlotte-ai/", "soc", "automation", "enterprise", "monitoring", "fast"),
    tool(StageId.ANALYSIS, DomainId.CYBERSECURITY, "sentinelone-purple-ai", "SentinelOne Purple AI", "Natural-language investigation in SentinelOne Singularity.", "تحقيق واستعلام باللغة الطبيعية داخل سينتينل ون.", "Not suitable without the SentinelOne platform or when emerging features are unacceptable.", "لا يناسبك من دون منصة سينتينل ون أو عند رفض الميزات الناشئة.", "https://www.sentinelone.com/platform/purple/", "soc", "natural_language", "automation", "monitoring", "fast"),

    tool(StageId.DESIGN, DomainId.SOFTWARE, "figma-make", "Figma Make / AI", "Collaborative interfaces, editable prototypes, and handoff.", "واجهات تعاونية ونماذج قابلة للتعديل والتسليم.", "Not the simplest route when only a published site is required.", "ليس الطريق الأبسط عندما يكون المطلوب موقعاً منشوراً فقط.", "https://www.figma.com/make/", "collaboration", "prototype", "handoff", "design_system", "visual"),
    tool(StageId.DESIGN, DomainId.SOFTWARE, "uizard", "Uizard", "Fast movement from an idea or sketch to an interface concept.", "انتقال سريع من فكرة أو رسم إلى مفهوم واجهة.", "Less suitable for a highly controlled enterprise design system.", "أقل ملاءمة لنظام تصميم مؤسسي شديد الضبط.", "https://uizard.io/product/", "fast", "prototype", "low_code", "visual", "iteration"),
    tool(StageId.DESIGN, DomainId.SOFTWARE, "framer-ai", "Framer AI", "Rapid interactive website creation and publishing.", "إنشاء موقع تفاعلي ونشره بسرعة.", "Not ideal for complex application logic or avoiding platform lock-in.", "لا يناسب منطق التطبيقات المعقد أو تجنب الارتباط بالمنصة.", "https://www.framer.com/ai/", "web", "publish", "prototype", "visual", "fast"),
    tool(StageId.DESIGN, DomainId.SOFTWARE, "whimsical-ai", "Whimsical AI", "Fast flows, diagrams, wireframes, and team ideation.", "تدفقات ومخططات وواجهات هيكلية سريعة للفريق.", "Not intended for high-fidelity production interface handoff.", "غير مخصص لتسليم واجهة إنتاجية عالية الدقة.", "https://whimsical.com/ai", "diagram", "wireframe", "collaboration", "fast", "planning"),
    tool(StageId.DESIGN, DomainId.ARTIFICIAL_INTELLIGENCE, "adobe-firefly", "Adobe Firefly", "Creative assets in Adobe workflows with commercial-use controls.", "أصول إبداعية ضمن سير أدوبي وضوابط للاستخدام التجاري.", "Less suitable for teams outside Adobe or requiring a local open model.", "أقل ملاءمة خارج أدوبي أو عند الحاجة إلى نموذج محلي مفتوح.", "https://business.adobe.com/products/firefly-business/firefly-ai-approach.html", "commercial", "enterprise", "visual", "editing", "governance"),
    tool(StageId.DESIGN, DomainId.ARTIFICIAL_INTELLIGENCE, "canva-magic-studio", "Canva Magic Studio", "Fast multi-channel production for non-specialist teams.", "إنتاج سريع متعدد القنوات لفرق غير متخصصة.", "Not ideal for exact professional control or a reproducible code pipeline.", "لا يناسب التحكم الاحترافي الدقيق أو خط إنتاج برمجي قابل للتكرار.", "https://www.canva.com/magic-studio/", "fast", "collaboration", "templates", "visual", "low_code"),
    tool(StageId.DESIGN, DomainId.ARTIFICIAL_INTELLIGENCE, "midjourney", "Midjourney", "Strong visual exploration and concept imagery.", "استكشاف بصري قوي وصور مفاهيمية.", "Not ideal for strict iterative identity control or incompatible usage terms.", "لا يناسب هوية تحتاج ضبطاً تكرارياً صارماً أو شروط استخدام مختلفة.", "https://docs.midjourney.com/docs/terms-of-service", "visual", "concept", "creative", "quality", "exploration"),
    tool(StageId.DESIGN, DomainId.ARTIFICIAL_INTELLIGENCE, "openai-image-generation", "OpenAI Image Generation", "Image generation and editing through a product API.", "توليد وتحرير الصور عبر واجهة برمجية داخل المنتج.", "Not suitable when a local model or specialist visual workflow is mandatory.", "لا يناسبك عند إلزام نموذج محلي أو سير بصري متخصص.", "https://openai.com/index/image-generation-api/", "api", "editing", "automation", "product", "visual"),
    tool(StageId.DESIGN, DomainId.CYBERSECURITY, "iriusrisk", "IriusRisk", "Structured threat modeling connected to the SDLC.", "نمذجة تهديدات منظمة ومتصلة بدورة التطوير.", "May be excessive for a tiny project needing only a lightweight diagram.", "قد يكون زائداً لمشروع صغير يحتاج مخططاً خفيفاً فقط.", "https://www.iriusrisk.com/", "threat_model", "enterprise", "automation", "governance", "integration"),
    tool(StageId.DESIGN, DomainId.CYBERSECURITY, "threatmodeler", "ThreatModeler", "Automated threat modeling for broad architectures.", "نمذجة تهديدات مؤتمتة لهندسات واسعة.", "Not the best fit for teams wanting a simple open-source tool.", "لا يناسب فريقاً يريد أداة مفتوحة وبسيطة.", "https://www.threatmodeler.ai/why-threatmodeler/ai-ml-threat-modeling", "threat_model", "automation", "scale", "enterprise", "cloud"),
    tool(StageId.DESIGN, DomainId.CYBERSECURITY, "sd-elements", "Security Compass SD Elements", "Security requirements tied to development and compliance.", "متطلبات أمنية مرتبطة بالتطوير والامتثال.", "Too heavy for a prototype without governance or enterprise integration needs.", "ثقيل على نموذج أولي بلا حوكمة أو تكامل مؤسسي.", "https://www.securitycompass.com/platform/", "requirements", "compliance", "governance", "enterprise", "integration"),
    tool(StageId.DESIGN, DomainId.CYBERSECURITY, "owasp-threat-dragon", "OWASP Threat Dragon", "Open-source and inspectable threat-model diagrams.", "مخططات نمذجة تهديدات مفتوحة وقابلة للفحص.", "Limited for deep enterprise automation and portfolio management.", "محدود للأتمتة المؤسسية العميقة وإدارة المحافظ.", "https://github.com/owasp/threat-dragon", "open_source", "diagram", "local", "threat_model", "lightweight"),

    tool(StageId.IMPLEMENTATION, DomainId.SOFTWARE, "github-copilot", "GitHub Copilot", "Code completion, chat, and agents in GitHub and IDE workflows.", "إكمال ومحادثة ووكلاء ضمن غيت هب وبيئات التطوير.", "Not suitable when repository policy forbids the service or GitHub is absent.", "لا يناسب سياسة تمنع الخدمة أو فريقاً لا يستخدم غيت هب.", "https://docs.github.com/en/copilot/get-started/what-is-github-copilot", "ide", "repository", "collaboration", "automation", "enterprise"),
    tool(StageId.IMPLEMENTATION, DomainId.SOFTWARE, "cursor", "Cursor", "Repository-aware agentic editing in an integrated IDE.", "تحرير وكيل واع بالمستودع داخل بيئة متكاملة.", "Not suitable when another IDE is mandatory or context cannot leave the device.", "لا يناسب فرض محرر آخر أو منع خروج سياق المستودع.", "https://cursor.com/docs", "ide", "repository", "agent", "fast", "code"),
    tool(StageId.IMPLEMENTATION, DomainId.SOFTWARE, "windsurf", "Windsurf", "Agentic coding workflows through Cascade in the editor.", "سير برمجي وكيل عبر كاسكيد داخل المحرر.", "Less suitable for teams locked to other editors or missing required controls.", "أقل ملاءمة لفريق مرتبط بمحرر آخر أو ضوابط غير متاحة.", "https://docs.windsurf.com/", "ide", "agent", "automation", "code", "iteration"),
    tool(StageId.IMPLEMENTATION, DomainId.SOFTWARE, "claude-code", "Claude Code", "Terminal-based coding agent and scriptable workflows.", "وكيل برمجي في الطرفية وتدفقات قابلة للبرمجة.", "Not ideal for users wanting only a graphical IDE or refusing terminal permissions.", "لا يناسب من يريد واجهة رسومية فقط أو يرفض صلاحيات الطرفية.", "https://code.claude.com/docs/en/how-claude-code-works", "terminal", "agent", "automation", "deep", "repository"),
    tool(StageId.IMPLEMENTATION, DomainId.ARTIFICIAL_INTELLIGENCE, "hugging-face", "Hugging Face", "Open models, datasets, applications, and libraries in one ecosystem.", "نماذج وبيانات وتطبيقات ومكتبات مفتوحة في منظومة واحدة.", "Not ideal when a fully managed closed service with no model operations is desired.", "لا يناسب من يريد خدمة مغلقة ومدارة بلا تشغيل نماذج.", "https://huggingface.co/docs/hub/index", "open_source", "models", "datasets", "local", "community"),
    tool(StageId.IMPLEMENTATION, DomainId.ARTIFICIAL_INTELLIGENCE, "langgraph", "LangGraph", "Stateful agents, long-running flows, and explicit control.", "وكلاء ذوو حالة ومسارات طويلة وتحكم صريح.", "Overkill for a simple chatbot without memory or branching.", "زائد لمحادثة بسيطة بلا ذاكرة أو تفرعات.", "https://github.com/langchain-ai/langgraph", "agent", "state", "workflow", "control", "open_source"),
    tool(StageId.IMPLEMENTATION, DomainId.ARTIFICIAL_INTELLIGENCE, "llamaindex", "LlamaIndex", "Data-centric RAG and agent applications.", "تطبيقات استرجاع ووكلاء تتمحور حول البيانات.", "Less useful when no external knowledge is needed or a smaller framework is preferred.", "أقل فائدة بلا معرفة خارجية أو عند تفضيل إطار أصغر.", "https://docs.llamaindex.ai/en/latest/understanding/agent/structured_output/", "rag", "data", "documents", "agent", "integration"),
    tool(StageId.IMPLEMENTATION, DomainId.ARTIFICIAL_INTELLIGENCE, "crewai", "CrewAI", "Role-based multi-agent teams, tasks, and flows.", "فرق وكلاء مبنية على أدوار ومهام وتدفقات.", "Not ideal for deterministic simple processes or low-level graph control.", "لا يناسب عملية حتمية بسيطة أو تحكماً منخفض المستوى.", "https://github.com/crewaiinc/crewai", "agent", "multi_agent", "workflow", "automation", "roles"),
    tool(StageId.IMPLEMENTATION, DomainId.CYBERSECURITY, "snyk-code", "Snyk Code / Agent Fix", "SAST and suggested fixes inside developer workflows.", "تحليل ساكن وإصلاحات مقترحة داخل سير المطور.", "Not ideal when a fully open rule engine is required.", "لا يناسب عند اشتراط محرك قواعد مفتوح بالكامل.", "https://docs.snyk.io/scan-with-snyk/snyk-code", "sast", "fix", "ide", "integration", "enterprise"),
    tool(StageId.IMPLEMENTATION, DomainId.CYBERSECURITY, "semgrep-assistant", "Semgrep Assistant", "Inspectable rules with AI-assisted triage and fixes.", "قواعد قابلة للفحص مع مساعدة للفرز والإصلاح.", "Not ideal when the team refuses rule management or needs one broad platform.", "لا يناسب فريقاً يرفض إدارة القواعد أو يريد منصة شاملة واحدة.", "https://semgrep.dev/blog/2024/the-tech-behind-semgrep-assistant/", "sast", "rules", "open_source", "fix", "ci"),
    tool(StageId.IMPLEMENTATION, DomainId.CYBERSECURITY, "aikido-autofix", "Aikido AutoFix", "Unified security fixes in a developer-focused AppSec platform.", "إصلاحات أمنية موحدة ضمن منصة موجهة للمطور.", "Large changes still require deep human review.", "التغييرات الكبيرة ما زالت تحتاج مراجعة بشرية عميقة.", "https://help.aikido.dev/aikido-autofix", "fix", "appsec", "automation", "integration", "developer"),
    tool(StageId.IMPLEMENTATION, DomainId.CYBERSECURITY, "gitlab-duo-vulnerability", "GitLab Duo Vulnerability Resolution", "Vulnerability analysis and resolution inside GitLab DevSecOps.", "تحليل وإصلاح ثغرات داخل غيت لاب وديف سيك أوبس.", "Not suitable for repositories and CI pipelines outside GitLab.", "لا يناسب المستودعات وخطوط البناء خارج غيت لاب.", "https://docs.gitlab.com/user/gitlab_duo/prompt_examples/analyze_vulnerabilities/", "repository", "ci", "fix", "integration", "devsecops"),

    tool(StageId.TESTING, DomainId.SOFTWARE, "qodo", "Qodo", "Test generation and code/PR review in developer workflows.", "توليد اختبارات ومراجعة كود وطلبات دمج ضمن سير المطور.", "Not intended as a visual end-to-end UI testing platform.", "غير مخصص كمنصة اختبار واجهة شاملة بصرياً.", "https://www.qodo.ai/solutions/testing/", "code", "unit", "repository", "ci", "automation"),
    tool(StageId.TESTING, DomainId.SOFTWARE, "diffblue-cover", "Diffblue Cover", "Automated Java unit-test generation.", "توليد آلي لاختبارات وحدة جافا.", "Not suitable for non-Java projects or end-to-end behavior tests.", "لا يناسب المشاريع غير جافا أو اختبارات السلوك الشاملة.", "https://cover-docs.diffblue.com/get-started/what-is-diffblue-cover", "java", "unit", "automation", "code", "local"),
    tool(StageId.TESTING, DomainId.SOFTWARE, "testim", "Testim", "AI-assisted web interface test automation.", "أتمتة اختبارات واجهات الويب بمساعدة الذكاء الاصطناعي.", "Not suited to unit tests or backend-only systems.", "لا يناسب اختبارات الوحدة أو الأنظمة الخلفية فقط.", "https://help.testim.io/docs/testim-automate", "web", "e2e", "visual", "automation", "ui"),
    tool(StageId.TESTING, DomainId.SOFTWARE, "mabl", "mabl", "Managed end-to-end and API tests with generation and monitoring.", "اختبارات شاملة وواجهات برمجية مُدارة مع توليد ومراقبة.", "Not ideal for a lightweight local-only testing stack.", "لا يناسب حزمة اختبار خفيفة ومحلية فقط.", "https://help.mabl.com/hc/en-us/articles/31649455424660-Create-tests-with-generative-AI", "e2e", "api", "monitoring", "automation", "cloud"),
    tool(StageId.TESTING, DomainId.ARTIFICIAL_INTELLIGENCE, "langsmith", "LangSmith", "Evaluation and observability for LLM and agent applications.", "تقييم ومراقبة تطبيقات النماذج والوكلاء.", "Less suitable for simple apps without traces or teams requiring fully local open tooling.", "أقل ملاءمة لتطبيق بلا تتبع أو فريق يشترط أدوات محلية مفتوحة.", "https://docs.langchain.com/langsmith/evaluation", "evaluation", "tracing", "agent", "monitoring", "cloud"),
    tool(StageId.TESTING, DomainId.ARTIFICIAL_INTELLIGENCE, "arize-phoenix", "Arize Phoenix", "Open-source LLM observability and evaluation.", "مراقبة وتقييم مفتوح المصدر لتطبيقات النماذج.", "Requires setup when the team wants a closed managed service only.", "يحتاج إعداداً عندما يريد الفريق خدمة مغلقة ومدارة فقط.", "https://github.com/arize-ai/phoenix", "open_source", "evaluation", "tracing", "local", "monitoring"),
    tool(StageId.TESTING, DomainId.ARTIFICIAL_INTELLIGENCE, "deepeval", "DeepEval", "Code-first LLM tests and CI evaluation.", "اختبارات نماذج برمجية وتقييم قابل للدمج في البناء.", "Not ideal for a non-technical team wanting only no-code controls.", "لا يناسب فريقاً غير تقني يريد أدوات بلا كود فقط.", "https://github.com/confident-ai/deepeval", "evaluation", "code", "ci", "open_source", "metrics"),
    tool(StageId.TESTING, DomainId.ARTIFICIAL_INTELLIGENCE, "giskard", "Giskard", "Risk scanning and evaluation for AI and LLM applications.", "مسح مخاطر وتقييم لتطبيقات الذكاء الاصطناعي والنماذج.", "Some scans can be heavy for a time- or resource-constrained environment.", "قد تكون بعض المسوح ثقيلة في بيئة محدودة الوقت أو الموارد.", "https://github.com/Giskard-AI/giskard-oss", "risk", "evaluation", "security", "open_source", "governance"),
    tool(StageId.TESTING, DomainId.CYBERSECURITY, "burp-suite", "Burp Suite AI / DAST", "Advanced manual web testing with automation.", "اختبار ويب يدوي متقدم مع أتمتة.", "Not ideal for teams wanting a fully managed DAST service without web-security expertise.", "لا يناسب فريقاً يريد خدمة مُدارة بلا خبرة أمن ويب.", "https://portswigger.net/burp/documentation/desktop/burp-ai", "manual", "web", "dast", "security", "deep"),
    tool(StageId.TESTING, DomainId.CYBERSECURITY, "invicti", "Invicti", "Enterprise DAST, asset discovery, and broad integrations.", "اختبار ديناميكي مؤسسي واكتشاف أصول وتكاملات واسعة.", "May be excessive for a small project needing low-cost manual testing.", "قد يكون زائداً لمشروع صغير يحتاج اختباراً يدوياً منخفض الكلفة.", "https://www.invicti.com/platform-overview", "enterprise", "dast", "scale", "automation", "report"),
    tool(StageId.TESTING, DomainId.CYBERSECURITY, "stackhawk", "StackHawk", "Developer-focused DAST for CI/CD and APIs.", "اختبار ديناميكي موجه للمطور وخطوط البناء وواجهات البرمجة.", "Not a replacement for deep manual penetration testing.", "ليس بديلاً عن اختبار اختراق يدوي عميق.", "https://docs.stackhawk.com/getting-started/", "developer", "dast", "ci", "api", "automation"),
    tool(StageId.TESTING, DomainId.CYBERSECURITY, "bright-security", "Bright Security", "Early-SDLC DAST and API security testing.", "اختبار ديناميكي مبكر واختبار أمن واجهات البرمجة.", "Less suitable when API definitions are unavailable or testing is manual-only.", "أقل ملاءمة بلا تعريفات واجهات أو عند اشتراط اختبار يدوي فقط.", "https://docs.brightsec.com/docs/introducing-to-bright", "dast", "api", "ci", "developer", "automation"),
)


DOMAIN_LABELS = {
    DomainId.SOFTWARE: lt("software", "البرمجيات"),
    DomainId.ARTIFICIAL_INTELLIGENCE: lt("artificial intelligence", "الذكاء الاصطناعي"),
    DomainId.CYBERSECURITY: lt("cybersecurity", "الأمن السيبراني"),
}


def opt(id: str, en: str, ar: str, *signals: str) -> OptionSpec:
    return OptionSpec(id=id, en=en, ar=ar, signals=signals)


ANALYSIS_QUESTIONS = (
    QuestionSpec("outcome", "What is the primary outcome for the {domain} analysis?", "ما المخرج الأساسي المطلوب من تحليل {domain}؟", (opt("rapid-map", "Rapid landscape map", "خريطة سريعة للمشهد", "fast", "discovery", "web"), opt("deep-evidence", "Deep evidence synthesis", "توليف أدلة معمق", "deep", "evidence", "documents"), opt("decision-brief", "Decision-ready brief", "موجز جاهز للقرار", "report", "summary", "governance"))),
    QuestionSpec("source_scope", "Which source scope matters most for the {domain} analysis?", "ما نطاق المصادر الأهم لتحليل {domain}؟", (opt("open-web", "Open web and current sources", "الويب المفتوح والمصادر الحديثة", "web", "current", "discovery"), opt("owned-documents", "Supplied internal documents", "مستندات داخلية مقدمة", "documents", "grounded", "workspace"), opt("published-evidence", "Published research and standards", "أبحاث ومعايير منشورة", "academic", "citations", "evidence"))),
    QuestionSpec("freshness", "How fresh must the {domain} evidence be?", "ما درجة حداثة أدلة {domain} المطلوبة؟", (opt("latest", "Latest available signals", "أحدث الإشارات المتاحة", "current", "fast", "monitoring"), opt("established", "Established validated evidence", "أدلة راسخة ومتحقق منها", "validation", "deep", "governance"), opt("balanced", "A balance of current and established", "مزيج من الحديث والراسخ", "report", "evidence", "citations"))),
    QuestionSpec("traceability", "What traceability level is required for the {domain} analysis?", "ما مستوى قابلية التتبع المطلوب لتحليل {domain}؟", (opt("links", "Direct source links", "روابط مباشرة للمصادر", "citations", "web"), opt("claim-map", "Claim-to-evidence mapping", "ربط الادعاء بالدليل", "validation", "evidence", "deep"), opt("summary-only", "Concise summary is enough", "يكفي ملخص موجز", "summary", "fast"))),
    QuestionSpec("sensitivity", "What data sensitivity applies to the {domain} analysis?", "ما حساسية البيانات في تحليل {domain}؟", (opt("public", "Public information", "معلومات عامة", "web", "cloud", "fast"), opt("internal", "Internal business material", "مواد عمل داخلية", "documents", "workspace", "governance"), opt("regulated", "Regulated or security-sensitive", "منظمة أو حساسة أمنياً", "local", "enterprise", "governance"))),
    QuestionSpec("collaboration", "Who collaborates on the {domain} analysis?", "من سيتعاون على تحليل {domain}؟", (opt("solo", "One analyst", "محلل واحد", "fast", "lightweight"), opt("team", "A working team", "فريق عمل", "collaboration", "workspace"), opt("executive", "Analysts and decision makers", "محللون وصناع قرار", "report", "governance", "enterprise"))),
    QuestionSpec("integration", "Where must the {domain} analysis connect?", "أين يجب أن يتكامل تحليل {domain}؟", (opt("standalone", "Standalone research workspace", "مساحة بحث مستقلة", "web", "documents"), opt("productivity", "Productivity suite", "حزمة إنتاجية", "workspace", "collaboration", "integration"), opt("operational", "Operational platform or repository", "منصة تشغيلية أو مستودع", "repository", "soc", "automation"))),
    QuestionSpec("scale", "What is the scale of the {domain} analysis?", "ما حجم تحليل {domain}؟", (opt("single", "One question or artifact", "سؤال أو أصل واحد", "fast", "lightweight"), opt("project", "A complete project", "مشروع كامل", "deep", "documents", "workflow"), opt("portfolio", "Continuous portfolio or program", "محفظة أو برنامج مستمر", "scale", "enterprise", "monitoring"))),
    QuestionSpec("automation", "How automated should the {domain} analysis be?", "ما مقدار أتمتة تحليل {domain}؟", (opt("manual", "Analyst-controlled review", "مراجعة يتحكم بها المحلل", "manual", "validation", "deep"), opt("assisted", "AI-assisted workflow", "سير مدعوم بالذكاء الاصطناعي", "automation", "fast", "natural_language"), opt("continuous", "Continuous automated monitoring", "مراقبة مؤتمتة مستمرة", "monitoring", "automation", "soc"))),
    QuestionSpec("explainability", "How should the {domain} findings be explained?", "كيف يجب شرح نتائج {domain}؟", (opt("concise", "Short readable explanation", "شرح قصير وواضح", "summary", "report"), opt("detailed", "Detailed reasoning trail", "مسار استدلال مفصل", "deep", "long_context", "citations"), opt("structured", "Structured fields and comparisons", "حقول ومقارنات منظمة", "structured", "validation", "evidence"))),
    QuestionSpec("deployment", "Where may the {domain} analysis run?", "أين يمكن تشغيل تحليل {domain}؟", (opt("cloud", "Cloud service", "خدمة سحابية", "cloud", "web", "fast"), opt("hybrid", "Hybrid workspace", "مساحة هجينة", "workspace", "integration", "governance"), opt("local", "Local or controlled environment", "بيئة محلية أو مضبوطة", "local", "open_source", "security"))),
    QuestionSpec("budget", "Which cost model fits the {domain} analysis?", "ما نموذج التكلفة المناسب لتحليل {domain}؟", (opt("free-first", "Free or open-source first", "مجاني أو مفتوح أولاً", "open_source", "community", "lightweight"), opt("predictable", "Predictable team subscription", "اشتراك فريق متوقع", "workspace", "collaboration"), opt("enterprise", "Enterprise platform budget", "ميزانية منصة مؤسسية", "enterprise", "governance", "scale"))),
    QuestionSpec("governance", "What governance applies to the {domain} analysis?", "ما الحوكمة المطلوبة لتحليل {domain}؟", (opt("light", "Light review", "مراجعة خفيفة", "fast", "lightweight"), opt("policy", "Documented internal policy", "سياسة داخلية موثقة", "governance", "documents"), opt("formal", "Formal compliance and audit", "امتثال وتدقيق رسمي", "enterprise", "validation", "security"))),
    QuestionSpec("task_language", "Describe the dominant {domain} analysis task.", "صف المهمة الغالبة في تحليل {domain}.", (opt("discover", "Discover the landscape", "اكتشاف المشهد", "discovery", "web", "fast"), opt("validate", "Validate a claim or risk", "التحقق من ادعاء أو خطر", "validation", "evidence", "security"), opt("monitor", "Monitor change over time", "مراقبة التغير مع الزمن", "monitoring", "current", "automation")), QuestionType.SHORT_TEXT),
)


DESIGN_QUESTIONS = (
    QuestionSpec("artifact", "What {domain} design artifact is required?", "ما أصل تصميم {domain} المطلوب؟", (opt("concept", "Concept exploration", "استكشاف مفهوم", "concept", "creative", "fast"), opt("prototype", "Interactive prototype", "نموذج تفاعلي", "prototype", "visual", "iteration"), opt("model", "Structured model or diagram", "نموذج منظم أو مخطط", "diagram", "threat_model", "planning"))),
    QuestionSpec("fidelity", "What fidelity is needed for the {domain} design?", "ما دقة تصميم {domain} المطلوبة؟", (opt("low", "Low-fidelity structure", "بنية منخفضة الدقة", "wireframe", "diagram", "fast"), opt("high", "High-fidelity visual output", "مخرج بصري عالي الدقة", "visual", "quality", "editing"), opt("production", "Production-ready handoff", "تسليم جاهز للإنتاج", "handoff", "design_system", "integration"))),
    QuestionSpec("collaboration", "How will the team collaborate on the {domain} design?", "كيف سيتعاون الفريق على تصميم {domain}؟", (opt("solo", "Solo iteration", "تكرار فردي", "fast", "lightweight"), opt("live", "Live team collaboration", "تعاون فريق مباشر", "collaboration", "workspace"), opt("governed", "Reviewed and governed workflow", "سير مراجع ومحكوم", "governance", "enterprise"))),
    QuestionSpec("handoff", "How will the {domain} design be handed off?", "كيف سيسلّم تصميم {domain}؟", (opt("visual", "Visual reference", "مرجع بصري", "visual", "concept"), opt("editable", "Editable design source", "مصدر تصميم قابل للتعديل", "editing", "collaboration"), opt("integrated", "Integrated requirements or code", "متطلبات أو كود متكامل", "handoff", "integration", "requirements"))),
    QuestionSpec("iteration", "How quickly must the {domain} design iterate?", "ما سرعة تكرار تصميم {domain}؟", (opt("minutes", "First draft in minutes", "مسودة أولى خلال دقائق", "fast", "low_code"), opt("cycles", "Several review cycles", "دورات مراجعة متعددة", "iteration", "collaboration"), opt("controlled", "Controlled approved changes", "تغييرات مضبوطة ومعتمدة", "governance", "enterprise"))),
    QuestionSpec("consistency", "What consistency control matters for the {domain} design?", "ما ضبط الاتساق المهم لتصميم {domain}؟", (opt("flexible", "Flexible exploration", "استكشاف مرن", "creative", "concept"), opt("brand", "Brand or design-system consistency", "اتساق العلامة أو نظام التصميم", "design_system", "templates"), opt("policy", "Security or policy consistency", "اتساق أمني أو سياساتي", "governance", "requirements", "compliance"))),
    QuestionSpec("accessibility", "What accessibility expectation applies to the {domain} design?", "ما توقعات إمكانية الوصول في تصميم {domain}؟", (opt("basic", "Basic readable structure", "بنية مقروءة أساسية", "wireframe", "lightweight"), opt("wcag", "WCAG-oriented interface", "واجهة موجهة لمعيار إمكانية الوصول", "design_system", "validation"), opt("documented", "Documented enterprise controls", "ضوابط مؤسسية موثقة", "enterprise", "governance"))),
    QuestionSpec("automation", "What should AI automate in the {domain} design?", "ما الذي يجب أن يؤتمته الذكاء الاصطناعي في تصميم {domain}؟", (opt("ideation", "Ideation and variants", "الأفكار والبدائل", "creative", "concept"), opt("generation", "Generate the core artifact", "توليد الأصل الأساسي", "automation", "visual", "prototype"), opt("requirements", "Generate structured requirements", "توليد متطلبات منظمة", "requirements", "threat_model", "governance"))),
    QuestionSpec("deployment", "What happens after the {domain} design is approved?", "ماذا يحدث بعد اعتماد تصميم {domain}؟", (opt("present", "Present the concept", "عرض المفهوم", "report", "visual"), opt("publish", "Publish a live experience", "نشر تجربة حية", "publish", "web"), opt("integrate", "Feed development or governance", "تغذية التطوير أو الحوكمة", "handoff", "integration", "requirements"))),
    QuestionSpec("privacy", "What privacy boundary applies to the {domain} design?", "ما حدود الخصوصية في تصميم {domain}؟", (opt("public", "Public assets", "أصول عامة", "cloud", "visual"), opt("internal", "Internal team material", "مواد فريق داخلية", "workspace", "collaboration"), opt("controlled", "Controlled sensitive architecture", "هندسة حساسة ومضبوطة", "local", "security", "governance"))),
    QuestionSpec("licensing", "What usage rights matter for the {domain} design?", "ما حقوق الاستخدام المهمة لتصميم {domain}؟", (opt("exploration", "Internal exploration only", "استكشاف داخلي فقط", "concept", "fast"), opt("commercial", "Commercial production use", "استخدام إنتاجي تجاري", "commercial", "governance"), opt("open", "Open and inspectable artifacts", "أصول مفتوحة وقابلة للفحص", "open_source", "local"))),
    QuestionSpec("scale", "How many {domain} designs must be managed?", "كم تصميم {domain} يجب إدارته؟", (opt("one", "One focused artifact", "أصل مركز واحد", "lightweight", "fast"), opt("system", "A reusable system", "نظام قابل لإعادة الاستخدام", "design_system", "templates"), opt("portfolio", "An enterprise portfolio", "محفظة مؤسسية", "enterprise", "scale", "governance"))),
    QuestionSpec("integration", "Which ecosystem must the {domain} design use?", "أي منظومة يجب أن يستخدمها تصميم {domain}؟", (opt("standalone", "Standalone tool", "أداة مستقلة", "lightweight", "local"), opt("creative", "Creative workspace", "مساحة عمل إبداعية", "visual", "editing", "collaboration"), opt("sdlc", "Development or security lifecycle", "دورة التطوير أو الأمن", "integration", "requirements", "threat_model"))),
    QuestionSpec("design_intent", "Describe the dominant {domain} design intent.", "صف النية الغالبة لتصميم {domain}.", (opt("explore", "Explore visual directions", "استكشاف اتجاهات بصرية", "creative", "visual"), opt("prototype", "Prototype an experience", "نمذجة تجربة", "prototype", "iteration"), opt("secure", "Model risks and controls", "نمذجة المخاطر والضوابط", "threat_model", "security", "governance")), QuestionType.SHORT_TEXT),
)


IMPLEMENTATION_QUESTIONS = (
    QuestionSpec("work_type", "What is the main {domain} implementation work?", "ما عمل تنفيذ {domain} الأساسي؟", (opt("code", "Write and change code", "كتابة وتعديل الكود", "code", "ide", "repository"), opt("workflow", "Build an agent or workflow", "بناء وكيل أو سير", "agent", "workflow", "automation"), opt("security", "Integrate security controls", "دمج ضوابط أمنية", "security", "sast", "fix"))),
    QuestionSpec("interface", "Where should the {domain} implementation assistant work?", "أين يجب أن يعمل مساعد تنفيذ {domain}؟", (opt("ide", "Inside an IDE", "داخل بيئة تطوير", "ide", "code"), opt("terminal", "In the terminal", "في الطرفية", "terminal", "automation"), opt("platform", "Inside the repository platform", "داخل منصة المستودع", "repository", "ci", "integration"))),
    QuestionSpec("autonomy", "How autonomous may the {domain} implementation be?", "ما مستوى استقلال تنفيذ {domain}؟", (opt("suggest", "Suggest only", "اقتراح فقط", "code", "validation"), opt("edit", "Edit with review", "تعديل مع مراجعة", "ide", "agent", "fix"), opt("execute", "Execute multi-step tasks", "تنفيذ مهام متعددة الخطوات", "agent", "automation", "workflow"))),
    QuestionSpec("context", "What context must the {domain} implementation understand?", "ما السياق الذي يجب أن يفهمه تنفيذ {domain}؟", (opt("file", "Current file or prompt", "الملف أو الطلب الحالي", "fast", "code"), opt("repository", "A full repository", "مستودع كامل", "repository", "deep", "long_context"), opt("data", "Models, data, and documents", "نماذج وبيانات ومستندات", "data", "documents", "rag"))),
    QuestionSpec("architecture", "What architecture fits the {domain} implementation?", "ما الهندسة المناسبة لتنفيذ {domain}؟", (opt("simple", "Simple deterministic component", "مكون حتمي بسيط", "lightweight", "code"), opt("stateful", "Stateful controlled workflow", "سير ذو حالة ومضبوط", "state", "workflow", "control"), opt("multi_agent", "Role-based multi-agent system", "نظام متعدد الوكلاء قائم على الأدوار", "multi_agent", "roles", "agent"))),
    QuestionSpec("knowledge", "How does the {domain} implementation use external knowledge?", "كيف يستخدم تنفيذ {domain} معرفة خارجية؟", (opt("none", "No external knowledge", "لا معرفة خارجية", "code", "local"), opt("retrieval", "Retrieval over documents", "استرجاع من المستندات", "rag", "documents", "data"), opt("models", "Models and datasets ecosystem", "منظومة نماذج وبيانات", "models", "datasets", "open_source"))),
    QuestionSpec("privacy", "What privacy boundary applies to the {domain} implementation?", "ما حدود الخصوصية في تنفيذ {domain}؟", (opt("cloud", "Cloud processing is allowed", "المعالجة السحابية مسموحة", "cloud", "fast"), opt("controlled", "Controlled enterprise service", "خدمة مؤسسية مضبوطة", "enterprise", "governance"), opt("local", "Local or open-source operation", "تشغيل محلي أو مفتوح", "local", "open_source"))),
    QuestionSpec("integration", "Which {domain} integrations are mandatory?", "ما تكاملات {domain} الإلزامية؟", (opt("editor", "Editor integration", "تكامل المحرر", "ide", "developer"), opt("ci", "CI and repository integration", "تكامل البناء والمستودع", "ci", "repository"), opt("platform", "Application or data platform", "منصة تطبيق أو بيانات", "api", "integration", "data"))),
    QuestionSpec("security", "How should security affect the {domain} implementation?", "كيف يجب أن يؤثر الأمن في تنفيذ {domain}؟", (opt("review", "Human code review", "مراجعة كود بشرية", "validation", "code"), opt("scan", "Automated scanning", "فحص مؤتمت", "sast", "rules", "ci"), opt("fix", "Suggested or automated fixes", "إصلاحات مقترحة أو مؤتمتة", "fix", "automation", "appsec"))),
    QuestionSpec("team", "How does the team collaborate on the {domain} implementation?", "كيف يتعاون الفريق على تنفيذ {domain}؟", (opt("solo", "Solo developer", "مطور منفرد", "terminal", "lightweight"), opt("pull_request", "Pull-request workflow", "سير طلبات دمج", "repository", "collaboration", "ci"), opt("enterprise", "Governed enterprise team", "فريق مؤسسي محكوم", "enterprise", "governance", "integration"))),
    QuestionSpec("speed", "What speed-quality balance is needed for the {domain} implementation?", "ما توازن السرعة والجودة المطلوب لتنفيذ {domain}؟", (opt("rapid", "Rapid iteration", "تكرار سريع", "fast", "iteration"), opt("balanced", "Reviewable assisted changes", "تغييرات مدعومة وقابلة للمراجعة", "validation", "ide"), opt("controlled", "Deep controlled changes", "تغييرات عميقة ومضبوطة", "deep", "control", "governance"))),
    QuestionSpec("operations", "How will the {domain} implementation be operated?", "كيف سيشغّل تنفيذ {domain}؟", (opt("manual", "Developer-run", "يشغله المطور", "terminal", "local"), opt("pipeline", "Automated pipeline", "خط مؤتمت", "ci", "automation"), opt("service", "Long-running service", "خدمة طويلة التشغيل", "state", "monitoring", "scale"))),
    QuestionSpec("openness", "What ownership model fits the {domain} implementation?", "ما نموذج الملكية المناسب لتنفيذ {domain}؟", (opt("managed", "Managed commercial service", "خدمة تجارية مُدارة", "enterprise", "cloud"), opt("mixed", "Managed with inspectable components", "مُدارة مع مكونات قابلة للفحص", "integration", "governance"), opt("open", "Open-source and self-managed", "مفتوحة ومدارة ذاتياً", "open_source", "local", "community"))),
    QuestionSpec("implementation_intent", "Describe the dominant {domain} implementation intent.", "صف النية الغالبة لتنفيذ {domain}.", (opt("assist", "Assist a developer", "مساعدة مطور", "ide", "code"), opt("orchestrate", "Orchestrate models or agents", "تنسيق نماذج أو وكلاء", "agent", "workflow", "models"), opt("remediate", "Find and remediate weaknesses", "اكتشاف نقاط الضعف ومعالجتها", "security", "sast", "fix")), QuestionType.SHORT_TEXT),
)


TESTING_QUESTIONS = (
    QuestionSpec("target", "What must the {domain} testing validate?", "ما الذي يجب أن يتحقق منه اختبار {domain}؟", (opt("code", "Code-level behavior", "سلوك على مستوى الكود", "code", "unit"), opt("experience", "End-to-end experience", "تجربة شاملة", "e2e", "ui", "web"), opt("risk", "Security or model risk", "خطر أمني أو خطر نموذج", "security", "risk", "evaluation"))),
    QuestionSpec("automation", "How automated should the {domain} testing be?", "ما مقدار أتمتة اختبار {domain}؟", (opt("manual", "Expert-led manual testing", "اختبار يدوي يقوده خبير", "manual", "deep"), opt("generated", "AI-generated tests", "اختبارات مولدة بالذكاء الاصطناعي", "automation", "code"), opt("continuous", "Continuous pipeline testing", "اختبار مستمر في خط البناء", "ci", "monitoring", "automation"))),
    QuestionSpec("surface", "Which surface dominates the {domain} testing?", "أي سطح يهيمن على اختبار {domain}؟", (opt("unit", "Units and functions", "الوحدات والدوال", "unit", "code"), opt("web", "Web interface", "واجهة ويب", "web", "ui", "e2e"), opt("api", "APIs and services", "واجهات برمجية وخدمات", "api", "integration"))),
    QuestionSpec("language", "What technology constraint applies to the {domain} testing?", "ما قيد التقنية في اختبار {domain}؟", (opt("java", "Java codebase", "قاعدة كود جافا", "java", "unit"), opt("polyglot", "Multiple languages", "لغات متعددة", "code", "repository"), opt("no_code", "Low-code test authoring", "تأليف اختبار منخفض الكود", "low_code", "ui"))),
    QuestionSpec("environment", "Where must the {domain} testing run?", "أين يجب تشغيل اختبار {domain}؟", (opt("local", "Local or self-hosted", "محلي أو مستضاف ذاتياً", "local", "open_source"), opt("ci", "CI pipeline", "خط بناء", "ci", "repository"), opt("managed", "Managed cloud platform", "منصة سحابية مُدارة", "cloud", "enterprise"))),
    QuestionSpec("observability", "What observability is needed for the {domain} testing?", "ما قابلية المراقبة المطلوبة لاختبار {domain}؟", (opt("result", "Pass/fail result", "نتيجة نجاح أو فشل", "unit", "code"), opt("trace", "Detailed traces", "تتبعات مفصلة", "tracing", "deep"), opt("monitor", "Continuous monitoring", "مراقبة مستمرة", "monitoring", "scale"))),
    QuestionSpec("evaluation", "How should {domain} quality be measured?", "كيف يجب قياس جودة {domain}؟", (opt("assertions", "Deterministic assertions", "تأكيدات حتمية", "unit", "validation"), opt("metrics", "Evaluation metrics", "مقاييس تقييم", "metrics", "evaluation"), opt("risk_scan", "Risk and vulnerability scan", "مسح مخاطر وثغرات", "risk", "security", "dast"))),
    QuestionSpec("depth", "What depth is required for the {domain} testing?", "ما عمق اختبار {domain} المطلوب؟", (opt("smoke", "Fast smoke coverage", "تغطية دخانية سريعة", "fast", "ci"), opt("broad", "Broad automated coverage", "تغطية مؤتمتة واسعة", "automation", "scale"), opt("expert", "Deep expert investigation", "تحقيق خبير عميق", "manual", "deep", "security"))),
    QuestionSpec("remediation", "What should happen after a {domain} failure?", "ماذا يجب أن يحدث بعد فشل اختبار {domain}؟", (opt("report", "Report only", "تقرير فقط", "report", "validation"), opt("suggest", "Suggest a fix", "اقتراح إصلاح", "fix", "code"), opt("workflow", "Open a remediation workflow", "فتح سير معالجة", "integration", "ci", "appsec"))),
    QuestionSpec("team", "Who owns the {domain} testing?", "من يملك اختبار {domain}؟", (opt("developer", "Developers", "المطورون", "developer", "code"), opt("qa", "QA team", "فريق ضمان الجودة", "ui", "e2e", "collaboration"), opt("security", "Security or AI governance team", "فريق الأمن أو حوكمة الذكاء الاصطناعي", "security", "governance", "risk"))),
    QuestionSpec("scale", "What scale must the {domain} testing support?", "ما الحجم الذي يجب أن يدعمه اختبار {domain}؟", (opt("focused", "Focused component", "مكون مركز", "unit", "lightweight"), opt("application", "Complete application", "تطبيق كامل", "e2e", "integration"), opt("portfolio", "Enterprise portfolio", "محفظة مؤسسية", "enterprise", "scale", "monitoring"))),
    QuestionSpec("false_positives", "How costly are false positives in {domain} testing?", "ما كلفة الإيجابيات الكاذبة في اختبار {domain}؟", (opt("tolerable", "Tolerable during exploration", "مقبولة أثناء الاستكشاف", "fast", "automation"), opt("reviewed", "Human triage is available", "الفرز البشري متاح", "validation", "manual"), opt("critical", "Must be strongly verified", "يجب التحقق منها بقوة", "deep", "security", "governance"))),
    QuestionSpec("reporting", "What reporting is needed for the {domain} testing?", "ما التقارير المطلوبة لاختبار {domain}؟", (opt("developer", "Developer feedback", "ملاحظات للمطور", "developer", "ide"), opt("dashboard", "Operational dashboard", "لوحة تشغيلية", "monitoring", "tracing"), opt("audit", "Compliance-ready report", "تقرير جاهز للامتثال", "report", "enterprise", "governance"))),
    QuestionSpec("testing_intent", "Describe the dominant {domain} testing intent.", "صف النية الغالبة لاختبار {domain}.", (opt("prevent", "Prevent regressions", "منع التراجعات", "unit", "ci", "code"), opt("evaluate", "Evaluate model behavior", "تقييم سلوك النموذج", "evaluation", "metrics", "tracing"), opt("attack", "Find exploitable weaknesses", "اكتشاف نقاط ضعف قابلة للاستغلال", "security", "dast", "manual")), QuestionType.SHORT_TEXT),
)


STAGE_QUESTIONS = {
    StageId.ANALYSIS: ANALYSIS_QUESTIONS,
    StageId.DESIGN: DESIGN_QUESTIONS,
    StageId.IMPLEMENTATION: IMPLEMENTATION_QUESTIONS,
    StageId.TESTING: TESTING_QUESTIONS,
}


POOL_SOURCES = {
    (StageId.ANALYSIS, DomainId.SOFTWARE): ("iso-25010", "ISO/IEC 25010:2023", "ISO", "https://www.iso.org/standard/78176.html", SourceKind.OFFICIAL_DOCUMENTATION),
    (StageId.DESIGN, DomainId.SOFTWARE): ("wcag-22", "Web Content Accessibility Guidelines 2.2", "W3C", "https://www.w3.org/TR/WCAG22/", SourceKind.OFFICIAL_DOCUMENTATION),
    (StageId.IMPLEMENTATION, DomainId.SOFTWARE): ("nist-ssdf", "Secure Software Development Framework", "NIST", "https://csrc.nist.gov/pubs/sp/800/218/final", SourceKind.OFFICIAL_DOCUMENTATION),
    (StageId.TESTING, DomainId.SOFTWARE): ("iso-25010-testing", "ISO/IEC 25010:2023", "ISO", "https://www.iso.org/standard/78176.html", SourceKind.OFFICIAL_DOCUMENTATION),
    (StageId.ANALYSIS, DomainId.ARTIFICIAL_INTELLIGENCE): ("nist-ai-rmf", "AI Risk Management Framework", "NIST", "https://www.nist.gov/itl/ai-risk-management-framework", SourceKind.OFFICIAL_DOCUMENTATION),
    (StageId.DESIGN, DomainId.ARTIFICIAL_INTELLIGENCE): ("nist-ai-playbook", "AI RMF Playbook", "NIST", "https://www.nist.gov/itl/ai-risk-management-framework/nist-ai-rmf-playbook", SourceKind.OFFICIAL_DOCUMENTATION),
    (StageId.IMPLEMENTATION, DomainId.ARTIFICIAL_INTELLIGENCE): ("owasp-genai", "OWASP Top 10 for LLM Applications", "OWASP", "https://genai.owasp.org/llm-top-10/", SourceKind.OFFICIAL_DOCUMENTATION),
    (StageId.TESTING, DomainId.ARTIFICIAL_INTELLIGENCE): ("mitre-atlas", "MITRE ATLAS", "MITRE", "https://atlas.mitre.org/", SourceKind.OFFICIAL_DOCUMENTATION),
    (StageId.ANALYSIS, DomainId.CYBERSECURITY): ("nist-csf-20", "Cybersecurity Framework 2.0", "NIST", "https://www.nist.gov/cyberframework", SourceKind.OFFICIAL_DOCUMENTATION),
    (StageId.DESIGN, DomainId.CYBERSECURITY): ("owasp-threat-modeling", "Threat Modeling Cheat Sheet", "OWASP", "https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html", SourceKind.OFFICIAL_DOCUMENTATION),
    (StageId.IMPLEMENTATION, DomainId.CYBERSECURITY): ("nist-ssdf-cyber", "Secure Software Development Framework", "NIST", "https://csrc.nist.gov/pubs/sp/800/218/final", SourceKind.OFFICIAL_DOCUMENTATION),
    (StageId.TESTING, DomainId.CYBERSECURITY): ("owasp-wstg", "Web Security Testing Guide", "OWASP", "https://owasp.org/www-project-web-security-testing-guide/latest/", SourceKind.OFFICIAL_DOCUMENTATION),
}


def source_from_tuple(spec: tuple[str, str, str, str, SourceKind]) -> EvaluationSource:
    source_id, name, publisher, url, kind = spec
    return EvaluationSource(
        id=source_id,
        name=lt(name, name),
        publisher=lt(publisher, publisher),
        kind=kind,
        url=url,
        collected_at=REVIEWED_AT,
    )


def tool_source(spec: ToolSpec) -> EvaluationSource:
    return EvaluationSource(
        id=f"{spec.id}-official",
        name=lt(f"{spec.name} official source", f"المصدر الرسمي لأداة {spec.name}"),
        publisher=lt(spec.name, spec.name),
        kind=SourceKind.OFFICIAL_REPOSITORY if "github.com" in spec.url else SourceKind.VENDOR_DOCUMENTATION,
        url=spec.url,
        collected_at=REVIEWED_AT,
    )


def build_stages() -> list[Stage]:
    return [
        Stage(id=StageId.ANALYSIS, name=lt("Analysis", "التحليل")),
        Stage(id=StageId.DESIGN, name=lt("Design", "التصميم")),
        Stage(id=StageId.IMPLEMENTATION, name=lt("Implementation", "التنفيذ")),
        Stage(id=StageId.TESTING, name=lt("Testing", "الاختبار")),
    ]


def build_tools() -> list[Tool]:
    return [
        Tool(
            id=spec.id,
            name=lt(spec.name, spec.name),
            description=lt(spec.best_en, spec.best_ar),
            stages=[spec.stage],
            domain=spec.domain,
            best_for=lt(spec.best_en, spec.best_ar),
            limitations=[lt(spec.limit_en, spec.limit_ar)],
            source_url=spec.url,
            reviewed_at=REVIEWED_AT,
        )
        for spec in TOOL_SPECS
    ]


def question_id(stage: StageId, domain: DomainId, dimension: str) -> str:
    return f"{stage.value}-{domain.value}-{dimension}"


def build_questions() -> list[Question]:
    questions: list[Question] = []
    for stage, specs in STAGE_QUESTIONS.items():
        if len(specs) != 14:
            raise ValueError(f"{stage.value} must define exactly 14 question specs")
        for domain in DomainId:
            domain_label = DOMAIN_LABELS[domain]
            evidence = source_from_tuple(POOL_SOURCES[(stage, domain)])
            for spec in specs:
                kwargs: dict[str, object] = {}
                if spec.question_type is QuestionType.SHORT_TEXT:
                    kwargs["text_intents"] = [
                        TextIntent(
                            id=option.id,
                            label=lt(option.en, option.ar),
                            value=1.0,
                            aliases={
                                Language.ENGLISH: [option.en, option.id.replace("-", " ")],
                                Language.ARABIC: [option.ar],
                            },
                        )
                        for option in spec.options
                    ]
                else:
                    kwargs["options"] = [
                        AnswerOption(
                            id=option.id,
                            label=lt(option.en, option.ar),
                            value=1.0,
                        )
                        for option in spec.options
                    ]
                questions.append(
                    Question(
                        id=question_id(stage, domain, spec.dimension),
                        stage=stage,
                        domain=domain,
                        dimension=spec.dimension,
                        prompt=lt(
                            spec.en.format(domain=domain_label.en),
                            spec.ar.format(domain=domain_label.ar),
                        ),
                        type=spec.question_type,
                        importance=0.9 if spec.dimension in {"outcome", "artifact", "work_type", "target"} else 0.75,
                        sources=[evidence],
                        reviewed_at=REVIEWED_AT,
                        **kwargs,
                    )
                )
    return questions


def preference_order(
    option: OptionSpec, pool: tuple[ToolSpec, ...], tie_offset: int
) -> list[ToolSpec]:
    scored = []
    for index, candidate in enumerate(pool):
        overlap = len(set(option.signals) & set(candidate.strengths))
        tie_rank = (index - tie_offset) % len(pool)
        scored.append((overlap, -tie_rank, candidate))
    return [item[2] for item in sorted(scored, key=lambda item: (-item[0], -item[1], item[2].id))]


def build_rules() -> list[Rule]:
    pools = {
        (stage, domain): tuple(
            spec for spec in TOOL_SPECS if spec.stage is stage and spec.domain is domain
        )
        for stage in StageId
        for domain in DomainId
    }
    weights = (1.0, 0.55, -0.35, -0.75)
    rules: list[Rule] = []
    for stage, question_specs in STAGE_QUESTIONS.items():
        for domain in DomainId:
            pool = pools[(stage, domain)]
            if len(pool) != 4:
                raise ValueError(f"{stage.value}/{domain.value} must contain four tools")
            criterion_source = source_from_tuple(POOL_SOURCES[(stage, domain)])
            for question_index, question_spec in enumerate(question_specs):
                qid = question_id(stage, domain, question_spec.dimension)
                for option_index, option in enumerate(question_spec.options):
                    ordered = preference_order(
                        option, pool, tie_offset=(question_index + option_index) % 4
                    )
                    impacts = []
                    for rank, candidate in enumerate(ordered):
                        positive = weights[rank] > 0
                        rationale_en = (
                            f"{candidate.name} matches the selected {option.en.lower()} requirement."
                            if positive
                            else f"{candidate.name} is a weaker fit for the selected {option.en.lower()} requirement."
                        )
                        rationale_ar = (
                            f"تلائم أداة {candidate.name} متطلب «{option.ar}» المحدد."
                            if positive
                            else f"تعد أداة {candidate.name} أقل ملاءمة لمتطلب «{option.ar}» المحدد."
                        )
                        impacts.append(
                            RuleImpact(
                                tool_id=candidate.id,
                                weight=weights[rank],
                                rationale=lt(rationale_en, rationale_ar),
                                sources=[criterion_source, tool_source(candidate)],
                            )
                        )
                    rules.append(
                        Rule(
                            id=f"{qid}-{option.id}",
                            question_id=qid,
                            answer_option_id=option.id,
                            impacts=impacts,
                        )
                    )
    return rules


def build_snapshot() -> KnowledgeSnapshot:
    return KnowledgeSnapshot(
        stages=build_stages(),
        tools=build_tools(),
        questions=build_questions(),
        rules=build_rules(),
    )


def main(output: Path = DEFAULT_OUTPUT) -> int:
    snapshot = build_snapshot()
    output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(
        snapshot.model_dump(mode="json"), ensure_ascii=False, indent=2
    ).encode("utf-8")
    output.write_bytes(
        gzip.compress(serialized, compresslevel=9, mtime=0)
        if output.suffix == ".gz"
        else serialized
    )
    print(
        json.dumps(
            {
                "output": str(output),
                "tools": len(snapshot.tools),
                "questions": len(snapshot.questions),
                "rules": len(snapshot.rules),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
