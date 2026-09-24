from dataclasses import replace

import pytest

from app.knowledge import default_knowledge_path, load_knowledge
from scripts.simulate_adaptive_questionnaire import (
    SimulationReport,
    _latency_metrics,
    _target_tool,
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
    assert "# Adaptive Questionnaire - 1 Session Simulation" in rendered
    assert "3/unknown" in rendered
    expanded = render_markdown(replace(report, catalog_tool_count=192, total_pool_count=12))
    assert "3/192" in expanded
    assert "1/12" in expanded


@pytest.mark.parametrize("pool_size", [3, 4, 16, 20])
def test_target_tool_cycles_through_every_tool_in_actual_pool(pool_size: int) -> None:
    pool = list(range(pool_size))

    assert [_target_tool(pool, visit) for visit in range(pool_size * 2)] == pool * 2


def test_latency_metrics_use_nearest_rank_and_do_not_require_sorted_input() -> None:
    assert _latency_metrics([]) == (0.0, 0.0, 0.0)
    assert _latency_metrics([7.0]) == (7.0, 7.0, 7.0)
    assert _latency_metrics(list(reversed(range(1, 21)))) == (10.5, 19, 20)


def test_twenty_four_session_smoke_simulation_has_no_failures() -> None:
    report = run_simulation(session_count=24)

    assert report.session_count == 24
    assert report.completed_sessions == 24
    assert report.failed_sessions == 0
    assert report.pool_count == 12
    assert report.minimum_question_count >= 6
    assert report.maximum_question_count <= 10
    snapshot = load_knowledge(default_knowledge_path())
    assert report.catalog_tool_count == len(snapshot.tools)
    assert report.catalog_question_count == len(snapshot.questions)
    assert report.catalog_rule_count == len(snapshot.rules)
    assert report.result_tool_coverage_percent == round(
        100 * report.result_tool_coverage / report.catalog_tool_count, 1
    )
    assert report.total_pool_count == report.pool_count
    # Each completed session needs an additional advance call to obtain its results.
    assert report.request_count >= sum(map(len, report.session_paths)) + report.session_count
    assert 0 < report.request_latency_mean_ms <= report.request_latency_max_ms
    assert 0 < report.request_latency_p95_ms <= report.request_latency_max_ms
    assert report.session_latency_mean_ms >= report.request_latency_mean_ms
    assert 0 < report.session_latency_p95_ms <= report.session_latency_max_ms


def test_simulation_replays_identical_seed_and_answers_deterministically() -> None:
    first = run_simulation(session_count=12, seed_prefix="repeatable")
    second = run_simulation(session_count=12, seed_prefix="repeatable")

    assert first.session_paths == second.session_paths
    assert first.session_recommendations == second.session_recommendations
