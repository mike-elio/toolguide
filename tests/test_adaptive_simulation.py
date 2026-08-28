from scripts.simulate_adaptive_questionnaire import run_simulation


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
