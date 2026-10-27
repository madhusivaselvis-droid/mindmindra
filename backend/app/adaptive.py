from dataclasses import dataclass

@dataclass
class DifficultyDecision:
    next_difficulty: int
    explanation: str

def recommend_difficulty(accuracy: float, current: int, recent_accuracies: list[float]) -> DifficultyDecision:
    values = recent_accuracies[-3:] + [accuracy]
    average = sum(values) / len(values)
    if average >= .85 and len(values) >= 3:
        next_level = min(3, current + 1)
        return DifficultyDecision(next_level, f'Performance stayed strong across {len(values)} recent sessions, so Level {next_level} was selected.')
    if average < .60:
        next_level = max(1, current - 1)
        return DifficultyDecision(next_level, f'Recent accuracy was below 60%, so Level {next_level} was selected for a gentler challenge.')
    return DifficultyDecision(current, f'Performance is steady, so Level {current} was kept.')
