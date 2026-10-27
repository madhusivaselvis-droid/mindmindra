from dataclasses import dataclass
from statistics import mean
from typing import Any

from sklearn.ensemble import RandomForestClassifier


FEATURE_NAMES = (
    'accuracy',
    'reaction',
    'completion',
    'consistency',
    'score',
    'attempts',
    'previous_difficulty',
    'cps',
)
MIN_TRAINING_SESSIONS = 8


@dataclass(frozen=True)
class DifficultyDecision:
    cps: float
    components: dict[str, float]
    next_difficulty: int
    model_used: str
    confidence: float | None
    caregiver_notification: bool
    next_activity: str
    explanation: str


def performance_components(
    *, accuracy: float, response_time: float, attempts: int, completed: bool,
    recent_accuracies: list[float],
) -> dict[str, float]:
    accuracy_score = max(0.0, min(100.0, accuracy * 100))
    average_response_seconds = response_time / max(attempts, 1)
    reaction_score = max(0.0, min(100.0, 100.0 - average_response_seconds * 10.0))
    completion_score = 100.0 if completed else 0.0
    if recent_accuracies:
        recent_mean = mean(recent_accuracies[-3:]) * 100.0
        consistency_score = max(0.0, 100.0 - abs(accuracy_score - recent_mean))
    else:
        consistency_score = 100.0
    cps = 0.4 * accuracy_score + 0.2 * reaction_score + 0.2 * completion_score + 0.2 * consistency_score
    return {
        'accuracy': round(accuracy_score, 1),
        'reaction': round(reaction_score, 1),
        'completion': round(completion_score, 1),
        'consistency': round(consistency_score, 1),
        'cps': round(cps, 1),
    }


def threshold_difficulty(cps: float, previous_difficulty: int) -> int:
    if cps > 80:
        return min(3, previous_difficulty + 1)
    if cps >= 60:
        return previous_difficulty
    if cps >= 40:
        return max(1, previous_difficulty - 1)
    return max(1, previous_difficulty - 1)


def _features(components: dict[str, float], score: int, attempts: int, previous_difficulty: int) -> list[float]:
    return [
        components['accuracy'], components['reaction'], components['completion'],
        components['consistency'], float(score), float(attempts),
        float(previous_difficulty), components['cps'],
    ]


def recommend_difficulty(
    *, current_accuracy: float, current_response_time: float, current_score: int,
    current_attempts: int, current_completed: bool, previous_difficulty: int,
    history: list[dict[str, Any]],
) -> DifficultyDecision:
    recent_accuracies = [float(item['accuracy']) for item in history[-3:]]
    components = performance_components(
        accuracy=current_accuracy,
        response_time=current_response_time,
        attempts=current_attempts,
        completed=current_completed,
        recent_accuracies=recent_accuracies,
    )
    fallback_level = threshold_difficulty(components['cps'], previous_difficulty)

    training_rows: list[list[float]] = []
    training_labels: list[int] = []
    for index, item in enumerate(history):
        prior = history[max(0, index - 3):index]
        historical_components = performance_components(
            accuracy=float(item['accuracy']),
            response_time=float(item['response_time']),
            attempts=int(item['attempts']),
            completed=bool(item['completed']),
            recent_accuracies=[float(previous['accuracy']) for previous in prior],
        )
        difficulty = int(item['difficulty_level'])
        training_rows.append(_features(historical_components, int(item['score']), int(item['attempts']), difficulty))
        training_labels.append(threshold_difficulty(historical_components['cps'], difficulty))

    if len(training_rows) >= MIN_TRAINING_SESSIONS and len(set(training_labels)) >= 2:
        model = RandomForestClassifier(n_estimators=120, max_depth=5, min_samples_leaf=2, class_weight='balanced', random_state=42)
        model.fit(training_rows, training_labels)
        feature_row = _features(components, current_score, current_attempts, previous_difficulty)
        prediction = int(model.predict([feature_row])[0])
        probabilities = model.predict_proba([feature_row])[0]
        confidence = float(max(probabilities))
        explanation = f'Random Forest used {len(training_rows)} previous pattern sessions and recommends Level {prediction}.'
        model_name = 'random_forest'
    else:
        prediction = fallback_level
        confidence = None
        explanation = f'Threshold fallback recommends Level {prediction}; Random Forest will activate after {MIN_TRAINING_SESSIONS} sessions with varied outcomes.'
        model_name = 'threshold_fallback'

    notify = components['cps'] < 40
    if notify:
        prediction = min(prediction, max(1, previous_difficulty - 1))
        explanation += ' CPS is below 40, so an easier activity and caregiver review are recommended.'
    return DifficultyDecision(
        cps=components['cps'],
        components=components,
        next_difficulty=prediction,
        model_used=model_name,
        confidence=round(confidence, 3) if confidence is not None else None,
        caregiver_notification=notify,
        next_activity='GUIDED_EASY_ACTIVITY' if notify else 'PATTERN_RECOGNITION',
        explanation=explanation,
    )
