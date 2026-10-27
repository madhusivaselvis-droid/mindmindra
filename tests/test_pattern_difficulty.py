from app.ai.difficulty import recommend_difficulty, threshold_difficulty


def test_cps_thresholds_select_expected_level_changes():
    assert threshold_difficulty(81, 2) == 3
    assert threshold_difficulty(80, 2) == 2
    assert threshold_difficulty(59.9, 2) == 1
    assert threshold_difficulty(39.9, 2) == 1


def test_random_forest_activates_after_enough_historical_sessions():
    history = [
        {'accuracy': 0.95, 'response_time': 1.5, 'attempts': 3, 'completed': True, 'score': 95, 'difficulty_level': level}
        for level in [1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3]
    ]
    decision = recommend_difficulty(
        current_accuracy=0.95,
        current_response_time=1.5,
        current_score=95,
        current_attempts=3,
        current_completed=True,
        previous_difficulty=2,
        history=history,
    )
    assert decision.model_used == 'random_forest'
    assert decision.next_difficulty in (1, 2, 3)
    assert decision.cps > 80


def test_insufficient_history_uses_explainable_threshold_fallback():
    decision = recommend_difficulty(
        current_accuracy=0.75,
        current_response_time=3,
        current_score=75,
        current_attempts=4,
        current_completed=True,
        previous_difficulty=2,
        history=[],
    )
    assert decision.model_used == 'threshold_fallback'
    assert decision.components['accuracy'] == 75
    assert decision.components['completion'] == 100
    assert decision.next_difficulty in (1, 2, 3)


def test_low_cps_selects_easier_activity_and_notifies_caregiver():
    decision = recommend_difficulty(
        current_accuracy=0.1,
        current_response_time=1000,
        current_score=10,
        current_attempts=10,
        current_completed=False,
        previous_difficulty=3,
        history=[],
    )
    assert decision.cps < 40
    assert decision.next_difficulty == 2
    assert decision.next_activity == 'GUIDED_EASY_ACTIVITY'
    assert decision.caregiver_notification
