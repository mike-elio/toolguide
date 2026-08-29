from scripts.simulate_adaptive_questionnaire import (
    SimulationReport,
    render_markdown,
    run_simulation,
)


def test_rendered_report_has_no_trailing_whitespace() -> None:
    report = SimulationReport(
        session_count=1,
        completed_sessions=1,
        failed_sessions=0,
        pool_count=1,
        minimum_question_count=6,
        maximum_question_count=6,
        question_count_distribution={6: 1},
        result_tool_coverage=3,
        result_tool_coverage_percent=6.2,
        top_recommendation_diversity={"analysis/software": 1},
        session_paths=(("analysis-software-q1",),),
        session_recommendations=(("tool-1",),),
        failures=(),
        samples=("analysis/software | 6 questions | Tool 1",),
    )

    rendered = render_markdown(report)

    assert all(line == line.rstrip() for line in rendered.splitlines())


def test_twenty_four_session_smoke_simulation_has_no_failures() -> None:
    report = run_simulation(session_count=24)

    assert report.session_count == 24
    assert report.completed_sessions == 24
    assert report.failed_sessions == 0
    assert report.pool_count == 12
    assert report.minimum_question_count >= 6
    assert report.maximum_question_count <= 10


def test_simulation_replays_identical_seed_and_answers_deterministically() -> None:
    first = run_simulation(session_count=12, seed_prefix="repeatable")
    second = run_simulation(session_count=12, seed_prefix="repeatable")

    assert first.session_paths == second.session_paths
    assert first.session_recommendations == second.session_recommendations
