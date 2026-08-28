from pathlib import Path

from pypdf import PdfReader

from scripts.update_backend_plan_pdf import build_updated_pdf


SOURCE_PDF = Path("output/pdf/ai_expert_system_backend_plan_ar.pdf")


def test_build_updated_pdf_keeps_phase_appendices_idempotent(tmp_path: Path) -> None:
    first_output = tmp_path / "first.pdf"
    second_output = tmp_path / "second.pdf"

    build_updated_pdf(SOURCE_PDF, first_output)
    build_updated_pdf(first_output, second_output)

    first = PdfReader(first_output)
    second = PdfReader(second_output)
    assert len(first.pages) == 7
    assert len(second.pages) == 7
    assert first.metadata.get("/Phase4Appendix") == "1"
    assert second.metadata.get("/Phase4Appendix") == "1"
    assert first.metadata.get("/Phase5Api") == "1"
    assert second.metadata.get("/Phase5Api") == "1"

    phase_four_text = second.pages[-2].extract_text()
    assert "(-score, tool_id)" in phase_four_text
    assert "RecommendationService" in phase_four_text
    assert "Benchmarks do not break ties" in phase_four_text

    phase_five_text = second.pages[-1].extract_text()
    assert "GET /api/stages" in phase_five_text
    assert "POST /api/recommendations" in phase_five_text
    assert "KnowledgeSnapshot" in phase_five_text
    assert "Loader deferred to Phase 6" in phase_five_text
