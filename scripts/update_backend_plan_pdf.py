from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

import arabic_reshaper
from bidi.algorithm import get_display
from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = PROJECT_ROOT / "output" / "pdf" / "ai_expert_system_backend_plan_ar.pdf"
ARIAL = Path("C:/Windows/Fonts/arial.ttf")
ARIAL_BOLD = Path("C:/Windows/Fonts/arialbd.ttf")
PHASE_FOUR_MARKER = "/Phase4Appendix"
PHASE_FIVE_MARKER = "/Phase5Api"


def _rtl(text: str) -> str:
    return get_display(arabic_reshaper.reshape(text))


def _register_fonts() -> None:
    if not ARIAL.is_file() or not ARIAL_BOLD.is_file():
        raise FileNotFoundError("Arial Arabic fonts were not found in C:/Windows/Fonts")
    pdfmetrics.registerFont(TTFont("PlanArabic", ARIAL))
    pdfmetrics.registerFont(TTFont("PlanArabicBold", ARIAL_BOLD))


def _draw_phase_four_appendix(path: Path) -> None:
    _register_fonts()
    document = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    document.setFillColor(HexColor("#172033"))
    document.rect(0, 0, width, height, fill=1, stroke=0)
    document.setFillColor(HexColor("#67E8F9"))
    document.setFont("PlanArabicBold", 18)
    document.drawRightString(
        width - 48,
        height - 68,
        _rtl("ملحق تنفيذ المرحلة الرابعة - الترتيب والتفسير"),
    )

    arabic_lines = [
        "تم تنفيذ الترتيب خارج محرك CLIPS لضمان نتيجة مستقلة عن ترتيب الأجندة.",
        "تحسم الدرجة الأعلى الترتيب، ثم يحسم معرف الأداة التعادل تصاعديا.",
        "تُبنى أسباب الترشيح فقط من قيم التبرير المرتبطة بتأثيرات القواعد التي اشتغلت فعليا.",
        "يظهر أقوى عامل إيجابي وأقوى عامل سلبي ولا يتم اختلاق أي قدرة أو مقياس.",
        "لا تستخدم بيانات الاختبار المعياري لحسم التعادل قبل اعتماد سياسة تطبيع مستقلة.",
    ]
    document.setFont("PlanArabic", 12)
    document.setFillColor(HexColor("#E5EEF8"))
    y = height - 120
    for line in arabic_lines:
        document.drawRightString(width - 48, y, _rtl(line))
        y -= 31

    document.setFillColor(HexColor("#0F172A"))
    document.roundRect(48, 310, width - 96, 180, 12, fill=1, stroke=0)
    document.setFillColor(HexColor("#A7F3D0"))
    document.setFont("Courier", 10)
    technical_lines = [
        "ranking_key = (-score, tool_id)",
        "service = RecommendationService",
        "reasons = fired RuleImpact.rationale values only",
        "Benchmarks do not break ties",
        "pytest -q: PASS",
        "compileall + pip check + strict schemas: PASS",
    ]
    y = 458
    for line in technical_lines:
        document.drawString(64, y, line)
        y -= 24

    document.setFillColor(HexColor("#94A3B8"))
    document.setFont("Helvetica", 8)
    document.drawString(48, 78, "Sources: Python Sorting HOWTO | CLIPS 6.4.2 | Tintarev & Masthoff 2012")
    document.drawCentredString(width / 2, 34, "6")
    document.save()


def _draw_phase_five_appendix(path: Path) -> None:
    _register_fonts()
    document = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    document.setFillColor(HexColor("#172033"))
    document.rect(0, 0, width, height, fill=1, stroke=0)
    document.setFillColor(HexColor("#67E8F9"))
    document.setFont("PlanArabicBold", 18)
    document.drawRightString(
        width - 48,
        height - 68,
        _rtl("ملحق تنفيذ المرحلة الخامسة - واجهة HTTP والعقود"),
    )

    arabic_lines = [
        "أضيفت واجهات قراءة مرتبة للمراحل والأسئلة والأدوات بعقود استجابة صريحة.",
        "يمر طلب الترشيح بعقد صارم ثم يستخدم خدمة الترشيح ومحرك CLIPS الحقيقيين.",
        "تتحقق حاوية المعرفة من المعرّفات والمراجع بين المراحل والأسئلة والقواعد والأدوات.",
        "تحافظ أخطاء الإدخال والحالات التشغيلية على غلاف موحد دون كشف التفاصيل الداخلية.",
        "تم تأجيل تحميل قاعدة المعرفة من الملفات إلى المرحلة السادسة بقرار تصميم مقصود.",
    ]
    document.setFont("PlanArabic", 12)
    document.setFillColor(HexColor("#E5EEF8"))
    y = height - 120
    for line in arabic_lines:
        document.drawRightString(width - 48, y, _rtl(line))
        y -= 31

    document.setFillColor(HexColor("#0F172A"))
    document.roundRect(48, 286, width - 96, 204, 12, fill=1, stroke=0)
    document.setFillColor(HexColor("#A7F3D0"))
    document.setFont("Courier", 9.5)
    technical_lines = [
        "GET /api/stages",
        "GET /api/stages/{stage}/questions",
        "GET /api/tools/{tool_id}",
        "POST /api/recommendations",
        "contracts = KnowledgeSnapshot + RecommendationRequest",
        "response_model = typed Pydantic contracts",
        "Loader deferred to Phase 6",
    ]
    y = 458
    for line in technical_lines:
        document.drawString(64, y, line)
        y -= 24

    document.setFillColor(HexColor("#94A3B8"))
    document.setFont("Helvetica", 8)
    document.drawString(
        48,
        78,
        "Sources: FastAPI APIRouter | Response Models | Dependencies | TestClient",
    )
    document.drawCentredString(width / 2, 34, "7")
    document.save()


def build_updated_pdf(source_path: Path, output_path: Path) -> None:
    reader = PdfReader(source_path)
    metadata = reader.metadata or {}
    phase_four_pages = int(metadata.get(PHASE_FOUR_MARKER) == "1")
    phase_five_pages = int(metadata.get(PHASE_FIVE_MARKER) == "1")
    base_page_count = len(reader.pages) - phase_four_pages - phase_five_pages

    with TemporaryDirectory() as temporary_directory:
        phase_four_path = Path(temporary_directory) / "phase4-appendix.pdf"
        phase_five_path = Path(temporary_directory) / "phase5-api.pdf"
        _draw_phase_four_appendix(phase_four_path)
        _draw_phase_five_appendix(phase_five_path)
        phase_four = PdfReader(phase_four_path)
        phase_five = PdfReader(phase_five_path)

        writer = PdfWriter()
        for page in reader.pages[:base_page_count]:
            writer.add_page(page)
        writer.add_page(phase_four.pages[0])
        writer.add_page(phase_five.pages[0])
        metadata = {
            str(key): str(value)
            for key, value in (reader.metadata or {}).items()
            if value is not None
        }
        metadata[PHASE_FOUR_MARKER] = "1"
        metadata[PHASE_FIVE_MARKER] = "1"
        writer.add_metadata(metadata)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            mode="wb", delete=False, dir=output_path.parent, suffix=".pdf"
        ) as temporary_output:
            writer.write(temporary_output)
            temporary_output_path = Path(temporary_output.name)
        temporary_output_path.replace(output_path)


if __name__ == "__main__":
    build_updated_pdf(DEFAULT_PDF, DEFAULT_PDF)
